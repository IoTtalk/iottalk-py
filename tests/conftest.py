from threading import Lock

import paho
import pytest


@pytest.fixture()
def lock():
    '''
    a lock useful for blocking
    '''
    l = Lock()
    l.acquire()
    yield l


@pytest.fixture()
def mqtt_client(lock):
    '''
    A mqtt client with a lock stored in ``userdata`` and a topic subscribed
    '''
    c = paho.mqtt.client.Client(userdata=lock)
    c.connect('localhost', 1883)
    c.subscribe('test/dan')
    c.loop_start()
    yield c
    c.disconnect()
    c.loop_stop()
