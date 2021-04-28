import sys
import time
import os
import thingspeak
import datetime
import csv
import Adafruit_DHT
from sps30 import SPS30
from time import sleep
from urllib.request import urlopen

# ThingsSpeak credentials
myAPI = 'L50MRPUQ7X1N3J9Z'  # Add your API Key
baseURL = 'https://api.thingspeak.com/update?api_key=%s' % myAPI


pm1, pm25, pm10 = None, None, None
try:
    sps = SPS30(1)

    if sps.read_article_code() == sps.ARTICLE_CODE_ERROR:
        raise Exception("ARTICLE CODE CRC ERROR!")

    if sps.read_device_serial() == sps.SERIAL_NUMBER_ERROR:
        raise Exception("SERIAL NUMBER CRC ERROR!")

    if sps.read_auto_cleaning_interval() != 604800:
        # default 604800, set 0 to disable auto-cleaning
        sps.set_auto_cleaning_interval(604800)
        # device has to be powered-down or reset to check new auto-cleaning interval
        sps.device_reset()

    if sps.read_auto_cleaning_interval() == sps.AUTO_CLN_INTERVAL_ERROR:  # or returns the interval in seconds
        raise Exception("AUTO-CLEANING INTERVAL CRC ERROR!")

    sleep(5)

    sps.start_measurement()

    sleep(5)

    while not sps.read_data_ready_flag():
        sleep(0.25)
        if sps.read_data_ready_flag() == sps.DATA_READY_FLAG_ERROR:
            raise Exception("DATA-READY FLAG CRC ERROR!")

    if sps.read_measured_values() == sps.MEASURED_VALUES_ERROR:
        raise Exception("MEASURED VALUES CRC ERROR!")
    # else:
        #print ("pm1.0 Value in µg/m3: " + str(sps.dict_values['pm1p0']))
        #print ("PM2.5 Value in µg/m3: " + str(sps.dict_values['pm2p5']))
        #print ("PM4.0 Value in µg/m3: " + str(sps.dict_values['pm4p0']))
        #print ("pm10.0 Value in µg/m3: " + str(sps.dict_values['pm10p0']))
        # print ("NC0.5 Value in 1/cm3: " + str(sps.dict_values['nc0p5']))    # NC: Number of Concentration
        #print ("NC1.0 Value in 1/cm3: " + str(sps.dict_values['nc1p0']))
        #print ("NC2.5 Value in 1/cm3: " + str(sps.dict_values['nc2p5']))
        #print ("NC4.0 Value in 1/cm3: " + str(sps.dict_values['nc4p0']))
        #print ("NC10.0 Value in 1/cm3: " + str(sps.dict_values['nc10p0']))
        #print ("Typical Particle Size in µm: " + str(sps.dict_values['typical']))

    sps.stop_measurement()

    sps.start_fan_cleaning()

    pm1 = round((sps.dict_values['pm1p0']), 2)
    pm25 = round((sps.dict_values['pm2p5']), 2)
    pm10 = round((sps.dict_values['pm10p0']), 2)
except Exception as e:
    print(e)


temp, hum = None, None
try:
    sensor = Adafruit_DHT.DHT22

    # Set to your GPIO pin
    pin = 4

    humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)

    temp = str(round((temperature), 2))
    hum = str(round((humidity), 2))
except:
    print("ADAFRUIT ERROR")


date = str(datetime.datetime.now().strftime("%Y-%m-%d"))
time = str(datetime.datetime.now().strftime("%H:%M:%S"))

# Specify the fields for ThingsSpeak and send data
try:
    f = urlopen(baseURL + '&field2=%s&field3=%s&field4=%s&field5=%s&field6=%s' %
                (temp, hum, pm1, pm25, pm10))
    f.read()
    f.close()
except:
    print("Erreur reseau")

with open("/home/pi/dts/info.csv", "a+") as f:
    f.write("{},{},{},{},{},{},{}\n".format(
        date, time, temp, hum, pm1, pm25, pm10))

os.system("git commit -am '[Automatic] CSV udpdate' &> /dev/null")
os.system("git push &> /dev/null")


#print('Temperature in Celsius:',temp)
#print('Humidity in %:', hum)
#print('pm1 value in µg/m3:',pm1)
#print('PM2.5 value in µg/m3:',pm25)
#print('pm10 value in µg/m3:',pm10)
# print('Date:',date)
# print('Time:',time)
print("New measurement uploaded!\n")
