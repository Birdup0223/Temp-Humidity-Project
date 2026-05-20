# Temp-Humidity-Project

Raspberry Pi 5 + BME280 environmental sensor (temperature, humidity, barometric pressure) on Ubuntu, with two ways to read it:

| Mode | Folder | Best for |
|------|--------|----------|
| **Console** | `scripts/single-read/` | Debugging, one-off checks, watching values in the terminal |
| **OS-level JSON** | `scripts/linux-device-read/` | Always-on readings any program or shell command can read from a file |

**New Pi from scratch:** [`NEW_PI_SETUP.md`](NEW_PI_SETUP.md) — full replication checklist.

---

## Repository layout

| Path | Contents |
|------|----------|
| `scripts/single-read/` | `read_bme280.py`, setup notes |
| `scripts/linux-device-read/` | `bme280_daemon.py`, `bme280-json.service`, setup notes |
| `Reference Material/` | Sensor specs and research PDFs |
| `NEW_PI_SETUP.md` | Step-by-step for a fresh Pi |
| `pi-connection.local.example.txt` | Template for SSH user/IP (copy locally; not committed) |

---

## linux-device-read — OS-level sensor access

### What it does

A small **Python daemon** (`bme280_daemon.py`) polls the BME280 over I2C and writes the latest sample to a **JSON file**. The file is updated **atomically** (write to a temp file, then rename) so readers never see half-written JSON.

This is **not** a kernel `/dev/*` device node. It is the usual pattern for “always available” sensor data on Linux: a **stable path** + a **background service**. Anything on the Pi can read it with normal tools (`cat`, `jq`, scripts, cron, other apps) without importing Adafruit libraries.

### Where the data lives

| Use case | Path |
|----------|------|
| **Production** (systemd, boot-time) | `/var/lib/bme280/readings.json` |
| **Manual test** | Any path you pass with `--output`, e.g. `/tmp/bme280-test/readings.json` |

With systemd, `StateDirectory=bme280` creates `/var/lib/bme280/` owned for the service user.

### JSON format

Always check **`"ok"`** first.

**Success** (`"ok": true`):

```json
{
  "ok": true,
  "timestamp_utc": "2026-05-20T15:05:52Z",
  "i2c_address": "0x77",
  "temperature_c": 24.796,
  "relative_humidity_percent": 55.841,
  "pressure_hpa": 1018.109,
  "approximate_altitude_m": -40.6
}
```

**Failure** (`"ok": false`): includes `"error"` (sensor missing, I2C issue, etc.).

| Field | Meaning |
|-------|---------|
| `temperature_c` | °C |
| `relative_humidity_percent` | % RH |
| `pressure_hpa` | Station pressure (hectopascals) |
| `approximate_altitude_m` | Derived from pressure; rough without local calibration |

---

### Reading the sensor (commands)

These work **while the daemon or systemd service is running**. They read the file; they do not talk to the hardware directly.

**Plain text (whole file):**

```bash
cat /var/lib/bme280/readings.json
```

**Pretty-printed:**

```bash
jq . /var/lib/bme280/readings.json
```

**One field** (requires `jq`):

```bash
jq -r .temperature_c /var/lib/bme280/readings.json
jq -r .relative_humidity_percent /var/lib/bme280/readings.json
jq -r .pressure_hpa /var/lib/bme280/readings.json
```

**Watch updates every 2 seconds:**

```bash
watch -n 2 cat /var/lib/bme280/readings.json
```

**Python one-liner:**

```bash
python3 -c "import json; print(json.load(open('/var/lib/bme280/readings.json')))"
```

**From another machine** (SSH):

```bash
ssh robot@192.168.1.96 "cat /var/lib/bme280/readings.json"
```

Install `jq` on the Pi if needed: `sudo apt install -y jq`.

---

### Running the daemon

