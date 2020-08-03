import threading
import time

from datetime import datetime

import requests

api_url = 'https://localhost/csm'  # default
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
    dan = None

    def __init__(self, func, daemonlize):
        self.thread = threading.Thread(target=func, daemon=daemonlize)

    def start(self):
        if self.thread:
            self.thread.start()

    def stop(self):
        if self.thread:
            self.thread.stop()

    def push(self, device_feature, data):
        if self.dan:
            self.dan.push(device_feature, data)


def on_register(dan):
    t1.dan = dan
    t2.dan = dan
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
            t2.push('Name-I', condition)
            print(datetime.now().isoformat(),
                  ' , weather condition = {}'.format(condition))
            time.sleep(2)

        except Exception as e:
            print(e)


def get_weather():
    while True:
        try:
            icon, condition = get_condition()
            t1.push('Name-I', condition)
            print(datetime.now().isoformat(),
                  ' icon = {}, weather updated,'
                  ' condition = {}'.format(icon, condition))

        except Exception:
            print('Get weather failed')

        time.sleep(600)


t1 = func_thread(func=get_weather, daemonlize=True)
t2 = func_thread(func=push_weather, daemonlize=True)
