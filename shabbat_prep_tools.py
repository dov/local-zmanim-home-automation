#!/usr/bin/env python

######################################################################
#  Tools for checking ip things.
######################################################################

import platform
import subprocess
import os
import sys
import time
import threading
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
import telegram
from telegram import Bot
import asyncio
from telegram.constants import ParseMode
from telegram.ext import Application
import json
import pychromecast
from crontab import CronTab
from datetime import datetime
import logging

logger = None
js = json.load(open('/home/dov/git/GrobBot/bot_config.json'))
bot_token=js['token']
me_user_id = js['user']

def check_is_up(hostname, timeout_in_ms = 500):
  """
  Checks if a host is up using the system's native ping binary.
  Does not require root privileges.
  """
  logger.info(f'check_is_up({hostname=}, {timeout_in_ms=}')
  is_windows = platform.system().lower() == "windows"
  param = "-n" if is_windows else "-c"
  timeout_param = "-w" if is_windows else "-W"
  timeout_val = timeout_in_ms if is_windows else timeout_in_ms/1000. # Windows uses milliseconds, Unix uses seconds
  
  command = ["ping", param, "1", timeout_param, str(timeout_val), hostname]
  
  try:
    # Run the command. If return code is 0, the host is up.
    subprocess.check_output(command, stderr=subprocess.STDOUT)
    return True
    
  except subprocess.CalledProcessError as e:
    # returncode == 1: Ping completed but host was unreachable/timed out.
    # returncode == 2: Unix ping often uses 2 for unknown host errors (DNS failure).
    if e.returncode in (1, 2):
      return False
    # If it's any other non-zero return code, re-raise it as it's an unexpected system issue
    raise
    
  except FileNotFoundError:
    # Triggered if the 'ping' binary itself is missing from the system PATH
    raise RuntimeError("The system 'ping' binary could not be found in the PATH.")


def mqtt_query(mqtt_id='kumkum',
               topic='power',
               host='192.168.1.11',
               port=1883,
               user=None,
               password=None,
               timeout=1.0,
               action=None):
  """
  Queries or sets the status of a Tasmota MQTT device.
  
  Parameters:
    mqtt_id (str): The MQTT device module ID.
    topic (str): The sub-topic suffix (e.g., 'POWER' or 'power').
    host (str): MQTT broker hostname or IP.
    port (int): MQTT broker port.
    user (str): MQTT username (optional).
    password (str): MQTT password (optional).
    timeout (float): Timeout in seconds waiting for the response.
    action (str): Explicit action to send: 'ON', 'OFF', or None to just query.
    
  Returns:
    str: The string payload response from the status topic (e.g., 'ON' or 'OFF').
    
  Raises:
    ConnectionError: If the connection to the broker fails.
    TimeoutError: If the device doesn't respond within the timeout window.
  """
  logger.info(
    "MQTT query initiated: id=%s, topic=%s, host=%s, port=%d, user=%s, timeout=%.1fs, action=%s",
    mqtt_id,
    topic,
    host,
    port,
    user,
    timeout,
    action
  )

  # Normalize topic formatting to match Tasmota standard uppercase structure
  topic_upper = topic.upper()
  status_topic = f"stat/{mqtt_id}/{topic_upper}"
  cmnd_topic = f"cmnd/{mqtt_id}/{topic_upper}"

  result_payload = {}
  got_result = threading.Event()
  connection_failed = threading.Event()

  def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code != 0:
      connection_failed.set()
      got_result.set()
      return
    client.subscribe(status_topic)

  def on_message(client, userdata, msg):
    if msg.topic == status_topic:
      result_payload['payload'] = msg.payload.decode('utf-8')
      got_result.set()

  client = mqtt.Client(CallbackAPIVersion.VERSION2)
  if user:
    client.username_pw_set(user, password)
  
  client.on_connect = on_connect
  client.on_message = on_message

  try:
    client.connect(host, port, 60)
  except Exception as e:
    raise ConnectionError(f"Could not connect to MQTT broker at {host}:{port}: {e}")

  client.loop_start()
  
  # Brief sleep to allow background thread to negotiate connection/subscription
  time.sleep(0.1)

  if connection_failed.is_set():
    client.loop_stop()
    raise ConnectionError(f"MQTT broker rejected connection with code status.")

  # If action is provided, forward it. Otherwise, send empty payload to query status.
  payload = action if action in ('ON', 'OFF') else ''
  client.publish(cmnd_topic, payload=payload)

  if not got_result.wait(timeout=timeout):
    client.loop_stop()
    raise TimeoutError(f"Timeout waiting for response from {mqtt_id} on topic {status_topic}.")

  client.loop_stop()
  
  if connection_failed.is_set():
    raise ConnectionError("MQTT broker connection dropped during execution.")

  return result_payload.get('payload', '')


