#!/usr/bin/python

# Google Spreadsheet DHT Sensor Data-logging Example

# Depends on the 'gspread' package being installed.  If you have pip installed
# execute:
# sudo pip install gspread

# Copyright (c) 2014 Adafruit Industries
# Author: Tony DiCola

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from __future__ import print_function
import sys
import time
import datetime

import Adafruit_DHT
import gspread
import paho.mqtt.client as mqtt
import json

def warning(*objs):
  print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\tWARNING: ", *objs, file=sys.stderr)
def info(*objs):
  print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\tINFO: ", *objs, file=sys.stderr)


# Type of sensor, can be Adafruit_DHT.DHT11, Adafruit_DHT.DHT22, or Adafruit_DHT.AM2302.
DHT_TYPE = Adafruit_DHT.DHT22

# Example of sensor connected to Raspberry Pi pin 23
#DHT_PIN  = 23
# Example of sensor connected to Beaglebone Black pin P8_11
DHT_PIN = 'P8_12'

# Google Docs account email, password, and spreadsheet name.
GDOCS_EMAIL = 'smtg@gmail.com'
# your google docs account email address'
GDOCS_PASSWORD = 'secret'
GDOCS_SPREADSHEET_NAME = 'a-spreadsheet'
MQTT_TOPIC_TEMP = 'w112/sensors/temperature/kitchen'
MQTT_TOPIC_RESOLUTION = MQTT_TOPIC_TEMP +'/resolution'
MQTT_BROKER_HOST = "localhost"
# How long to wait (in seconds) between measurements.
FREQUENCY_SECONDS = 30

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, rc):
  info("Connected with result code "+str(rc) + " subscribing to " +MQTT_TOPIC_RESOLUTION)
  # Subscribing in on_connect() means that if we lose the connection and
  # reconnect then subscriptions will be renewed.
  subscribed = client.subscribe(MQTT_TOPIC_RESOLUTION)
  info ('subscribed sucess = '+str(mqtt.MQTT_ERR_SUCCESS == subscribed[0])+' msgID: '+str(subscribed[1]))

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
  info(str(client)+ str(userdata))
  info(msg.topic+" on_message"+msg.payload)
  freqToSet = int(str(msg.payload))
  if freqToSet>0 and freqToSet<3600*24:
    info(msg.topic+" setting freq to "+str(freqToSet))
    FREQUENCY_SECONDS = freqToSet
  else:
    warning(msg.topic+" ignoring msg "+msg.payload)

def on_subscribe(mosq, obj, mid, granted_qos):
  info("[on_subscribe] Subscribed: " + str(mid) + " " + str(granted_qos))

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.on_subscribe = on_subscribe

client.connect(MQTT_BROKER_HOST, 1883, 60)

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
#client.loop_forever()
client.loop_start()

def login_open_sheet(email, password, spreadsheet):
  """Connect to Google Docs spreadsheet and return the first worksheet."""
  try:
    gc = gspread.login(email, password)
    worksheet = gc.open(spreadsheet).sheet1
    return worksheet
  except:
    warning('Unable to login and get spreadsheet.  Check email, password, spreadsheet name.')
    return None
    #sys.exit(1)


info('Logging sensor measurements to {0} every {1} seconds.'.format(GDOCS_SPREADSHEET_NAME, FREQUENCY_SECONDS))
# print 'Press Ctrl-C to quit.'
worksheet = None
while True:
    # Login if necessary.
    if worksheet is None:
      worksheet = login_open_sheet(GDOCS_EMAIL, GDOCS_PASSWORD, GDOCS_SPREADSHEET_NAME)

    # Attempt to get sensor reading.
    humidity, temp = Adafruit_DHT.read(DHT_TYPE, DHT_PIN)
    now = datetime.datetime.now()
    # Skip to the next reading if a valid measurement couldn't be taken.
    # This might happen if the CPU is under a lot of load and the sensor
    # can't be reliably read (timing is critical to read the sensor).
    if humidity is None or temp is None:
      time.sleep(2)
      continue

    #print 'Temperature: {0:0.1f} C'.format(temp)
    #print 'Humidity:    {0:0.1f} %'.format(humidity)

    # Append the data in the spreadsheet, including a timestamp
    try:
      worksheet.append_row((now, temp, humidity))
    except Exception as e:
      # Error appending data, most likely because credentials are stale.
      # Null out the worksheet so a login is performed at the top of the loop.
      warning(e)
      warning('Append error, logging in again')
      worksheet = None
      time.sleep(FREQUENCY_SECONDS)
      continue
    client.publish(MQTT_TOPIC_TEMP, json.dumps({'temp':temp,'hum':humidity,'tstamp':str(now)}))
    # Wait 30 seconds before continuing
    #info('Wrote a row to {0}'.format(GDOCS_SPREADSHEET_NAME))
    info('sleeping for '+str(FREQUENCY_SECONDS))
    time.sleep(FREQUENCY_SECONDS)
