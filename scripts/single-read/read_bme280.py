#!/usr/bin/env python3
"""Read Bosch BME280 environmental sensor over I2C on a Raspberry Pi (Ubuntu).

Prerequisites (see PI_BME280_SETUP.txt):
  - I2C enabled (dtparam=i2c_arm=on), user in group ``i2c`` (and often ``gpio`` on Pi 5).
  - Virtualenv with adafruit-blinka, adafruit-circuitpython-bme280, lgpio; liblgpio1 via apt.

How it fits together:
  - Adafruit *Blinka* provides ``board`` and ``busio`` so desktop Python uses the same APIs as
    CircuitPython on microcontrollers. On Pi 5 it goes through *lgpio* and the kernel I2C driver.
  - *adafruit-circuitpython-bme280* speaks the BME280 register protocol on the I2C bus.
  - Wiring: Pi SDA/SCL to breakout SDA/SCL, 3.3 V and GND (not 5 V for typical Adafruit boards).

Run (example): activate your venv, ``cd ~``, then
``python3 ~/Temp-Humidity-Project/scripts/single-read/read_bme280.py``.
"""

from __future__ import annotations

import argparse
import os
import sys
import time


def main() -> int:
    # --- CLI -----------------------------------------------------------------
    # Keep flags minimal: one-shot vs loop, I2C address, and poll interval.
    parser = argparse.ArgumentParser(description="Print BME280 temperature, humidity, pressure.")
    parser.add_argument(
        "--address",
        type=lambda x: int(x, 0),
        default=0x77,
        help="I2C 7-bit address (default 0x77). Many breakouts use 0x76 — check i2cdetect.",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Print readings repeatedly until Ctrl+C (SIGINT).",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Seconds to sleep between readings when --loop is set.",
    )
    args = parser.parse_args()

    # --- Working directory before importing Blinka / lgpio --------------------
    # Blinka on Raspberry Pi 5 loads ``lgpio``, which creates hidden pipe files named
    # ``.lgd-nfy*`` in the process current working directory. Some directories (e.g. a project
    # folder on certain mounts or with tight permissions) trigger "Can't set permissions" or
    # FileNotFoundError when those files are created. ``$HOME`` has been reliable in practice.
    try:
        home = os.path.expanduser("~")
        if home and os.path.isdir(home):
            os.chdir(home)
    except OSError:
        pass

    # --- Late imports (after chdir); dependency errors get actionable hints -----
    try:
        # ``board`` maps logical names (SCL, SDA) to the Pi header pins for this hardware.
        import board
        import busio
        from adafruit_bme280 import basic as adafruit_bme280
    except ImportError as e:
        err = str(e).lower()
        if "lgpio" in err:
            print(
                "Blinka on Raspberry Pi 5 needs the lgpio Python module.\n"
                "  sudo apt install -y liblgpio1\n"
                "  source ~/bme280-venv/bin/activate\n"
                "  pip install lgpio\n"
                "Or: sudo apt install -y python3-lgpio && recreate the venv with:\n"
                "  python3 -m venv --system-site-packages ~/bme280-venv\n",
                file=sys.stderr,
            )
        else:
            print(
                "Missing dependency. On the Pi, in your venv:\n"
                "  cd ~/Temp-Humidity-Project/scripts/single-read\n"
                "  pip install -r requirements-bme280.txt\n",
                file=sys.stderr,
            )
        print(repr(e), file=sys.stderr)
        return 1

    # --- Open I2C bus and sensor ----------------------------------------------
    # ``busio.I2C`` wraps the Linux I2C device for the pins defined on ``board``.
    # ``Adafruit_BME280_I2C`` performs chip ID check and configures oversampling;
    # ValueError usually means wrong address or no device / wiring issue.
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        bme = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=args.address)
    except ValueError as e:
        print(
            f"Could not open BME280 at I2C address {args.address:#04x}. "
            f"Try the other address (often 0x76 or 0x77) with --address.\n{e}",
            file=sys.stderr,
        )
        return 2

    # Mean sea-level pressure (hPa) used internally when exposing altitude-related properties.
    # Does not change raw temperature/humidity/pressure readouts here; library uses it for
    # ``altitude`` if you ever ask for that. Standard atmosphere reference is ~1013.25 hPa.
    bme.sea_level_pressure = 1013.25

    def line() -> str:
        # Properties trigger I2C reads each time (small overhead; fine for console debugging).
        # Units: °C per chip datasheet calibration; RH %; station pressure in hectopascals.
        return (
            f"Temperature: {bme.temperature:.2f} °C | "
            f"Humidity: {bme.relative_humidity:.2f} % | "
            f"Pressure: {bme.pressure:.2f} hPa"
        )

    if args.loop:
        try:
            while True:
                print(line(), flush=True)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nStopped.")
            return 0

    print(line())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
