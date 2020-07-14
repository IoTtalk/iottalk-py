'''
This module wraps the mqtt API into IoTtalk client API.

If your process contain single Device,
you can use::

    from iottalkpy import dan
    dan.register(...)


Or your process contain multiple Device,
you can use::

    from iottalkpy.dan import Client

    # for device 1
    dan1 = Client()
    dan1.register(...)

    # for device 2
    dan2 = Client()
    dan2.register(...)

'''
import json
import logging
import time

from threading import Lock
from uuid import UUID, uuid4

import requests

from paho.mqtt import client as mqtt
from paho.mqtt.client import MQTT_ERR_SUCCESS

from iottalkpy.color import DANColor
from iottalkpy.exceptions import RegistrationError

# python2 compatibility
try:
    import queue
except ImportError:
    import Queue as queue


__all__ = ('NoData', 'Client', 'push', 'register', 'deregister',
           'loop_forever')

logging.basicConfig(level=logging.INFO)  # root logger setting
log = logging.getLogger(DANColor.wrap(DANColor.logger, 'DAN'))
log.setLevel(level=logging.INFO)


class NoData():
    pass


class DeviceFeature(object):
    def __init__(self, df_name, df_type, param_type=None, push_data=None,
                 on_data=None):
        self.df_name = df_name
        self.df_type = df_type  # idf | odf
        self.param_type = param_type if param_type is not None else [None]

        self._on_data = None
        if df_type == 'odf' and on_data:
            self.on_data = on_data

        self._push_data = None
        if df_type == 'idf' and push_data:
            self.push_data = push_data

    @property
    def df_name(self):
        return self._df_name

    @df_name.setter
    def df_name(self, value):
        self._df_name = value

    @property
    def df_type(self):
        return self._df_type

    @df_type.setter
    def df_type(self, value):
        if value not in ['idf', 'odf']:
            msg = '<{df_name}>: df_type must be "idf" or "odf"'.format(df_name=self.df_name)
            raise RegistrationError(msg)
        self._df_type = value

    @property
    def param_type(self):
        return self._param_type

    @param_type.setter
    def param_type(self, value):
        self._param_type = value

    @property
    def on_data(self):
        return self._on_data

    @on_data.setter
    def on_data(self, value):
        if value is None or not callable(value):
            msg = '<{df_name}>: function not found'.format(df_name=self.df_name)
            raise RegistrationError(msg)
        self._on_data = value

    @property
    def push_data(self):
        return self._push_data

    @push_data.setter
    def push_data(self, value):
        if value is None or not callable(value):
            msg = '<{df_name}>: function not found.'.format(df_name=self.df_name)
            raise RegistrationError(msg)
        self._push_data = value

    def profile(self):
        return (self.df_name, self.param_type)


class ChannelPool(dict):
    def __init__(self):
        self.rtable = {}

    def __setitem__(self, df, topic):
        dict.__setitem__(self, df, topic)
        self.rtable[topic] = df

    def __delitem__(self, df):
        del self.rtable[self[df]]
        dict.__delitem__(self, df)

    def df(self, topic):
        return self.rtable.get(topic)


class Context(object):
    def __init__(self):
        self.url = None
        self.app_id = None
        self.name = None
        self.mqtt_host = None
        self.mqtt_port = None
        self.mqtt_client = None
        self.i_chans = ChannelPool()
        self.o_chans = ChannelPool()
        self.rev = None
        self.on_signal = None
        self.on_data = None
        self.on_register = None
        self.on_deregister = None
        self.on_connect = None
        self.on_disconnect = None
        self._mqueue = queue.Queue()  # storing the MQTTMessageInfo from ``publish``

    def __str__(self):
        return '[{}/{}, mqtt://{}:{}]'.format(
            self.url, self.app_id,
            self.mqtt_host, self.mqtt_port
        )


