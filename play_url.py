#!/usr/bin/env python
import sys
import argparse

sys.path.insert(0, "/home/dov/git/local-zmanim-home-automation")

from shabbat_prep_tools import play_mp3, open_log

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Play MP3 URL on Google Home speaker")
  parser.add_argument("url", help="URL of MP3 file to play")
  parser.add_argument("--volume", "-v", type=int, default=5, help="Volume level (0-10, default: 5)")
  parser.add_argument("--log", "-l", action="store_true", help="Enable logging")
  args = parser.parse_args()

  if args.log:
    open_log(sys.argv[0])

  play_mp3(url=args.url, volume=args.volume)
