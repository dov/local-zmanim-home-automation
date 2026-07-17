#!/usr/bin/env python

from shabbat_prep_tools import play_mp3, open_log, mqtt_query
import sys

logger = open_log(sys.argv[0])

#url = 'http://192.168.1.11/shavua-tov.mp3'
url = 'http://192.168.1.11/hamavdil-marokai.mp3'
play_mp3(url=url,
         volume=7)

# Turn off the kumkum
mqtt_query('kumkum', action='OFF')
print('ok')
