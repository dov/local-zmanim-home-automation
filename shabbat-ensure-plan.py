#!/usr/bin/env python3
######################################################################
#  Runs 30 minutes before candle lighting (scheduled by
#  shabbat-prepare.py).  If no device plan was scheduled by hand (e.g.
#  by ~/scripts/build_shab_at), installs the default plan from
#  shabbat_default_plan.py.
#
#  Usage:
#    shabbat-ensure-plan.py                run as the fallback
#    shabbat-ensure-plan.py --when DATE    simulate the erev day DATE
#    shabbat-ensure-plan.py --dry-run      only print what would happen
#    shabbat-ensure-plan.py --force        install even if a manual plan exists
#    shabbat-ensure-plan.py --remove       remove an installed default plan
#                                          (do this before build_shab_at if
#                                          the fallback beat you to it)
######################################################################

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta

from shabbat_prep_tools import open_log, send_msg
import shabbat_default_plan as plan


def atq_jobs():
  """Returns [(job_id, when, body)] for all waiting jobs."""
  env = dict(os.environ, LC_ALL='C')
  out = subprocess.run(['atq'], capture_output=True, text=True, env=env).stdout
  jobs = []
  for line in out.splitlines():
    m = re.match(r'(\d+)\s+(.+?)\s+([a-z=])\s+\S+$', line)
    if not m or m.group(3) == '=':   # '=' is a job that is running right now
      continue
    when = datetime.strptime(m.group(2), '%a %b %d %H:%M:%S %Y').astimezone()
    body = subprocess.run(['at', '-c', m.group(1)], capture_output=True,
                          text=True, env=env).stdout
    jobs.append((int(m.group(1)), when, body))
  return jobs


def split_queue(jobs, since, until):
  """Splits the jobs in [since, until] into (default_plan_jobs, manual_jobs)."""
  ours, manual = [], []
  for job_id, when, body in jobs:
    if not since <= when <= until:
      continue
    if plan.PLAN_TAG in body:
      ours.append(job_id)
    elif any(marker in body for marker in plan.MANUAL_PLAN_MARKERS):
      manual.append(job_id)
  return ours, manual


def install(jobs, block_start, logger):
  tag = f'{plan.PLAN_TAG} block={block_start.isoformat()}'
  for job in jobs:
    when = job.when.astimezone()
    res = subprocess.run(
      ['at', '-M', f'{when:%H:%M}', f'{when:%d.%m.%Y}'],
      input=f'{tag}\n{job.command()}\n', capture_output=True, text=True)
    if res.returncode != 0:
      raise RuntimeError(f'at failed for {job}: {res.stderr}')
  logger.info(f'Installed {len(jobs)} default plan jobs')


def remove(job_ids, logger):
  for job_id in job_ids:
    subprocess.run(['atrm', str(job_id)], check=True)
  logger.info(f'Removed {len(job_ids)} default plan jobs')


def main():
  parser = argparse.ArgumentParser(description='Install the default Shabbat device plan unless a manual one exists.')
  parser.add_argument('--when', help='Erev day to simulate (YYYY-MM-DD)')
  parser.add_argument('--dry-run', action='store_true')
  parser.add_argument('--force', action='store_true')
  parser.add_argument('--remove', action='store_true')
  args = parser.parse_args()

  logger = open_log(sys.argv[0])
  prepare = plan.load_prepare()

  if args.remove:
    ours, _ = split_queue(atq_jobs(), datetime(2000, 1, 1).astimezone(),
                          datetime(2100, 1, 1).astimezone())
    if not args.dry_run:
      remove(ours, logger)
    print(f'{"Would remove" if args.dry_run else "Removed"} {len(ours)} jobs')
    return

  if args.when:
    eval_time = datetime.strptime(args.when, '%Y-%m-%d')
  else:
    eval_time = datetime.now()
  start, end, _ = prepare.get_observance_block(eval_time)
  if not start:
    logger.info('No Shabbat or Yom Tov entry tonight. Nothing to do.')
    return

  # The real run is 30 minutes before entry; a simulation pretends so.
  now = start - timedelta(minutes=30) if args.when else \
        datetime.now().astimezone()
  block = plan.make_block(start, end, prepare)
  ours, manual = split_queue(atq_jobs(), now, end + timedelta(hours=4))
  jobs = plan.build_plan(block, now)
  logger.info(f'Block {start:%a %d.%m %H:%M} - {end:%a %d.%m %H:%M}; '
              f'{len(manual)} manual jobs, {len(ours)} default jobs queued')

  if args.dry_run:
    for job in jobs:
      print(f'{job.when:%a %d.%m %H:%M}  {job.device:<11} {job.state}  {job.note}')
    print(f'\n{len(jobs)} jobs')
    print('\n'.join(plan.summarize(jobs)))
    if manual and not args.force:
      print(f'\nWould NOT install: {len(manual)} manual jobs already queued')
    elif ours:
      print(f'\nWould NOT install: default plan already queued ({len(ours)} jobs)')
    return

  if manual and not args.force:
    logger.info('Manual plan found; not installing the default plan.')
    return
  if ours:
    logger.info('Default plan is already installed.')
    return

  install(jobs, start, logger)
  send_msg('Shabbat: no manual plan found, installed the DEFAULT plan '
           f'({len(jobs)} jobs).\n' + '\n'.join(plan.summarize(jobs)) +
           '\nTo replace it run: shabbat-ensure-plan.py --remove, '
           'then build_shab_at.')


if __name__ == '__main__':
  try:
    main()
  except Exception as e:
    if '--dry-run' not in sys.argv:
      send_msg(f'shabbat-ensure-plan FAILED: {type(e).__name__}: {e}')
    raise
