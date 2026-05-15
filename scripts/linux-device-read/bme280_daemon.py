#!/usr/bin/env python3
"""Poll BME280 and publish readings as JSON for OS-level consumers.

Writes atomically to a stable path (default ``/var/lib/bme280/readings.json``) so any process
can ``cat`` or parse the file without talking to this daemon. Intended to run under systemd;
see ``bme280-json.service`` and ``PI_LINUX_DEVICE_READ.txt``.

JSON schema (``ok`` true):
  timestamp_utc            ISO8601 Zulu time
  i2c_address              string like ``0x77``
  temperature_c            float
  relative_humidity_percent float
  pressure_hpa             float (station pressure)
  approximate_altitude_m   float or null (depends on sea_level_pressure calibration)

When ``ok`` is false, ``error`` holds a short message (sensor missing, I/O glitch, etc.).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import tempfile
import time
from datetime import datetime, timezone
from typing import Any


LOG = logging.getLogger("bme280_daemon")

DEFAULT_JSON_PATH = "/var/lib/bme280/readings.json"


def chdir_home_for_lgpio() -> None:
    """Blinka on Pi 5 uses lgpio, which creates ``.lgd-nfy*`` files in cwd; ``$HOME`` is safe."""
    try:
        home = os.path.expanduser("~")
        if home and os.path.isdir(home):
            os.chdir(home)
    except OSError:
        pass


def load_sensor_backend(address: int):
    """Import Blinka + driver and return an initialized ``Adafruit_BME280_I2C`` instance."""
    try:
        import board
        import busio
        from adafruit_bme280 import basic as adafruit_bme280
    except ImportError as e:
        err = str(e).lower()
        if "lgpio" in err:
            LOG.error(
                "Blinka on Pi 5 needs lgpio: sudo apt install -y liblgpio1 && "
                "pip install lgpio (inside ~/bme280-venv)."
            )
        else:
            LOG.error("Missing Adafruit deps: pip install -r requirements.txt (linux-device-read).")
        raise

    i2c = busio.I2C(board.SCL, board.SDA)
    bme = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=address)
    bme.sea_level_pressure = 1013.25
    return bme


def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, mode=0o755, exist_ok=True)


def write_json_atomic(path: str, payload: dict[str, Any]) -> None:
    """Write JSON then rename into place so readers never see a half-written file."""
    directory = os.path.dirname(os.path.abspath(path)) or "."
    ensure_parent_dir(path)

    fd, tmp_path = tempfile.mkstemp(
        prefix=".readings_",
        suffix=".json.tmp",
        dir=directory,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, path)
        os.chmod(path, 0o644)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def reading_payload_ok(address: int, bme) -> dict[str, Any]:
    approx_alt: float | None
    try:
        approx_alt = float(bme.altitude)
    except Exception:
        approx_alt = None

    return {
        "ok": True,
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "i2c_address": f"{address:#04x}",
        "temperature_c": round(float(bme.temperature), 3),
        "relative_humidity_percent": round(float(bme.relative_humidity), 3),
        "pressure_hpa": round(float(bme.pressure), 3),
        "approximate_altitude_m": round(approx_alt, 2) if approx_alt is not None else None,
    }


def reading_payload_error(address: int, message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "i2c_address": f"{address:#04x}",
        "error": message,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish BME280 readings as JSON.")
    parser.add_argument(
        "--output",
        "-o",
        default=os.environ.get("BME280_JSON_PATH", DEFAULT_JSON_PATH),
        help=f"JSON output path (default: env BME280_JSON_PATH or {DEFAULT_JSON_PATH}).",
    )
    parser.add_argument(
        "--address",
        type=lambda x: int(x, 0),
        default=0x77,
        help="I2C 7-bit address (default 0x77).",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Seconds between successful polls (default 2).",
    )
    return parser.parse_args()


def sleep_interruptible(seconds: float, should_stop: list[bool]) -> None:
    """Sleep in small slices so SIGTERM/SIGINT sets ``should_stop`` and we exit promptly."""
    end = time.monotonic() + max(0.0, seconds)
    while time.monotonic() < end:
        if should_stop[0]:
            return
        time.sleep(min(0.25, end - time.monotonic()))


def main() -> int:
    args = parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    chdir_home_for_lgpio()

    stop_flag = [False]

    def handle_stop(signum: int, _frame) -> None:
        LOG.info("Received signal %s, shutting down.", signum)
        stop_flag[0] = True

    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)

    try:
        bme = load_sensor_backend(args.address)
    except ValueError as e:
        LOG.error("BME280 not found at %s: %s", f"{args.address:#04x}", e)
        try:
            write_json_atomic(args.output, reading_payload_error(args.address, str(e)))
        except OSError as oe:
            LOG.error("Could not write error JSON to %s: %s", args.output, oe)
        return 2
    except ImportError:
        return 1

    LOG.info(
        "Publishing to %s every %.1fs (I2C %s)",
        args.output,
        args.interval,
        f"{args.address:#04x}",
    )

    try:
        while not stop_flag[0]:
            try:
                payload = reading_payload_ok(args.address, bme)
                write_json_atomic(args.output, payload)
                LOG.debug("Wrote %s", payload.get("timestamp_utc"))
            except OSError as e:
                LOG.warning("Write failed: %s", e)
            except Exception as e:  # noqa: BLE001 — publish error blob for consumers
                LOG.exception("Read/write cycle failed")
                try:
                    write_json_atomic(
                        args.output,
                        reading_payload_error(args.address, str(e)),
                    )
                except OSError:
                    pass

            sleep_interruptible(args.interval, stop_flag)
    finally:
        LOG.info("Daemon exit.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