def _invalid_url(url):
    ''' Check if the url is a valid url
    # This method should be refined
    >>> _invalid_url(None)
    True
    >>> _invalid_url('')
    True
    '''
    return url is None or url == ''


class Client:
    def __init__(self):
        self.context = Context()
        self._is_reconnect = False

    def _on_connect(self, client, userdata, flags, rc):

        if not self._is_reconnect:
            log.info('Successfully connect to %s.',
                     DANColor.wrap(DANColor.data, self.context.url))
            log.info('Device ID: %s.',
                     DANColor.wrap(DANColor.data, self.context.app_id))
            log.info('Device name: %s.',
                     DANColor.wrap(DANColor.data, self.context.name))

            res, _ = client.subscribe(self.context.o_chans['ctrl'], qos=2)
            if res != MQTT_ERR_SUCCESS:
                #FIXME: use proper exception type
                raise Exception('Subscribe to control channel failed')

        else:  # in case of reconnecting, we need to renew all subscriptions
            log.info('Reconnect: %s.', DANColor.wrap(DANColor.data, self.context.name))
            client.publish(
                self.context.i_chans['ctrl'],
                json.dumps({'state': 'offline', 'rev': self.context.rev}),
                retain=True,
                qos=2
            )
            for k, topic in self.context.o_chans.items():
                log.info('Renew subscriptions for %s -> %s',
                         DANColor.wrap(DANColor.data, k), DANColor.wrap(DANColor.data, topic))
                client.subscribe(topic, qos=2)
            # FIXME: online msg may reach eariler then offline, race condition
            time.sleep(1)

        msg = client.publish(
            self.context.i_chans['ctrl'],
            json.dumps({'state': 'online', 'rev': self.context.rev}),
            retain=True,
            qos=2
        )
        self.context._mqueue.put(msg)

        self._is_reconnect = True

        if self.context.on_connect:
            self.context.on_connect()

    def _on_message(self, client, userdata, msg):
        if self.context.mqtt_client is not client:
            # drop messages that comes after deregistration
            return

        payload = msg.payload.decode('utf8')
        if msg.topic == self.context.o_chans['ctrl']:
            signal = json.loads(payload)
            if signal['command'] == 'CONNECT':
                if 'idf' in signal:
                    idf = signal['idf']
                    self.context.i_chans[idf] = signal['topic']
                    handling_result = self.context.on_signal(
                        signal['command'], [idf]
                    )

                elif 'odf' in signal:
                    odf = signal['odf']
                    self.context.o_chans[odf] = signal['topic']
                    handling_result = self.context.on_signal(
                        signal['command'], [odf]
                    )
                    # TODO: make ``qos`` configurable
                    client.subscribe(self.context.o_chans[odf])

            elif signal['command'] == 'DISCONNECT':
                if 'idf' in signal:
                    idf = signal['idf']
                    del self.context.i_chans[idf]
                    handling_result = self.context.on_signal(
                        signal['command'], [idf]
                    )

                elif 'odf' in signal:
                    odf = signal['odf']
                    client.unsubscribe(self.context.o_chans[odf])
                    del self.context.o_chans[odf]
                    handling_result = self.context.on_signal(
                        signal['command'], [odf]
                    )

            res_message = {
                'msg_id': signal['msg_id'],
            }
            if handling_result is True:     # user may return (False, 'reason')
                res_message['state'] = 'ok'
            else:
                res_message['state'] = 'error'
                res_message['reason'] = handling_result[1]

            # FIXME: current v2 server implementation will ignore this message
            #        We might fix this in v3
            self.context.mqtt_client.publish(
                self.context.i_chans['ctrl'],
                json.dumps(res_message),
                qos=2,
            )

        else:
            df = self.context.o_chans.df(msg.topic)
            if not df:
                return
            self.context.on_data(df, json.loads(payload))

    def _on_offline_pub(self, client, userdata, mid):
        client.disconnect()

    def _on_disconnect(self, client, userdata, rc):
        log.info('%s (%s) disconnected from  %s.',
                 DANColor.wrap(DANColor.data, self.context.name),
                 DANColor.wrap(DANColor.data, self.context.app_id),
                 DANColor.wrap(DANColor.data, self.context.url))
        if hasattr(self, '_disconn_lock'):  # we won't have it if reconnecting
            self._disconn_lock.release()

        if self.context.on_disconnect:
            self.context.on_disconnect()

    def register(self, url, on_signal, on_data,
                 id_=None, name=None,
                 idf_list=None, odf_list=None,
                 accept_protos=None,
                 profile=None, register_callback=None,
                 on_register=None, on_deregister=None,
                 on_connect=None, on_disconnect=None):
        ''' Register to an IoTtalk server.

        :param url: the url of Iottalk server
        :param on_signal: the signal handler
        :param on_data: the data handler
        :param id_: the uuid used to identify an application, if not provided,
                    this function generates one and return
        :param name: the name of the application
        :param idf_list: the Input Device Feature list of the application.
                         Every element should be a tuple,
                         with the feature name and unit information provided,
                         e.g. ('meow', ('dB'))
        :param odf_list: the Output Device Feature list of the application.
        :param accept_protos: the protocols accepted by the application.
                              default is ``['mqtt']``.
        :param profile: an abitrary json data field
        :param on_register: the callable function invoked
                            while the registeration succeeded.
        :param register_callback: this is deprecated, please use ``on_register``
                                  instead.
        :param on_deregister: the callable function invoked
                              while the deregistration succeeded.
        :param on_connect: the callable function invoked while the MQTT
                           client connected.
                           Note that this function might be called multiple
                           times if the client keep reconnecting.
        :param on_disconnect: the callable function invoked while the MQTT
                              client disconnected.
                              Note that this function might be called multiple
                              times if the client lose the connection.
        :type url: str
        :type on_signal: Function
        :type on_data: Function
        :type id_: str
        :type name: str
        :type idf_list: List[Tuple[str, List[str]]]
        :type odf_list: List[Tuple[str, List[str]]]
        :type accept_protos: List[str]
        :type profile: dict
        :returns: the json object responsed from server if registration succeed
        :raises: RegistrationError if already registered or registration failed
        '''
        ctx = self.context

        if ctx.mqtt_client:
            raise RegistrationError('Already registered')

        ctx.url = url
        if _invalid_url(ctx.url):
            raise RegistrationError('Invalid url: "{}"'.format(ctx.url))

        try:
            ctx.app_id = UUID(id_) if id_ else uuid4()
        except ValueError:
            raise RegistrationError('Invalid UUID: {!r}'.format(id_))

        body = {}
        if name:
            body['name'] = name

        if idf_list:
            body['idf_list'] = idf_list

        if odf_list:
            body['odf_list'] = odf_list

        body['accept_protos'] = accept_protos if accept_protos else ['mqtt']

        if profile:
            body['profile'] = profile

        _reg_msg = 'register_callback is deprecated, please use `on_register` instead.'
        if on_register and register_callback:
            raise RegistrationError(_reg_msg)
        elif on_register:
            ctx.on_register = on_register
        elif register_callback:
            log.warning(_reg_msg)
            ctx.on_register = register_callback

        # other callbacks
        ctx.on_deregister = on_deregister
        ctx.on_connect = on_connect
        ctx.on_disconnect = on_disconnect

        try:
            response = requests.put(
                '{}/{}'.format(ctx.url, ctx.app_id),
                headers={
                    'Content-Type': 'application/json',
                },
                data=json.dumps(body)
            )

            if response.status_code != 200:
                raise RegistrationError(response.json()['reason'])
        except requests.exceptions.ConnectionError:
            raise RegistrationError('ConnectionError')
        except (KeyError, json.JSONDecodeError):
            raise RegistrationError('Invalid response from server')

        metadata = response.json()
        ctx.name = metadata['name']
        ctx.mqtt_host = metadata['url']['host']
        ctx.mqtt_port = metadata['url']['port']
        ctx.i_chans['ctrl'] = metadata['ctrl_chans'][0]
        ctx.o_chans['ctrl'] = metadata['ctrl_chans'][1]
        ctx.rev = rev = metadata['rev']
        ctx.mqtt_client = mqtt.Client(client_id='iottalk-py-{}'.format(uuid4().hex))
        ctx.mqtt_client.on_message = self._on_message
        ctx.mqtt_client.on_connect = self._on_connect
        ctx.mqtt_client.on_disconnect = self._on_disconnect

        ctx.mqtt_client.enable_logger(log)
        ctx.mqtt_client.will_set(
            self.context.i_chans['ctrl'],
            json.dumps({'state': 'offline', 'rev': rev}),
            retain=True,
        )
        ctx.mqtt_client.connect(
            self.context.mqtt_host,
            port=self.context.mqtt_port,
        )

        ctx.mqtt_client.loop_start()

        ctx.on_signal = on_signal
        ctx.on_data = on_data

        try:
            msg = ctx._mqueue.get(timeout=5)
            msg.wait_for_publish()
        except queue.Empty:
            log.error('MQTT connection timeout')
            raise
        log.debug('Online message published')

        if ctx.on_register:
            ctx.on_register()

        return ctx

    def deregister(self):
        ''' Deregister from an IoTtalk server.

        This function will block until the offline message published and
        DELETE request finished.

        :raises: RegistrationError if not registered or deregistration failed
        '''
        log.debug("Deregisteration triggered")
        ctx = self.context

        if not ctx.mqtt_client:
            raise RegistrationError('Not registered')

        # FIXME: replace lock with ``wait_for_publish``
        self._disconn_lock = Lock()
        self._disconn_lock.acquire()

        ctx.mqtt_client.on_publish = self._on_offline_pub
        ctx.mqtt_client.publish(
            ctx.i_chans['ctrl'],
            json.dumps({'state': 'offline', 'rev': ctx.rev}),
            retain=True,
            qos=2,
        ).wait_for_publish()

        try:
            response = requests.delete(
                '{}/{}'.format(ctx.url, ctx.app_id),
                headers={
                    'Content-Type': 'application/json'
                },
                data=json.dumps({'rev': ctx.rev})
            )

            if response.status_code != 200:
                raise RegistrationError(response.json()['reason'])
        except requests.exceptions.ConnectionError:
            raise RegistrationError('ConnectionError')
        except (KeyError, json.JSONDecodeError):
            raise RegistrationError('Invalid response from server')

        self._disconn_lock.acquire()  # wait for disconnect finished
        del self._disconn_lock
        ctx.mqtt_client = None

        if ctx.on_deregister:
            ctx.on_deregister()

        return response.json()

    def push(self, idf, data, block=False):
        '''
        Push data to IoTtalk server.

        :param block: if ``True``, block mqtt publishing util finished
        :returns: ``True`` if publishing fired, ``False`` if failed
        :raises: RegistrationError if not registered
        '''
        ctx = self.context
        if not ctx.mqtt_client:
            raise RegistrationError('Not registered')

        if ctx.i_chans.get(idf) is None:
            return False

        data = data if isinstance(data, list) else [data]
        data = json.dumps(data)

        # TODO: make qos configurable
        pub = ctx.mqtt_client.publish(
            self.context.i_chans[idf],
            data,
        )

        if block:
            pub.wait_for_publish()

        return True

    def loop_forever(self):
        return self.context.mqtt_client.loop_forever()


_default_client = Client()


def register(*args, **kwargs):
    return _default_client.register(*args, **kwargs)


def deregister():
    return _default_client.deregister()


def push(idf, data, **kwargs):
    return _default_client.push(idf, data, **kwargs)


def loop_forever():
    return _default_client.loop_forever()
