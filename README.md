# Temp-Humidity-Project

Raspberry Pi 5 + BME280 (temperature, humidity, pressure): console reads, JSON daemon for OS-level access, and reference material.

## New Pi from scratch

**Start here:** [`NEW_PI_SETUP.md`](NEW_PI_SETUP.md) — full replication checklist (git clone, venv, single-read test, systemd JSON service, troubleshooting including **`216/GROUP`**).

## Layout

| Path | Purpose |
|------|--------|
| `scripts/single-read/` | One-shot / loop CLI (`read_bme280.py`) |
| `scripts/linux-device-read/` | Daemon + systemd unit → `/var/lib/bme280/readings.json` |
| `Reference Material/` | Specs and research PDFs |

## Pi quick start (summary)

```bash
sudo apt update
sudo apt install -y git i2c-tools python3-pip python3-venv python3-full python3.12-venv liblgpio1
sudo usermod -aG i2c $USER
# log out and back in

cd ~
git clone https://github.com/Birdup0223/Temp-Humidity-Project.git

python3 -m venv ~/bme280-venv
source ~/bme280-venv/bin/activate
pip install --upgrade pip
pip install -r ~/Temp-Humidity-Project/scripts/single-read/requirements-bme280.txt
pip install -r ~/Temp-Humidity-Project/scripts/linux-device-read/requirements.txt

cd ~
python3 ~/Temp-Humidity-Project/scripts/single-read/read_bme280.py
```

Always-on JSON: see [`NEW_PI_SETUP.md`](NEW_PI_SETUP.md) §7 or `scripts/linux-device-read/PI_LINUX_DEVICE_READ.txt`.

```bash
cat /var/lib/bme280/readings.json
```

## Windows development

Copy `pi-connection.local.example.txt` to `pi-connection.local.txt` (gitignored) with your Pi SSH user and IP.

## License

Add a license if you plan to share the repo publicly.
