# New Raspberry Pi setup (replication checklist)

Use this when bringing up a **fresh Pi** with the same BME280 + Ubuntu workflow. Assumes **Raspberry Pi 5**, **Ubuntu 24.04 (noble)**, Adafruit BME280 over I2C, repo cloned to **`~/Temp-Humidity-Project`**.

Replace **`robot`** below if your Linux username differs — also edit **`User=`** / paths in `scripts/linux-device-read/bme280-json.service` before installing systemd.

---

## 1. OS packages and I2C

```bash
sudo apt update
sudo apt install -y git i2c-tools python3-pip python3-venv python3-full python3.12-venv liblgpio1
```

Enable I2C if `i2cdetect -l` shows no buses:

```bash
sudo nano /boot/firmware/config.txt
# Ensure: dtparam=i2c_arm=on
sudo reboot
```

After reboot:

```bash
i2cdetect -y 1
```

Expect **`76`** or **`77`** when the sensor is wired.

---

## 2. User permissions

```bash
sudo usermod -aG i2c $USER
```

(`gpio` group is optional on Ubuntu; only add if it exists: `getent group gpio`.)

**Log out and back in** (or reboot) so group membership applies.

---

## 3. Clone the repo

```bash
cd ~
git clone https://github.com/Birdup0223/Temp-Humidity-Project.git
```

---

## 4. Python virtualenv (shared by single-read + linux-device-read)

```bash
python3 -m venv ~/bme280-venv
source ~/bme280-venv/bin/activate
pip install --upgrade pip
pip install -r ~/Temp-Humidity-Project/scripts/single-read/requirements-bme280.txt
pip install -r ~/Temp-Humidity-Project/scripts/linux-device-read/requirements.txt
```

If **`No module named 'lgpio'`**: `sudo apt install -y liblgpio1` then `pip install lgpio`.

---

## 5. Test console read (single-read)

```bash
source ~/bme280-venv/bin/activate
cd ~
python3 ~/Temp-Humidity-Project/scripts/single-read/read_bme280.py
```

If no device: add **`--address 0x76`**.

---

## 6. Test JSON daemon manually (linux-device-read)

**Terminal A:**

```bash
source ~/bme280-venv/bin/activate
cd ~
python3 ~/Temp-Humidity-Project/scripts/linux-device-read/bme280_daemon.py \
  --output /tmp/bme280-test/readings.json \
  --interval 2
```

**Terminal B:**

```bash
cat /tmp/bme280-test/readings.json
```

Expect **`"ok": true`**. Stop Terminal A with **Ctrl+C**.

(`/tmp/bme280-test` is only for this test; production path is below.)

---

## 7. Install systemd service (always-on JSON)

**Before `cp`:** if your username is not **`robot`**, edit the unit:

```bash
nano ~/Temp-Humidity-Project/scripts/linux-device-read/bme280-json.service
```

Change **`User=`**, **`Group=`**, **`WorkingDirectory=`**, and **`ExecStart=`** paths (`/home/robot` → `/home/YOURUSER`).

Install:

```bash
sudo cp ~/Temp-Humidity-Project/scripts/linux-device-read/bme280-json.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now bme280-json.service
systemctl status bme280-json.service
```

**Success:** `Active: active (running)`.

**Readings file:**

```bash
cat /var/lib/bme280/readings.json
jq . /var/lib/bme280/readings.json
```

### Troubleshooting systemd

| Symptom | Fix |
|--------|-----|
| **`216/GROUP`** | Unit must **not** contain `SupplementaryGroups=i2c gpio` unless those groups exist. Shipped unit omits it. If an old unit is installed: `sudo sed -i '/^SupplementaryGroups=/d' /etc/systemd/system/bme280-json.service` then `daemon-reload` + `restart`. |
| Service restart loop | `journalctl -u bme280-json.service -n 40 --no-pager` |
| No JSON file | Service not running; fix status first |
| Wrong I2C address | `sudo systemctl edit bme280-json.service` and add `--address 0x76` to `ExecStart` |

---

## 8. After code changes on GitHub

On the Pi:

```bash
cd ~/Temp-Humidity-Project && git pull
sudo cp ~/Temp-Humidity-Project/scripts/linux-device-read/bme280-json.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart bme280-json.service
```

---

## Quick reference

| What | Where |
|------|--------|
| Repo on Pi | `~/Temp-Humidity-Project` |
| Python venv | `~/bme280-venv` |
| Live JSON (production) | `/var/lib/bme280/readings.json` |
| Console script | `scripts/single-read/read_bme280.py` |
| Daemon | `scripts/linux-device-read/bme280_daemon.py` |
| Detailed guides | `scripts/single-read/PI_BME280_SETUP.txt`, `scripts/linux-device-read/PI_LINUX_DEVICE_READ.txt` |
