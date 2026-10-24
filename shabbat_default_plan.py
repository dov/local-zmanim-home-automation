#!/usr/bin/env python3
######################################################################
#  Default Shabbat / Yom Tov device plan.
#
#  This is the fallback for when ~/scripts/build_shab_at was not run by
#  hand.  All times are derived from the zmanim of the observance block
#  (candle lighting, chatzot, tzais) instead of fixed clock times, so the
#  plan follows the season automatically.  The seasonal switches and the
#  offsets are all in the CONFIGURATION section below.
#
#  The module is pure planning (no at/atq calls); see
#  shabbat-ensure-plan.py for detecting a manual plan and installing.
######################################################################

import importlib.util
import os
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from zmanim.zmanim_calendar import ZmanimCalendar


def H(hours=0, minutes=0):
  return timedelta(hours=hours, minutes=minutes)


######################################################################
#  CONFIGURATION
######################################################################

# Seasons are ((month, day), (month, day)), inclusive, and may wrap over
# the new year.  None means all year round.  A season is tested against
# the date of the day (or night) that is being planned.

# Kitchen A/C during Shabbat day.
KITCHEN_AC_SEASON = ((4, 15), (11, 15))
# Kitchen A/C also on the entry evening (dinner).  Summer only.
KITCHEN_AC_NIGHT_SEASON = ((6, 1), (9, 30))

# Bedroom A/C.  Summer only!  Change the dates here.
BEDROOM_AC_SEASON = ((6, 1), (9, 30))

# Plata kept on from entry to after lunch (cholent) instead of only
# around the meals.
PLATA_CHAMIN_SEASON = ((11, 1), (3, 31))

# The Triss (esp_triss.py).  Unknown seasonality, so all year.
TRISS_SEASON = None

# --- Offsets.  "chatzot" is solar noon, "entry" the start of the night
# --- (candle lighting for the first night, tzais of the previous day
# --- for later nights in a chained Yom Tov/Shabbat block).

# Kitchen A/C: cycles on KITCHEN_AC_ON out of every KITCHEN_AC_PERIOD.
KITCHEN_AC_DAY_START = -H(3)            # relative to chatzot
KITCHEN_AC_DAY_TAIL = H(2, 10)          # after tzais of the last day only
KITCHEN_AC_PERIOD = H(0, 30)
KITCHEN_AC_ON = H(0, 20)
KITCHEN_AC_NIGHT_START = H(1, 30)       # relative to entry
KITCHEN_AC_NIGHT_END = H(3, 30)         # relative to entry

# Bedroom A/C: night sleep (start is clamped to a clock window) and nap.
BEDROOM_AC_NIGHT_START = H(4)           # relative to entry
BEDROOM_AC_NIGHT_EARLIEST = time(21, 30)
BEDROOM_AC_NIGHT_LATEST = time(23, 0)
BEDROOM_AC_NIGHT_LENGTH = H(2)
BEDROOM_AC_NAP_START = H(2)             # relative to chatzot
BEDROOM_AC_NAP_LENGTH = H(3)
BEDROOM_AC_NAP_END_BEFORE_TZAIS = H(0, 20)  # never run into the exit

# Plata.  ON is re-sent every PLATA_STEP; OFF is sent 3 times at the end.
PLATA_STEP = H(0, 15)
PLATA_START = H(0, 3)                   # relative to entry
PLATA_DINNER_LENGTH = H(3, 30)
PLATA_LUNCH_START = -H(1, 30)           # relative to chatzot
PLATA_LUNCH_END = H(1, 30)
PLATA_SEUDA3_START = -H(1, 52)          # relative to tzais of that day
PLATA_SEUDA3_END = -H(0, 22)
PLATA_CHAMIN_END = H(2, 30)             # relative to chatzot

# Triss: ON every 15 minutes in the afternoon, then OFF 8 times.
TRISS_STEP = H(0, 15)
TRISS_START = H(0, 33)                  # relative to chatzot
TRISS_END = H(4, 3)
TRISS_OFF_REPEATS = 8

# Bulb (noa): ON every 30 minutes from before dusk to bedtime.
BULB_STEP = H(0, 30)
BULB_BEFORE_DUSK = H(2)                 # dusk = candle lighting of that date
BULB_OFF_TIME = time(23, 30)

# Etty's lamp: ON every hour until after midnight.
ETTY_LAMP_STEP = H(1)
ETTY_LAMP_NIGHT_START = H(0, 34)        # relative to entry (first night)
ETTY_LAMP_DAY_START = H(2, 34)          # relative to chatzot (later days)
ETTY_LAMP_UNTIL = time(1, 0)            # next morning

