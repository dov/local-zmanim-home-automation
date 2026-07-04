#!/usr/bin/env python3
import os
import sys
import argparse
import logging
from datetime import datetime, timedelta, date
from crontab import CronTab

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

SCRIPT_MAPPING = [
    {"name": "shabbat-pre-1h.py",  "anchor": "start", "offset_hours": -1},
    {"name": "shabbat-pre-0h.py",  "anchor": "start", "offset_hours": 0},
    {"name": "shabbat-post-0h.py", "anchor": "end",   "offset_hours": 0},
    {"name": "shabbat-post-1h.py", "anchor": "end",   "offset_hours": 1}
]

# --- LOGGING SETUP ---
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

# Initialize Geolocation for Rehovot
location = GeoLocation("Rehovot", LAT, LON, TZ_NAME, elevation=ELEVATION)

def is_observance_day(check_date: date) -> bool:
    """Returns True if the date is a Friday or a Yom Tov that restricts work/requires candle lighting."""
    # Fridays are always an entry to an observance
    if check_date.weekday() == 4:  # 4 = Friday
        return True
    
    # Check for Holidays using JewishCalendar
    j_cal = JewishCalendar(datetime_date=check_date, in_israel=True)
    
    # is_yom_tov_assur_bemelacha tracks days with Shabbat-like restrictions (Entry nights)
    if j_cal.is_yom_tov_assur_bemelacha():
        return True
        
    return False

def get_observance_block(target_date: datetime):
    """
    Scans a 3-day window using ZmanimCalendar. 
    If an observance begins tonight, it chains adjacent holy days and returns (start_datetime, end_datetime).
    """
    start_date = target_date.date()
    
    # If an observance doesn't begin tonight, we do nothing today.
    if not is_observance_day(start_date):
        return None, None

    # 1. Find the exact candle lighting time for tonight
    cal_start = ZmanimCalendar(geo_location=location, date=start_date)
    union_start = cal_start.candle_lighting()
    
    # 2. Trace forward day-by-day to find when the continuous block ends
    # We inspect the upcoming days to find when a day is no longer Shabbat/Yom Tov
    current_inspect_date = start_date + timedelta(days=1)
    
    # Loop to find the last consecutive day of this holiday/Shabbat chain
    while True:
        # If the day we are checking is a holiday or a Saturday, the observance continues.
        # Note: Saturday is weekday 5 in Python (Mon=0, Tue=1... Sat=5, Sun=6)
        is_shabbat = (current_inspect_date.weekday() == 5)
        
        j_cal = JewishCalendar(datetime_date=current_inspect_date, in_israel=True)
        is_yom_tov = j_cal.is_yom_tov_assur_bemelacha()
        
        if is_shabbat or is_yom_tov:
            # The chain is active; check the next calendar day
            current_inspect_date += timedelta(days=1)
        else:
            # We hit a weekday! The block ended on the previous night.
            break
            
    # 3. Calculate Havdalah (tzais) on the night the block terminates
    # The exit Havdalah occurs on the evening of the first day that is NOT an observance day
    cal_end = ZmanimCalendar(geo_location=location, date=current_inspect_date)
    union_end = cal_end.tzais()
    
    return union_start, union_end

def update_cron_jobs(start_time, end_time):
    """Purges previous dynamic jobs and schedules existing target scripts."""
    try:
        cron = CronTab(user=True)
    except Exception as e:
        logger.error(f"Could not access user crontab: {e}")
        sys.exit(1)
    
    # Remove previous dynamic entries
    cron.remove_all(comment="shabbat-automation")
    
    for item in SCRIPT_MAPPING:
        script_path = os.path.join(SCRIPT_DIR, item["name"])
        
        if not os.path.exists(script_path):
            logger.warning(f"Skipping schedule: '{item['name']}' not found in {SCRIPT_DIR}")
            continue
            
        anchor_time = start_time if item["anchor"] == "start" else end_time
        target_time = anchor_time + timedelta(hours=item["offset_hours"])
        
        cmd = f"/usr/bin/python3 {script_path}"
        
        job = cron.new(command=cmd, comment="shabbat-automation")
        job.setall(target_time.minute, target_time.hour, target_time.day, target_time.month, "*")
        
        logger.info(f"Successfully scheduled {item['name']} for {target_time.strftime('%Y-%m-%d %H:%M')}")
        
    cron.write()
    logger.info("Crontab rewrite completed successfully.")

def main():
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

    # Process block using local Zmanim engine calculations
    start, end = get_observance_block(eval_time)
    
    if start and end:
        logger.info(f"Observance sequence detected!")
        logger.info(f"Union Start (Candle Lighting): {start.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Union End (Tzais/Havdalah):   {end.strftime('%Y-%m-%d %H:%M:%S')}")
        update_cron_jobs(start, end)
    else:
        logger.info("No Shabbat or Yom Tov entry occurs tonight. Exiting cleanly.")
        sys.exit(0)

if __name__ == "__main__":
    main()
