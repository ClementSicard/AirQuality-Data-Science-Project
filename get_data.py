import os
import time
import Adafruit_DHT
import requests
from sps30 import SPS30
DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 4

# In seconds
SAMPLING_INTERVAL = 30

try:
    f = open('/home/pi/dts/info.csv', 'a+')
    if os.stat('/home/pi/dts/info.csv').st_size == 0:
        f.write('Date,Time,Temperature,Humidity,PM1,PM2.5,PM10\r\n')
    f.close()
except:
    pass


sps = SPS30(1)

if sps.read_article_code() == sps.ARTICLE_CODE_ERROR:
    raise Exception("ARTICLE CODE CRC ERROR!")
else:
    print("ARTICLE CODE: " + str(sps.read_article_code()))

if sps.read_device_serial() == sps.SERIAL_NUMBER_ERROR:
    raise Exception("SERIAL NUMBER CRC ERROR!")
else:
    print("DEVICE SERIAL: " + str(sps.read_device_serial()))
# default 604800, set 0 to disable auto-cleaning
sps.set_auto_cleaning_interval(0)
sps.device_reset()


def temp_and_humidity():
    humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)

    if humidity is not None and temperature is not None:
        return temperature, humidity
    else:
        print("Failed to retrieve data from humidity sensor")


def pollution():

    try:
        time.sleep(3)
        sps.start_measurement()
        time.sleep(3)

        while not sps.read_data_ready_flag():
            print("New Measurement is not available!")
            time.sleep(1)
            if sps.read_data_ready_flag() == sps.DATA_READY_FLAG_ERROR:
                raise Exception("DATA-READY FLAG CRC ERROR!")
        pm1 = 0
        pm2 = 0
        pm10 = 0
        if sps.read_measured_values() == sps.MEASURED_VALUES_ERROR:
            raise Exception("MEASURED VALUES CRC ERROR!")
        else:
            pm1 = str(sps.dict_values['pm1p0'])
            pm2 = str(sps.dict_values['pm2p5'])
            pm10 = str(sps.dict_values['pm10p0'])

        sps.stop_measurement()
        print("Measurement added!")
        sps.start_fan_cleaning()

        return pm1, pm2, pm10

    except IOError:
        print("IOError")

        # A changer
        return 0, 0, 0


def save(t, h, pm1, pm25, pm10):
    with open("/home/pi/dts/info.csv", "a+") as f:
        f.write("{},{},{:0.5f},{:0.5f},{:0.5f}".format(t, h, pm1, pm25, pm10))


def upload(t, h, pm1, pm25, pm10):
    r = requests.get(
        "https://api.thingspeak.com/update?api_key=L50MRPUQ7X1N3J9Z&field2={0}&field3={1}&field4={2:0.5f}&field5={3:0.5f}&field6={4:0.5f}".format(t, h, pm1, pm25, pm10))


while True:
    t, h = temp_and_humidity()
    pm1, pm25, pm10 = pollution()
    save(t, h, float(pm1), float(pm25), float(pm10))
    upload(t, h, float(pm1), float(pm25), float(pm10))
    time.sleep(SAMPLING_INTERVAL)