# --- Commands.  `at` jobs created from cron/at get a minimal environment,
# --- so every command is absolute and gets an explicit environment.

JOB_ENV = {
  'PATH': '/usr/local/bin:/home/dov/scripts:/usr/bin:/bin',
  'PYTHONPATH': '/usr/local/lib/python3/site-packages:'
                '/usr/local/lib/python3.11/site-packages',
}

DEVICE_COMMANDS = {
  'kitchen_ac':  '/usr/local/bin/set_electra.py',
  'bedroom_ac':  '/home/dov/scripts/set_bedroom_electra.py',
  'plata':       '/usr/local/bin/esp-power-th16.py',
  'triss':       '/home/dov/scripts/esp_triss.py',
  'bulb':        '/home/dov/scripts/set_noa_bulb',
  'etty_lamp':   '/home/dov/scripts/etty_bedstand_lamp.py',
}

# Script names that, if found in a queued job inside the observance
# window, mean that a plan was already scheduled by hand.  Includes
# devices that build_shab_at has commented out right now.
MANUAL_PLAN_MARKERS = sorted(
  {os.path.basename(c) for c in DEVICE_COMMANDS.values()}
  | {'set_electra.py', 'set_noa_light.py', 'set_bedroom_bulb',
     'esp-power-mirpeset.py', 'esp-power.py'})

# Written as the first line of every job of the default plan.
PLAN_TAG = '# shabbat-default-plan'

######################################################################
#  END OF CONFIGURATION
######################################################################


def in_season(day, season):
#  if season is None:
#    return True
#  start, end = season
#  key = (day.month, day.day)
#  if start <= end:
#    return start <= key <= end
#  return key >= start or key <= end
  return False # False by default


def load_prepare():
  """The coordinator has a dash in its name; load it by path so that the
  observance logic is shared instead of duplicated."""
  path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      'shabbat-prepare.py')
  spec = importlib.util.spec_from_file_location('shabbat_prepare', path)
  mod = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(mod)
  return mod


@dataclass
class Day:
  date: date
  chatzot: datetime
  dusk: datetime           # candle lighting of that date
  tzais: datetime
  kind: str                # 'shabbat', 'yomtov' or 'both'


@dataclass
class Block:
  start: datetime          # candle lighting of the first night
  end: datetime            # tzais of the last day
  nights: list = field(default_factory=list)  # entry of each night
  days: list = field(default_factory=list)    # Day, aligned with nights


def make_block(start, end, prepare):
  """Expand the (start, end) of get_observance_block() into the nights and
  days of the chained block."""
  block = Block(start=start, end=end)
  d = start.date() + timedelta(days=1)
  while prepare.is_restricted_day(d):
    cal = ZmanimCalendar(geo_location=prepare.location, date=d)
    block.days.append(Day(date=d,
                          chatzot=cal.chatzos(),
                          dusk=cal.candle_lighting(),
                          tzais=cal.tzais(),
                          kind=prepare.classify_restricted_day(d)))
    d += timedelta(days=1)
  block.nights = [start] + [day.tzais for day in block.days[:-1]]
  return block


@dataclass(order=True, frozen=True)
class Job:
  when: datetime
  device: str
  state: int
  note: str = field(default='', compare=False)

  def command(self):
    env = ' '.join(f'{k}={v}' for k, v in JOB_ENV.items())
    return f'{env} {DEVICE_COMMANDS[self.device]} {self.state}'


def _floor(dt):
  return dt.replace(second=0, microsecond=0)


def _clock(day, t, tz):
  return datetime.combine(day, t, tzinfo=tz)


class Planner:
  """Collects jobs.  Nothing earlier than `now`+1min is scheduled; a
  window that is already open is joined right away (catch-up) so that a
  fallback at entry-0.5h still turns on things that should be on."""

  def __init__(self, now):
    self.min_time = _floor(now) + H(0, 1)
    self.jobs = set()

  def add(self, when, device, state, note):
    when = _floor(when)
    if when >= self.min_time:
      self.jobs.add(Job(when, device, state, note))

  def pulses(self, device, start, end, step, off_repeats, note):
    """ON every `step` in [start, end), then OFF `off_repeats` times."""
    t = _floor(start)
    if t < self.min_time < end:
      t = self.min_time
    while t < end:
      self.add(t, device, 1, note)
      t += step
    for _ in range(off_repeats):
      self.add(t, device, 0, note + ' (off)')
      t += step

  def cycle(self, device, start, end, period, on_length, note):
    """ON for `on_length` out of every `period` in [start, end)."""
    t = _floor(start)
    if t < self.min_time < end:
      t = self.min_time
    while t < end:
      self.add(t, device, 1, note)
      self.add(min(t + on_length, end), device, 0, note)
      t += period

  def window(self, device, start, end, note):
    """ON at start and OFF at end."""
    start = max(_floor(start), self.min_time)
    if start >= end:
      return
    self.add(start, device, 1, note)
    self.add(end, device, 0, note)


