#!/usr/bin/env python3
######################################################################
#  Prepars at jobs to be run around shabbat according to the
#  scripts found.
######################################################################

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta, date
import subprocess
import re

# Import Zmanim components
from zmanim.zmanim_calendar import ZmanimCalendar
from zmanim.hebrew_calendar.jewish_calendar import JewishCalendar
from zmanim.util.geo_location import GeoLocation

# --- CONFIGURATION ---
LAT = 31.897964
LON = 34.808122
ELEVATION = 49
TZ_NAME = "Asia/Jerusalem"

SCRIPT_DIR = os.path.expanduser("~/scripts")
LOG_FILE = os.path.expanduser("~/log/shabbat-prepare.log")

# Initialize Geolocation for Rehovot
location = GeoLocation("Rehovot", LAT, LON, TZ_NAME, elevation=ELEVATION)


SCRIPT_MAPPING = [
    {"name": "shabbat-pre-1h.py",  "anchor": "start", "offset_hours": -1},
    {"name": "shabbat-pre-0.5h.py",  "anchor": "start", "offset_hours": -0.5},
    {"name": "shabbat-pre-0h.py",  "anchor": "start", "offset_hours": 0},
    {"name": "shabbat-post-0h.py", "anchor": "end",   "offset_hours": 0},
    {"name": "shabbat-post-1h.py", "anchor": "end",   "offset_hours": 1}
]

class AtJobScheduler:
    def __init__(self):
        self.jobs = []

    def AddAtJob(self, Cmd, ExecutionTime):
        now = datetime.now().astimezone()
        if ExecutionTime < now:
            logging.info(f"Skipping past time: {ExecutionTime.strftime('%Y-%m-%d %H:%M')}")
            return
        self.jobs.append((Cmd, ExecutionTime))

    def WriteShellFile(self, filepath="/tmp/at-tasks.sh"):
        if not self.jobs:
            logging.info("No jobs to write. Skipping shell file generation.")
            return
        logging.info(f"Writing {len(self.jobs)} at jobs to {filepath}")
        with open(filepath, "w") as f:
            for Cmd, ExecutionTime in self.jobs:
                TimeStr = ExecutionTime.strftime("%H:%M")
                DateStr = ExecutionTime.strftime("%d.%m.%Y")
                f.write(f"echo {Cmd} | at -M {TimeStr} {DateStr}\n")
        logging.info(f"Successfully wrote shell file: {filepath}")

    def ExecuteShellFile(self, filepath="/tmp/at-tasks.sh"):
        if not self.jobs:
            logging.info("No jobs to execute. Skipping shell file execution.")
            return
        try:
            logging.info(f"Executing shell file: {filepath}")
            with open(filepath, "r") as f:
                shell_script = f.read()
            subprocess.run(
                ["bash", "-c", shell_script],
                check=True
            )
            logging.info("Successfully executed all at jobs")
        except subprocess.CalledProcessError as Err:
            logging.error(f"Failed to execute shell file {filepath}. Error: {Err}")


def is_observance_day(check_date: date) -> bool:
    """Returns True if the date is a Friday or a Yom Tov that restricts work/requires candle lighting."""
    if check_date.weekday() == 4:
        return True
    
    j_cal = JewishCalendar(datetime_date=check_date, in_israel=True)
    
    if j_cal.is_yom_tov_assur_bemelacha():
        return True
        
    return False


def get_observance_block(target_date: datetime):
    """
    Scans a 3-day window using ZmanimCalendar. 
    If an observance begins tonight, it chains adjacent holy days and returns (start_datetime, end_datetime).
    """
    start_date = target_date.date()
    
    if not is_observance_day(start_date):
        return None, None

    cal_start = ZmanimCalendar(geo_location=location, date=start_date)
    union_start = cal_start.candle_lighting()
    
    current_inspect_date = start_date + timedelta(days=1)
    
    while True:
        is_shabbat = (current_inspect_date.weekday() == 5)
        
        j_cal = JewishCalendar(datetime_date=current_inspect_date, in_israel=True)
        is_yom_tov = j_cal.is_yom_tov_assur_bemelacha()
        
        if is_shabbat or is_yom_tov:
            current_inspect_date += timedelta(days=1)
        else:
            break
            
    cal_end = ZmanimCalendar(geo_location=location, date=current_inspect_date - timedelta(days=1))
    union_end = cal_end.tzais()
    
    return union_start, union_end


def UpdateAtJobs(start_time, end_time):
    """Purges previous dynamic jobs and schedules existing target scripts."""
    scheduler = AtJobScheduler()
    
    for item in SCRIPT_MAPPING:
        script_path = os.path.join(SCRIPT_DIR, item["name"])
        
        if not os.path.exists(script_path):
            logging.warning(f"Skipping schedule: '{item['name']}' not found in {SCRIPT_DIR}")
            continue
            
        anchor_time = start_time if item["anchor"] == "start" else end_time
        target_time = anchor_time + timedelta(hours=item["offset_hours"])
        
        cmd = f"/home/dov/scripts/.venv/bin/python3 {script_path}"
        
        scheduler.AddAtJob(cmd, target_time)
        
    scheduler.WriteShellFile()
    scheduler.ExecuteShellFile()
    logging.info("At-job queue update completed successfully.")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logger = logging.getLogger("shabbat-prep")
    logger.info('------------------')
    logger.info(f'Running shabbat-prepare.py on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    
    parser = argparse.ArgumentParser(description="Schedule Shabbat/Yom Tov child automation tasks via Crontab.")
    parser.add_argument(
        "--when", 
        type=str, 
        help="Target date string in ISO8601 format (YYYY-MM-DD)"
    )
    args = parser.parse_args()

    if args.when:
        try:
            eval_time = datetime.strptime(args.when, "%Y-%m-%d")
            logger.info(f"Using manual simulation date: {eval_time.strftime('%Y-%m-%d')}")
        except ValueError:
            logger.error(f"Invalid YYYY-MM-DD date string provided: {args.when}")
            sys.exit(1)
    else:
        eval_time = datetime.now()
        logger.info(f"Running daily cron sweep. System date: {eval_time.strftime('%Y-%m-%d')}")

    start, end = get_observance_block(eval_time)
    
    if start and end:
        logger.info(f"Observance sequence detected!")
        logger.info(f"Union Start (Candle Lighting): {start.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Union End (Tzais/Havdalah):   {end.strftime('%Y-%m-%d %H:%M:%S')}")
        UpdateAtJobs(start, end)
    else:
        logger.info("No Shabbat or Yom Tov entry occurs tonight. Exiting cleanly.")
        sys.exit(0)


if __name__ == "__main__":
    main()
