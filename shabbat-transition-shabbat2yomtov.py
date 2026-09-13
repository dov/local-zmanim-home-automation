#!/usr/bin/env python

from shabbat_prep_tools import play_mp3, open_log, send_msg
import sys

logger = open_log(sys.argv[0])

# Shabbat is ending directly into a Yom Tov (no gap in melacha restrictions):
# play the entry-into-chag tune, but do NOT turn off the kumkum since the
# Yom Tov continues right on.
url = 'http://192.168.1.11/hamavdil-marokai.mp3' # placeholder - swap in your own tune
play_mp3(url=url, volume=7)

send_msg('Shabbat -> Chag: kumkum left as-is, Yom Tov continues.')
print('ok')
