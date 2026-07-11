#!/usr/bin/env python

from shabbat_prep_tools import play_mp3, open_log
import sys

logger = open_log(sys.argv[0])

url = 'http://192.168.1.11/shavua-tov.mp3'
play_mp3(url=url,
         volume=5)
print('ok')