def build_plan(block, now):
  """Returns the sorted list of Jobs for the block, from `now` onwards."""
  p = Planner(now)
  tz = block.start.tzinfo
  pairs = list(zip(block.nights, block.days))
  last = block.days[-1]

  # Evenings of the erev day and of every restricted day (for light).
  evenings = [(block.start.date(), block.start)] + \
             [(d.date, d.dusk) for d in block.days]

  for entry, day in pairs:
    # --- Kitchen A/C
    if in_season(day.date, KITCHEN_AC_NIGHT_SEASON):
      p.cycle('kitchen_ac', entry + KITCHEN_AC_NIGHT_START,
              entry + KITCHEN_AC_NIGHT_END,
              KITCHEN_AC_PERIOD, KITCHEN_AC_ON, 'kitchen a/c night')
    if in_season(day.date, KITCHEN_AC_SEASON):
      end = day.tzais + (KITCHEN_AC_DAY_TAIL if day is last else H())
      p.cycle('kitchen_ac', day.chatzot + KITCHEN_AC_DAY_START, end,
              KITCHEN_AC_PERIOD, KITCHEN_AC_ON, 'kitchen a/c day')

    # --- Bedroom A/C
    if in_season(day.date, BEDROOM_AC_SEASON):
      night_start = entry + BEDROOM_AC_NIGHT_START
      night_start = max(night_start,
                        _clock(entry.date(), BEDROOM_AC_NIGHT_EARLIEST, tz))
      night_start = min(night_start,
                        _clock(entry.date(), BEDROOM_AC_NIGHT_LATEST, tz))
      p.window('bedroom_ac', night_start,
               night_start + BEDROOM_AC_NIGHT_LENGTH, 'bedroom a/c night')
      nap_start = day.chatzot + BEDROOM_AC_NAP_START
      nap_end = min(nap_start + BEDROOM_AC_NAP_LENGTH,
                    day.tzais - BEDROOM_AC_NAP_END_BEFORE_TZAIS)
      p.window('bedroom_ac', nap_start, nap_end, 'bedroom a/c nap')

    # --- Plata
    if in_season(day.date, PLATA_CHAMIN_SEASON):
      p.pulses('plata', entry + PLATA_START,
               day.chatzot + PLATA_CHAMIN_END, PLATA_STEP, 3, 'plata chamin')
    else:
      p.pulses('plata', entry + PLATA_START,
               entry + PLATA_START + PLATA_DINNER_LENGTH,
               PLATA_STEP, 3, 'plata dinner')
      p.pulses('plata', day.chatzot + PLATA_LUNCH_START,
               day.chatzot + PLATA_LUNCH_END, PLATA_STEP, 3, 'plata lunch')
#      if day.kind in ('shabbat', 'both'):
#        p.pulses('plata', day.tzais + PLATA_SEUDA3_START,
#                 day.tzais + PLATA_SEUDA3_END, PLATA_STEP, 3, 'plata seuda 3')

    # --- Triss
    if in_season(day.date, TRISS_SEASON):
      p.pulses('triss', day.chatzot + TRISS_START, day.chatzot + TRISS_END,
               TRISS_STEP, TRISS_OFF_REPEATS, 'triss')

  # --- Light bulb and Etty's lamp
  for i, (d, dusk) in enumerate(evenings):
    p.pulses('bulb', dusk - BULB_BEFORE_DUSK,
             _clock(d, BULB_OFF_TIME, tz), BULB_STEP, 3, 'bulb')
    start = (dusk + ETTY_LAMP_NIGHT_START if i == 0
             else block.days[i - 1].chatzot + ETTY_LAMP_DAY_START)
    p.pulses('etty_lamp', start,
             _clock(d + timedelta(days=1), ETTY_LAMP_UNTIL, tz),
             ETTY_LAMP_STEP, 3, 'etty lamp')

  return sorted(p.jobs)


def summarize(jobs):
  """One line per device: job count and the first/last time."""
  lines = []
  for device in DEVICE_COMMANDS:
    mine = [j for j in jobs if j.device == device]
    if mine:
      lines.append(f'{device}: {len(mine)} jobs, '
                   f'{mine[0].when:%a %H:%M} - {mine[-1].when:%a %H:%M}')
  return lines
