# Temp-Humidity-Project

Raspberry Pi 5 + BME280 (temperature, humidity, pressure): console reads, JSON daemon, and reference material.

## Layout

| Path | Purpose |
|------|--------|
| `scripts/single-read/` | One-shot / loop CLI (`read_bme280.py`) and Pi setup notes |
| `scripts/linux-device-read/` | Daemon that writes JSON for OS-level consumers + systemd unit |
| `Reference Material/` | Specs and research PDFs |

## Pi quick start (after `git clone`)

```bash
sudo apt update
sudo apt install -y i2c-tools python3-pip python3-venv python3-full python3.12-venv liblgpio1
sudo usermod -aG i2c,gpio $USER
# log out and back in
```

Create a venv and install deps (paths assume repo cloned to `~/Temp-Humidity-Project`):

```bash
python3 -m venv ~/bme280-venv
source ~/bme280-venv/bin/activate
pip install --upgrade pip
pip install -r ~/Temp-Humidity-Project/scripts/single-read/requirements-bme280.txt
pip install -r ~/Temp-Humidity-Project/scripts/linux-device-read/requirements.txt
```

Run the reader from `$HOME` (Pi 5 / lgpio cwd quirk):

```bash
cd ~
python3 ~/Temp-Humidity-Project/scripts/single-read/read_bme280.py
```

JSON daemon and systemd: see `scripts/linux-device-read/PI_LINUX_DEVICE_READ.txt`.

## Local notes (not in git)

Copy `pi-connection.local.example.txt` to `pi-connection.local.txt` and set your Pi SSH user and IP.

## License

Add a license if you plan to share the repo publicly.
