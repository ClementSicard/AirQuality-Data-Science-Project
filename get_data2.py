import sys
import time
#import thingspeak
import datetime
import csv
import Adafruit_DHT
from sps30 import SPS30
from time import sleep
from urllib.request import urlopen

#ThingsSpeak credentials
#myAPI = 'XXXXXXXXXX' #Add your API Key
#baseURL = 'https://api.thingspeak.com/update?api_key=%s' % myAPI

sps = SPS30(1)

if sps.read_article_code() == sps.ARTICLE_CODE_ERROR:
    raise Exception("ARTICLE CODE CRC ERROR!")
else:
    print("ARTICLE CODE: " + str(sps.read_article_code()))

if sps.read_device_serial() == sps.SERIAL_NUMBER_ERROR:
    raise Exception("SERIAL NUMBER CRC ERROR!")
else:
    print("DEVICE SERIAL: " + str(sps.read_device_serial()))

sps.set_auto_cleaning_interval(604800) # default 604800, set 0 to disable auto-cleaning

sps.device_reset() # device has to be powered-down or reset to check new auto-cleaning interval

if sps.read_auto_cleaning_interval() == sps.AUTO_CLN_INTERVAL_ERROR: # or returns the interval in seconds
    raise Exception("AUTO-CLEANING INTERVAL CRC ERROR!")
else:
    print("AUTO-CLEANING INTERVAL: " + str(sps.read_auto_cleaning_interval()))


sensor = Adafruit_DHT.DHT22

# Set to your GPIO pin
pin    = 4

sleep(5)

sps.start_measurement()

sleep(5)

while not sps.read_data_ready_flag():
    sleep(0.25)
    if sps.read_data_ready_flag() == sps.DATA_READY_FLAG_ERROR:
        raise Exception("DATA-READY FLAG CRC ERROR!")

if sps.read_measured_values() == sps.MEASURED_VALUES_ERROR:
    raise Exception("MEASURED VALUES CRC ERROR!")
else:
    print ("PM1.0 Value in µg/m3: " + str(sps.dict_values['pm1p0']))
    print ("PM2.5 Value in µg/m3: " + str(sps.dict_values['pm2p5']))
    print ("PM4.0 Value in µg/m3: " + str(sps.dict_values['pm4p0']))
    print ("PM10.0 Value in µg/m3: " + str(sps.dict_values['pm10p0']))
    #print ("NC0.5 Value in 1/cm3: " + str(sps.dict_values['nc0p5']))    # NC: Number of Concentration
    #print ("NC1.0 Value in 1/cm3: " + str(sps.dict_values['nc1p0']))
    #print ("NC2.5 Value in 1/cm3: " + str(sps.dict_values['nc2p5']))
    #print ("NC4.0 Value in 1/cm3: " + str(sps.dict_values['nc4p0']))
    #print ("NC10.0 Value in 1/cm3: " + str(sps.dict_values['nc10p0']))
    #print ("Typical Particle Size in µm: " + str(sps.dict_values['typical']))

sps.stop_measurement()

sps.start_fan_cleaning()


humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)

def get_temp():
    temp = round((temperature),2)
    temp = str(temp)
    return(temp)

def get_hum():
    hum = round((humidity),2)
    hum = str(hum)
    return (hum)

def get_pm1():
    variable = "pm1"
    unit = "ug/m3"
    data = sps.dict_values['pm1p0']
    data = round((data),2)
    return(data)

def get_pm25():
    variable = "pm25"
    unit = "ug/m3"
    data = sps.dict_values['pm2p5']
    data = round((data),2)
    return(data)

def get_pm10():
    variable = "pm10"
    unit = "ug/m3"
    data = sps.dict_values['pm10p0']
    data = round((data),2)
    return(data)

def date_now():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    today = str(today)
    return(today)

def time_now():
    now = datetime.datetime.now().strftime("%H:%M:%S")
    now = str(now)
    return(now)

# Specify the fields for ThingsSpeak and send data
#f = urlopen(baseURL + '&field1=%s&field2=%s&field3=%s&field4=%s&field5=%s' % (get_temp(), get_hum(), get_pm1(), get_pm25(), get_pm10())) 
#f.read()
#f.close()

print('Temperature in Celsius:',get_temp())
print('Humidity in %:', get_hum())
print('PM1 value in µg/m3:',get_pm1())
print('PM2.5 value in µg/m3:',get_pm25())
print('PM10 value in µg/m3:',get_pm10())
print('Date:',date_now())
print('Time:',time_now())

