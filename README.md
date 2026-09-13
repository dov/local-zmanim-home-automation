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

## 🕎 Chained blocks and internal transitions

Shabbat and Yom Tov (per Israeli convention: 1-day Yom Tov, Rosh Hashana 2 days) are
detected identically and chained together into a single block whenever they're
adjacent with no gap in melacha restrictions — e.g. Shabbat followed directly by a
Yom Tov, or a 2-day Yom Tov followed directly by Shabbat. The Pre-Scripts run once,
relative to the start of the *whole* chained block, and the Post-Scripts run once,
relative to the *end* of the whole chained block.

Where the chain crosses an internal Shabbat↔Yom Tov boundary (e.g. Shabbat ends
directly into a Yom Tov night), an extra transition script runs exactly at that
internal Tzais — separately from `shabbat-post-0h.py`, which only fires at the
true end of the whole chain:

- `shabbat-transition-shabbat2yomtov.py` — Shabbat ends directly into a Yom Tov.
- `shabbat-transition-yomtov2shabbat.py` — a Yom Tov ends directly into Shabbat.

These are intentionally *not* the same as `shabbat-post-0h.py`: since the observance
continues right on, they play a different (chag-entry) tune and do **not** turn off
the kumkum.

# Installation and Requirements

Log into your Raspberry Pi, clone this repo (e.g. into `~/git/local-zmanim-home-automation/`),
and run `./deploy.sh` from inside it. It uses [`uv`](https://astral.sh) to build a local `.venv`
right there in the checkout and installs all required packages (`python-crontab`, `zmanim`,
`paho-mqtt`, `python-telegram-bot`, `pychromecast`) into it — see [Setting up the Daily
Trigger](#️-setting-up-the-daily-trigger) below.

## 📂 Project Directory Structure

The system runs directly out of this git checkout — there is no copy step. `SCRIPT_DIR` and the
venv used to invoke child scripts are both derived from `shabbat-prepare.py`'s own location, so
wherever you clone the repo (e.g. `~/git/local-zmanim-home-automation/`) is where it runs from:

```text
local-zmanim-home-automation/       # This git checkout
├── .venv/                          # Local virtualenv created by deploy.sh
├── shabbat-prepare.py              # The master scheduling coordinator
├── shabbat-pre-1h.py                # Runs 1 hour BEFORE Candle Lighting (Optional)
├── shabbat-pre-0h.py                # Runs EXACTLY AT Candle Lighting (Optional)
├── shabbat-post-0h.py               # Runs EXACTLY AT Tzais / Havdalah (Optional)
├── shabbat-post-1h.py               # Runs 1 hour AFTER Tzais / Havdalah (Optional)
├── shabbat-transition-shabbat2yomtov.py  # Internal Tzais: Shabbat -> Yom Tov (Optional)
└── shabbat-transition-yomtov2shabbat.py  # Internal Tzais: Yom Tov -> Shabbat (Optional)

$HOME/log/shabbat-prepare.log       # Central log repository created automatically
```
* **Filesystem Safety Check**: The master coordinator automatically scans the directory on every execution. If a specific child script (e.g., `shabbat-pre-1h.py`) is missing, it will gracefully skip scheduling it without breaking the rest of your pipeline.

## ⚙️ Setting up the Daily Trigger

Run `./deploy.sh` from inside the git checkout — it pulls the latest code, (re)builds `.venv` in
place, and idempotently installs the daily crontab entry for you:

```bash
cd ~/git/local-zmanim-home-automation && ./deploy.sh
```

That injects a line equivalent to:

```text
0 5 * * * cd /home/pi/git/local-zmanim-home-automation && uv run python3 shabbat-prepare.py >> shabbat.log 2>&1
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
