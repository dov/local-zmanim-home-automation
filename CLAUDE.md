# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a standalone, zero-network-dependency Python system for Raspberry Pi that automates smart home tasks around Shabbat and Jewish Holidays (*Yom Tov*). The system uses astronomical solar algorithms to detect observances and dynamically schedules custom execution scripts via the system `at` job scheduler.

## Core Architecture

1. **Daily Coordinator** (`shabbat-prepare.py`): Runs daily at 05:00 AM to determine if a Shabbat or Yom Tov occurs that evening.
2. **Observance Detection**: Uses the `zmanim` library to calculate precise local Candle Lighting and Tzais times based on geographic coordinates.
3. **Job Scheduling**: Uses an `AtJobScheduler` class to schedule pre/post scripts relative to observance start/end times.
4. **Child Scripts**: Optional execution scripts that run at specific times relative to the observance:
   - `shabbat-pre-1h.py`: 1 hour before Candle Lighting
   - `shabbat-pre-0.5h.py`: 30 minutes before Candle Lighting
   - `shabbat-pre-0h.py`: Exactly at Candle Lighting
   - `shabbat-post-0h.py`: Exactly at Tzais/Havdalah (end of the whole chained block)
   - `shabbat-post-1h.py`: 1 hour after Tzais/Havdalah
   - `shabbat-transition-shabbat2yomtov.py`: Internal Tzais where Shabbat ends directly into a Yom Tov (chag-entry tune, kumkum left on)
   - `shabbat-transition-yomtov2shabbat.py`: Internal Tzais where a Yom Tov ends directly into Shabbat (chag-entry tune, kumkum left on)
5. **Holiday chaining (Israeli convention)**: Shabbat and Yom Tov are detected via the same restricted-day logic and chained into one block whenever adjacent (e.g. Shabbat immediately followed by a Yom Tov). `get_observance_block()` in `shabbat-prepare.py` returns the overall start/end plus a list of internal Shabbat↔YomTov transitions within the chain; only those internal boundaries trigger the `shabbat-transition-*.py` scripts, not `shabbat-post-0h.py`.

## Key Components

### Main Coordinator Script
- File: `shabbat-prepare.py`
- Responsible for detecting observances and scheduling jobs
- Uses `zmanim` and `JewishCalendar` to determine religious observances
- Chains adjacent holy days into a single unified block

### Tools Library
- File: `shabbat_prep_tools.py`
- Contains utility functions for:
  - Network connectivity checks (`check_is_up`)
  - MQTT device communication (`mqtt_query`)
  - Telegram messaging (`send_telegram_message`)
  - Chromecast audio playback (`play_mp3`)
  - Power consumption monitoring (`get_athmos_power_draw`)

### Deployment Script
- File: `deploy.sh`
- Uses `uv` for Python environment management
- Runs in-place from the git checkout it lives in (`git pull` + builds `.venv` there) — no files are copied to `~/scripts`
- Sets up cron job for daily execution at 05:00 AM, running `shabbat-prepare.py` out of the checkout

## Common Development Tasks

### Running Tests/Simulations
Test specific dates without waiting for the daily cron:
```bash
./shabbat-prepare.py --when 2026-07-03
```

### Checking Scheduled Jobs
View currently scheduled `at` jobs:
```bash
atq
```

### Viewing Job Details
See details of a specific job:
```bash
at -c <job_number>
```

### Deployment
Deploy the system to the Raspberry Pi:
```bash
./deploy.sh
```

### Monitoring Logs
Check execution logs:
```bash
tail -f ~/log/shabbat-prepare.log
```

## Dependencies

Key Python packages used in this project:
- `zmanim`: Astronomical calculations for Jewish times
- `python-crontab`: Cron table manipulation
- `paho-mqtt`: MQTT protocol support
- `python-telegram-bot`: Telegram messaging
- `pychromecast`: Google Chromecast control

## Configuration

Geographic coordinates and other settings are hardcoded in `shabbat-prepare.py`:
- Latitude: 31.897964 (Rehovot)
- Longitude: 34.808122 (Rehovot)
- Elevation: 49 meters
- Timezone: Asia/Jerusalem

MQTT and Telegram credentials are stored in `/home/dov/git/GrobBot/bot_config.json`.