**Prerequisites:** I2C enabled, user in `i2c` group, virtualenv at `~/bme280-venv` with dependencies (see [Pi quick start](#pi-quick-start-summary) below).

**Foreground test** (writes to `/tmp` for experiments; folder is system `/tmp`, not your home):

```bash
source ~/bme280-venv/bin/activate
mkdir -p /tmp/bme280-test
cd ~
python3 ~/Temp-Humidity-Project/scripts/linux-device-read/bme280_daemon.py \
  --output /tmp/bme280-test/readings.json \
  --interval 2
```

In another terminal: `cat /tmp/bme280-test/readings.json`. Stop with **Ctrl+C**.

**Daemon options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--output` / `-o` | `/var/lib/bme280/readings.json` | JSON file path (or set env `BME280_JSON_PATH`) |
| `--interval` | `2` | Seconds between polls |
| `--address` | `0x77` | I2C address; use `0x76` if `i2cdetect` shows 76 |

Example — alternate address and 5 s interval:

```bash
python3 ~/Temp-Humidity-Project/scripts/linux-device-read/bme280_daemon.py \
  -o /var/lib/bme280/readings.json \
  --address 0x76 \
  --interval 5
```

---

### systemd service (recommended for a real Pi)

Install once after `git clone` and venv setup:

```bash
sudo cp ~/Temp-Humidity-Project/scripts/linux-device-read/bme280-json.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now bme280-json.service
```

**Service management:**

```bash
systemctl status bme280-json.service      # running?
sudo systemctl restart bme280-json.service
sudo systemctl stop bme280-json.service
journalctl -u bme280-json.service -f    # live logs
```

**Readings after install:**

```bash
cat /var/lib/bme280/readings.json
```

**Troubleshooting:** If status shows **`216/GROUP`**, an old unit may list `SupplementaryGroups=i2c gpio` when `gpio` does not exist on Ubuntu. Remove that line:

```bash
sudo sed -i '/^SupplementaryGroups=/d' /etc/systemd/system/bme280-json.service
sudo systemctl daemon-reload
sudo systemctl restart bme280-json.service
```

If your Linux user is not **`robot`**, edit `User=`, `Group=`, and `/home/robot` paths in `bme280-json.service` before `systemctl enable`. Details: [`NEW_PI_SETUP.md`](NEW_PI_SETUP.md) and `scripts/linux-device-read/PI_LINUX_DEVICE_READ.txt`.

---

## single-read — console output (brief)

For interactive use without the JSON file:

```bash
source ~/bme280-venv/bin/activate
cd ~
python3 ~/Temp-Humidity-Project/scripts/single-read/read_bme280.py
python3 ~/Temp-Humidity-Project/scripts/single-read/read_bme280.py --loop
python3 ~/Temp-Humidity-Project/scripts/single-read/read_bme280.py --address 0x76
```

See `scripts/single-read/PI_BME280_SETUP.txt` for I2C, venv, and Pi 5 notes.

---

## Pi quick start (summary)

```bash
sudo apt update
sudo apt install -y git i2c-tools python3-pip python3-venv python3-full python3.12-venv liblgpio1 jq
sudo usermod -aG i2c $USER
# log out and back in

cd ~
git clone https://github.com/Birdup0223/Temp-Humidity-Project.git

python3 -m venv ~/bme280-venv
source ~/bme280-venv/bin/activate
pip install --upgrade pip
pip install -r ~/Temp-Humidity-Project/scripts/single-read/requirements-bme280.txt
pip install -r ~/Temp-Humidity-Project/scripts/linux-device-read/requirements.txt

# Console test
cd ~
python3 ~/Temp-Humidity-Project/scripts/single-read/read_bme280.py

# JSON service (see linux-device-read section above)
sudo cp ~/Temp-Humidity-Project/scripts/linux-device-read/bme280-json.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now bme280-json.service
cat /var/lib/bme280/readings.json
```

---

## Windows development

Copy `pi-connection.local.example.txt` to `pi-connection.local.txt` (gitignored) and set your Pi SSH user and IP.

Update the Pi after pushing changes:

```bash
cd ~/Temp-Humidity-Project && git pull
sudo systemctl restart bme280-json.service
```

---

## License

Add a license if you plan to share the repo publicly.