# Your actual Telegram Bot Token from @BotFather
BOT_TOKEN = bot_token

async def send_telegram_message(message='', parse_mode='HTML', chat_id=bot_token):
  """
  Sends a message to a Telegram chat using the latest async python-telegram-bot.
  """
  logger.info(f'send_telegram_message({message=},{parse_mode=},{chat_id=})')

  if not message:
    return

  # Use the modern Application builder to safely initialize the bot lifecycle
  app = Application.builder().token(BOT_TOKEN).build()
  
  # Initialize the application background resources
  await app.initialize()
  
  try:
    await app.bot.send_message(
      chat_id=chat_id,
      text=message,
      parse_mode=parse_mode
    )
  finally:
    # Always clean up and close network connections safely
    await app.shutdown()

def send_msg(msg):
  # asyncio.run handles execution of the top-level async coroutine
  asyncio.run(send_telegram_message(
    message=msg,
    parse_mode=ParseMode.HTML,
    chat_id=me_user_id
  ))
  
def play_mp3(url='http://192.168.1.11/shavua-tov.mp3',
            volume=5):
  logger.info(f'play_mp3({url=},{volume=})')
  # Cleaned up: Removed the deprecated discovery functions. 
  # get_listed_chromecasts natively boots a background CastBrowser.
  chromecasts, browser = pychromecast.get_listed_chromecasts(friendly_names=["Family Room speaker"])
  
  if not chromecasts:
    print("Speaker not found.")
    browser.stop_discovery()
    return

  cast = chromecasts[0]
  
  # 1. Wait for connection block
  cast.wait()
  
  # 2. Set the volume 
  volume_float = min(max(volume / 10.0, 0.0), 1.0)
  cast.set_volume(volume_float)
  
  # 3. Bind the media controller and ensure it's ready
  mc = cast.media_controller
  mc.block_until_active(timeout=5)
  
  # 4. Retry loop to ensure the command is accepted
  max_attempts = 3
  for attempt in range(max_attempts):
    mc.play_media(url, 'audio/mpeg')
    
    # Wait a moment to let the state update
    time.sleep(2.0) 
    
    # Check if the player has successfully responded
    if mc.status.player_state in ['PLAYING', 'BUFFERING', 'PAUSED']:
      break
  else:
    print("Failed to start playback after multiple attempts.")
    
  # Always shut down the background browser when done setting up
  browser.stop_discovery()

def open_log(script_name):
  global logger
  LOG_FILE = os.path.expanduser("~/log/shabbat-prepare.log")
  
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
  logger.info(f'Running {script_name} on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
  return logger


# Example usage:
if __name__ == "__main__":
  open_log(sys.argv[0])
  try:
    status = mqtt_query(mqtt_id='tasmota_sonoff_hd_power', topic='power')
    print(f"Device Status: {status}")
  except (ConnectionError, TimeoutError) as err:
    print(f"Error executing MQTT ping: {err}", file=sys.stderr)

  print(f'{check_is_up("192.168.1.11")=}')
  print(f'{check_is_up("192.168.1.12")=}')

  HTML_MSG = "Hello from <b>Python</b>! This is a test message."
  
#  # asyncio.run handles execution of the top-level async coroutine
#  asyncio.run(send_telegram_message(
#    message=HTML_MSG,
#    parse_mode=ParseMode.HTML,
#    chat_id=me_user_id
#  ))

#  play_mp3()

  print('ok')
  

