# Shabbat & Yom Tov Cron Automation

A standalone, zero-network-dependency Python system for Raspberry Pi that automates smart home tasks around Shabbat and Jewish Holidays (*Yom Tov*). 

# System architecture

Every morning at 05:00 AM, a coordinator script uses astronomical solar algorithms to detect if an observance starts that evening. If a holy day is detected, it handles multi-day holiday chains (e.g., a 2-day holiday followed directly by Shabbat) as a single union block. It then dynamically schedules your custom target execution scripts in the system `crontab`. If NO observance is detected for that evening, the script logs the information and exits. Your active crontab remains completely untouched. If an observance IS detected for that evening, the script takes three steps:

1. It clears out any old cron lines tagged with the shabbat-automation comment. 
2. It calculates the precise local Candle Lighting and Tzais times for your coordinate. 
3. It checks your folder and schedules your available child script. 

The Pre-Scripts run relative to the evening entry:

- shabbat-pre-1h.py runs 1 hour before Candle Lighting.
- shabbat-pre-0h.py runs exactly at Candle Lighting. 

The Post-Scripts run relative to the exit Havdalah:

1. shabbat-post-0h.py runs exactly at Tzais.
2. shabbat-post-1h.py runs 1 hour after Tzais. 

# Installation and Requirements

Log into your Raspberry Pi and install the native system crontab engine bindings and local astronomical calculator:

`pip install python-crontab zmanim`

*(Note: Ensure you install python-crontab and not the conflicting standalone crontab packag.)*

## 📂 Project Directory Structure

The setup securely expands your local home environment dynamically. Place your execution scripts inside `~/scripts/`:

```text
$HOME
├── log/shabbat-prepare.log       # Central log repository created automatically
└── scripts/
    ├── shabbat-prepare.py    # The master scheduling coordinator
    ├── shabbat-pre-1h.py     # Runs 1 hour BEFORE Candle Lighting (Optional)
    ├── shabbat-pre-0h.py     # Runs EXACTLY AT Candle Lighting (Optional)
    ├── shabbat-post-0h.py    # Runs EXACTLY AT Tzais / Havdalah (Optional)
    └── shabbat-post-1h.py    # Runs 1 hour AFTER Tzais / Havdalah (Optional)
```
* **Filesystem Safety Check**: The master coordinator automatically scans the directory on every execution. If a specific child script (e.g., `shabbat-pre-1h.py`) is missing, it will gracefully skip scheduling it without breaking the rest of your pipeline.

## ⚙️ Setting up the Daily Trigger

To let the coordinator analyze the calendar every morning, add it to your system crontab:

```bash
crontab -e
```

Append the following line at the very bottom of the file:

```text
0 5 * * * /usr/bin/python3 /home/pi/scripts/shabbat-prepare.py >> /home/pi/scripts/shabbat.log 2>&1
```
This forces the scheduler to run daily at **05:00 AM**, redirecting startup debugging events to a dedicated script log.

## 🧪 Testing & Simulations

The system includes a robust `--when` argument parser to let you bypass the weekday constraint and test exact calendar dates manually.
### 1. Test an ordinary weekday (Should skip safely)
```bash
./shabbat-prepare.py --when 2026-07-01
```
* **Expected Log Output:** `No Shabbat or Yom Tov entry occurs tonight. Exiting cleanly.`

### 2. Test a normal Shabbat Entry
```bash
./shabbat-prepare.py --when 2026-07-03
```
* **Expected Log Output:** Detects the Friday sequence, computes the exact local times for Rehovot, and safely populates your crontab.

### 3. Check your active temporary schedules
After running a simulation on an observance day, run the following command to see what was injected into your system profile:
```bash
crontab -l
```
You will notice your permanent tasks remain untouched, alongside newly appended lines cleanly sandboxed with a `# shabbat-automation` tag.
