#!/usr/bin/env python3

from shabbat_prep_tools import play_mp3, open_log, check_is_up, mqtt_query, send_msg, get_athmos_power_draw
import sys

kumkum_topic = 'kumkum'
#kumkum_topic = 'tasmota_sonoff_hd_power'
audio_fail = 'shaa-kumkum-lo-mechubar.mp3'
audio_success = 'kolhakavod-kumkum.mp3'
audio_wrong_power = 'forgot-to-put-kumkum-in-boil-mode.mp3'

logger = open_log(sys.argv[0])
reason = None
try:
  is_up= mqtt_query(kumkum_topic)=='ON'
  print(f'{is_up=}')
  if not is_up:
    reason = 'Switch connected but not turned on'

except TimeoutError:
  is_up = False
  reason = 'Timeout error'

if reason:
  send_msg(f'shabbat-pre-1h: {reason}')
  play_mp3(f'http://192.168.1.11/{audio_fail}')
else:
  power_draw = get_athmos_power_draw(num_measurements=5)
  print(f'{power_draw=}')
  if power_draw is not None:
    if power_draw < 40 or power_draw > 100:
      play_mp3(f'http://192.168.1.11/{audio_success}')
      send_msg(f'kumkum ok!')
    else:
      play_mp3(f'http://192.168.1.11/{audio_wrong_power}')
      send_msg(f'kumkum power wrong: {power_draw}W')
  else:
    play_mp3(f'http://192.168.1.11/{audio_fail}')
    send_msg('kumkum power draw failed')
print(f'{is_up=}')
# TBD

#url = 'http://192.168.1.11/shavua-tov.mp3'
#play_mp3(url=url,
#         volume=5)

print('ok')

