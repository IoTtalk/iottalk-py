from datetime import datetime

import requests

api_url = 'https://localhost/csm'  # default
device_name = 'Weather_DA'
device_model = 'Weather'

push_interval = 60

# The input/output device features, please check IoTtalk document.
idf_list = ['Name-I']
odf_list = []


def on_register(dan):
    print('[da] register successfully')


def on_deregister():
    print('[da] register fail')


# MIRC311 Hsinchu
lat = '24.6742'
lon = '121.1611'


def Name_I():
    try:
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
        print(datetime.now().isoformat(),
              'icon = {}, weather updated,'
              'condition = {}'.format(icon, condition))

        return condition
    except Exception:
        print('Get weather failed')
        return None
