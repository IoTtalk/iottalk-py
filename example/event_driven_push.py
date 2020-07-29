import threading
import time

from datetime import datetime

import requests

api_url = 'https://localhost/csm'  # default
api_url = 'https://iottalk2.tw/csm'  # default
device_name = 'Weather_DA'
device_model = 'Weather'

push_interval = 60

# The input/output device features, please check IoTtalk document.
idf_list = ['Name-I']
odf_list = []

# MIRC311 Hsinchu
lat = '24.6742'
lon = '121.1611'


class func_thread:
    def __init__(self, func, daemonlize):
        self.f = threading.Thread(target=func, daemon=daemonlize)

    def start(self):
        self.f.start()

    def stop(self):
        self.f.stop()


def on_register(dan):
    t1.start()
    t2.start()
    print('[dai] register successfully')


def on_deregister():
    t1.stop()
    t2.stop()
    print('[da] register fail')


def get_condition():
    url = ('http://api.openweathermap.org/data/2.5/'
           'weather?lat={}&lon={}'
           '&appid=7193376830b573b984686c168c63e3ab')
    res = requests.get(url.format(lat, lon))

    if res.status_code == requests.codes.ok:
        weather_data = res.json()

    icon = weather_data['weather'][0]['icon']
    if icon in ['01d', '01n']:
        condition = 'clear sky'
    elif icon in ['02d', '02n']:
        condition = 'few clouds'
    elif icon in ['03d', '03n']:
        condition = 'scattered clouds'
    elif icon in ['04d', '04n']:
        condition = 'broken clouds'
    elif icon in ['09d', '09n']:
        condition = 'shower rain'
    elif icon in ['10d', '10n']:
        condition = 'rain'
    elif icon in ['11d', '11n']:
        condition = 'thunderstorm'
    elif icon in ['13d', '13n']:
        condition = 'snow'
    elif icon in ['50d', '50n']:
        condition = 'mist'

    return icon, condition


def push_weather():
    for i in range(30):
        try:
            condition = get_condition()[1]
            print(datetime.now().isoformat(),
                  ' , weather condition = {}'.format(condition))
            time.sleep(2)

        except Exception as e:
            print(e)


def get_weather():
    while True:
        try:
            icon, condition = get_condition()
            # condition =  weather_data['weather'][0]['main']
            # condition =  weather_data['weather'][0]['description']
            print(datetime.now().isoformat(),
                  ' icon = {}, weather updated,'
                  ' condition = {}'.format(icon, condition))

        except Exception:
            print('Get weather failed')

        time.sleep(600)


t1 = func_thread(get_weather, True)
t2 = func_thread(push_weather, True)
