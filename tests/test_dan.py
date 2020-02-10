import json
import pytest
import requests
import sys

from threading import Thread, Lock
from time import sleep
from uuid import UUID, uuid4

from paho.mqtt import client as mqtt

from iottalkpy import dan as iot_dan


@pytest.skip('Not test now', allow_module_level=True)
@pytest.fixture()
def uuid():
    return str(uuid4())


@pytest.fixture()
def base_url():
    return 'http://localhost:9992'


@pytest.fixture()
def dan():
    iot_dan._default_client = iot_dan.Client()  # refresh some global contexts
    yield iot_dan


@pytest.fixture()
def simple_da(dan, base_url):
    def on_data(*args):
        pass

    def on_signal(*args):
        pass

    context = dan.register(
        base_url,
        on_signal=on_signal,
        on_data=on_data,
        accept_protos=['mqtt'],
        odf_list=[('meow', ['dB'])],
        name='BetaCat',
        profile={
            'model': 'AI',
        },
    )

    assert context.rev is not None
    yield context
    sleep(1)  # make DA busy
    dan.deregister()


def test_register_without_id(base_url, dan):
    def on_data(*args):
        pass

    def on_signal(*args):
        pass

    context = dan.register(
        base_url,
        on_signal=on_signal,
        on_data=on_data,
        accept_protos=['mqtt'],
        idf_list=[('acce', ['m/s^s', 'm/s^2', 'm/s^2'])],
        odf_list=[('meow', ['dB'])],
        name='test da',
        profile={
            'model': 'BetaCat',
        },
    )

    assert context.url == base_url
    assert context.rev is not None
    assert isinstance(context.app_id, UUID)
    assert context.mqtt_host is not None
    assert context.mqtt_port is not None
    assert isinstance(context.mqtt_client, mqtt.Client)
    assert context.on_signal is on_signal
    assert context.on_data is on_data

    sleep(1)  # make DA busy


def test_register_with_id(base_url, uuid, dan):
    def on_data(*args):
        pass

    def on_signal(*args):
        pass

    context = dan.register(
        base_url,
        id_=uuid,
        on_signal=on_signal,
        on_data=on_data,
        accept_protos=['mqtt'],
        idf_list=[('acce', ['m/s^s', 'm/s^2', 'm/s^2'])],
        odf_list=[('meow', ['dB'])],
        name='test da',
        profile={
            'model': 'BetaCat',
        },
    )

    assert context.url == base_url
    assert context.rev is not None
    assert context.app_id == UUID(uuid)
    assert context.mqtt_host is not None
    assert context.mqtt_port is not None
    assert isinstance(context.mqtt_client, mqtt.Client)
    assert context.on_signal is on_signal
    assert context.on_data is on_data

    sleep(1)  # make DA busy


def test_register_deregister(base_url, dan):
    def on_data(*args):
        pass

    def on_signal(*args):
        pass

    context = dan.register(
        base_url,
        on_signal=on_signal,
        on_data=on_data,
        accept_protos=['mqtt'],
        idf_list=[('acce', ['m/s^s', 'm/s^2', 'm/s^2'])],
        odf_list=[('meow', ['dB'])],
        name='test da',
        profile={
            'model': 'BetaCat',
        },
    )

    assert context.url == base_url
    assert context.rev is not None
    assert isinstance(context.app_id, UUID)
    assert context.mqtt_host is not None
    assert context.mqtt_port is not None
    assert isinstance(context.mqtt_client, mqtt.Client)
    assert context.on_signal is on_signal
    assert context.on_data is on_data

    sleep(1)  # make DA busy
    dan.deregister()

    assert context.mqtt_client is None


def test_register_profile(base_url, uuid, dan):
    def on_data(*args):
        pass

    def on_signal(*args):
        pass

    context = dan.register(
        base_url,
        id_=uuid,
        on_signal=on_signal,
        on_data=on_data,
        accept_protos=['mqtt'],
        odf_list=[('meow', ['dB'])],
        name='BetaCat',
        profile={
            'model': 'AI',
        },
    )

    assert context.rev is not None

    url = '{}/{}'.format(base_url, uuid)
    res = requests.get(url)
    assert res.status_code == 200, res.text

    data = res.json()
    assert data['id'] == uuid
    assert data['profile'] == {'model': 'AI'}

    sleep(1)  # make DA busy


def test_mqtt_online_msg(mqtt_client, simple_da, lock, dan):
    topic = simple_da.i_chans['ctrl']
    rev = simple_da.rev

    def on_msg(client, user_data, msg):
        on_msg.topic = msg.topic
        on_msg.payload = json.loads(msg.payload.decode())
        lock.release()

    mqtt_client.on_message = on_msg
    mqtt_client.subscribe(topic)

    lock.acquire()  # wait for message

    assert topic == on_msg.topic
    assert on_msg.payload == {
        'state': 'online',
        'rev': rev,
    }


def test_mqtt_offline_msg(mqtt_client, base_url, lock, dan):
    def on_data(*args):
        pass

    def on_signal(*args):
        pass

    ctx = dan.register(
        base_url,
        on_signal=on_signal,
        on_data=on_data,
        accept_protos=['mqtt'],
        odf_list=[('meow', ['dB'])],
        name='BetaCat',
        profile={
            'model': 'AI',
        },
    )

    topic = ctx.i_chans['ctrl']
    rev = ctx.rev

    assert ctx.rev is not None
    sleep(1)  # make DA busy
    dan.deregister()

    def on_msg(client, user_data, msg):
        on_msg.topic = msg.topic
        on_msg.payload = json.loads(msg.payload.decode())
        lock.release()

    mqtt_client.on_message = on_msg
    mqtt_client.subscribe(topic)

    lock.acquire()  # wait for message

    assert on_msg.topic == topic
    assert on_msg.payload == {
        'state': 'offline',
        'rev': rev,
    }


def test_on_online_pub(simple_da):
    assert simple_da.mqtt_client.on_publish is None


def test_register_without_name(base_url, uuid, dan):
    def on_data(*args):
        pass

    def on_signal(*args):
        pass

    context = dan.register(
        base_url,
        id_=uuid,
        on_signal=on_signal,
        on_data=on_data,
        accept_protos=['mqtt'],
        odf_list=[('meow', ['dB'])],
        profile={
            'model': 'AI',
        },
    )

    assert context.rev is not None

    url = '{}/{}'.format(base_url, uuid)
    res = requests.get(url)
    assert res.status_code == 200, res.text

    data = res.json()
    assert data['id'] == uuid
    assert data.get('name') is not None


# if the playload is not a dict or list,
# wrap it into list then encode to json
@pytest.mark.parametrize('payload', [42, "string", None])
def test_push(dan, simple_da, payload):
    def pub(topic, data, **kwargs):
        '''
        mock publish function
        '''
        assert topic == 'magic'
        assert data == json.dumps([payload])

    simple_da.i_chans['meow'] = 'magic'
    orig_pub = simple_da.mqtt_client.publish
    simple_da.mqtt_client.publish = pub

    dan.push('magic', payload)

    simple_da.mqtt_client.publish = orig_pub


@pytest.mark.parametrize('payload', [
    (-4, 3),
    [3, -4],
    {'answer': 42},
])
def test_push_json(dan, simple_da, payload):
    def pub(topic, data, **kwargs):
        '''
        mock publish function
        '''
        assert topic == 'magic'
        assert data == json.dumps(payload)

    simple_da.i_chans['meow'] = 'magic'
    orig_pub = simple_da.mqtt_client.publish
    simple_da.mqtt_client.publish = pub

    dan.push('magic', payload)

    simple_da.mqtt_client.publish = orig_pub
