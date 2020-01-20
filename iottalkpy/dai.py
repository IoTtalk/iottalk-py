import atexit
import importlib
import importlib.util
import logging
import os.path
import platform
import re
import signal
import sys
import time

from multiprocessing import Process
from threading import Thread, Event
from uuid import UUID

from iottalkpy.color import DAIColor
from iottalkpy.dan import DeviceFeature, RegistrationError, NoData
from iottalkpy.dan import register, push, deregister

log = logging.getLogger(DAIColor.wrap(DAIColor.logger, 'DAI'))
log.setLevel(level=logging.INFO)


class DAI(Process):
    def __init__(self, api_url, device_model, device_addr=None,
                 device_name=None, persistent_binding=False, username=None,
                 extra_setup_webpage='', device_webpage='',
                 register_callback=None, on_register=None, on_deregister=None,
                 on_connect=None, on_disconnect=None,
                 push_interval=1, interval={}, device_features={}):
        super(Process, self).__init__()
        self.api_url = api_url
        self.device_model = device_model
        self.device_addr = device_addr
        self.device_name = device_name
        self.persistent_binding = persistent_binding
        self.username = username
        self.extra_setup_webpage = extra_setup_webpage
        self.device_webpage = device_webpage

        self.register_callback = register_callback
        self.on_register = on_register
        self.on_deregister = on_deregister
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect

        self.push_interval = push_interval
        self.interval = interval

        self.device_features = device_features
        self.flags = {}

    def push_data(self, df_name):
        if not self.device_features[df_name].push_data:
            return
        log.debug('%s:%s', df_name, self.flags[df_name])
        while self.flags[df_name]:
            _data = self.device_features[df_name].push_data()
            if not isinstance(_data, NoData) and _data is not NoData:
                push(df_name, _data)
            time.sleep(self.interval[df_name])

    def on_signal(self, signal, df_list):
        log.info('Receive signal: \033[1;33m%s\033[0m, %s', signal, df_list)
        if 'CONNECT' == signal:
            for df_name in df_list:
                # race condition
                if not self.flags.get(df_name):
                    self.flags[df_name] = True
                    t = Thread(target=self.push_data, args=(df_name,))
                    t.daemon = True
                    t.start()
        elif 'DISCONNECT' == signal:
            for df_name in df_list:
                self.flags[df_name] = False
        elif 'SUSPEND' == signal:
            # Not use
            pass
        elif 'RESUME' == signal:
            # Not use
            pass
        return True

    def on_data(self, df_name, data):
        self.device_features[df_name].on_data(data)
        return True

    @staticmethod
    def get_df_function_name(df_name):
        return re.sub(r'-O$', '_O', re.sub(r'-I$', '_I', df_name))

    def exit_handler(self, signal, frame):
        sys.exit(0)  # this will trigger ``atexit`` callbacks

    def _check_parameter(self):
        if self.api_url is None:
            raise RegistrationError('api_url is required')

        if self.device_model is None:
            raise RegistrationError('device_model not given.')

        if isinstance(self.device_addr, UUID):
            self.device_addr = str(self.device_addr)
        elif self.device_addr:
            try:
                UUID(self.device_addr)
            except ValueError:
                try:
                    self.device_addr = str(UUID(int=int(self.device_addr, 16)))
                except ValueError:
                    log.warning('Invalid device_addr. Change device_addr to None.')
                    self.device_addr = None

        if self.device_name is None:
            pass
            # raise RegistrationError('device_name not given.')

        if self.persistent_binding and self.device_addr is None:
                msg = ('In case of `persistent_binding` set to `True`, '
                       'the `device_addr` should be set and fixed.')
                raise ValueError(msg)

        if not self.device_features.keys():
            raise RegistrationError('Neither idf_list nor odf_list is empty.')

        return True

    def start(self):
        self._check_parameter()

        idf_list = []
        odf_list = []
        for df in self.device_features.values():
            if df.df_type == 'idf':
                idf_list.append(df.profile())
            else:
                odf_list.append(df.profile())

        def f():
            for key in self._flags:
                self._flags[key] = False
            log.debug('on_disconnect: _flag = %s', str(self._flags))
            if self.on_disconnect:
                return self.on_disconnect()

        context = register(
            self.api_url,
            on_signal=self.on_signal,
            on_data=self.on_data,
            accept_protos=['mqtt'],
            id_=self.device_addr,
            idf_list=idf_list,
            odf_list=odf_list,
            name=self.device_name,
            profile={
                'model': self.device_model,
                'u_name': self.username,
                'extra_setup_webpage': self.extra_setup_webpage,
                'device_webpage': self.device_webpage,
            },
            register_callback=self.register_callback,
            on_register=self.on_register,
            on_deregister=self.on_deregister,
            on_connect=self.on_connect,
            on_disconnect=f
        )

        if not self.persistent_binding:
            atexit.register(deregister)
        signal.signal(signal.SIGTERM, self.exit_handler)
        signal.signal(signal.SIGINT, self.exit_handler)

        log.info('Press Ctrl+C to exit DAI.')
        if platform.system() == 'Windows':
            # workaround for https://bugs.python.org/issue35935
            while True:
                time.sleep(86400)
        else:
            Event().wait()  # wait for SIGINT


def load_module(file_name):
    if file_name.endswith('.py'):
        # https://stackoverflow.com/a/67692
        spec = importlib.util.spec_from_file_location("ida", file_name)
        ida = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ida)
    else:
        # mapping ``/my/path/ida`` to ``my.path.ida``
        m = '.'.join(os.path.normpath(file_name).split(os.path.sep))
        ida = importlib.import_module(m)

    api_url = getattr(ida, 'api_url', None)
    device_model = getattr(ida, 'device_model', None)
    device_addr = getattr(ida, 'device_addr', None)
    device_name = getattr(ida, 'device_name', None)
    persistent_binding = getattr(ida, 'persistent_binding', False)
    username = getattr(ida, 'username', None)
    extra_setup_webpage = getattr(ida, 'extra_setup_webpage', '')
    device_webpage = getattr(ida, 'device_webpage', '')

    # callbacks
    register_callback = getattr(ida, 'register_callback', None)
    on_register = getattr(ida, 'on_register', None)
    on_deregister = getattr(ida, 'on_deregister', None)
    on_connect = getattr(ida, 'on_connect', None)
    on_disconnect = getattr(ida, 'on_disconnect', None)

    push_interval = getattr(ida, 'push_interval', 1)
    interval = getattr(ida, 'interval', {})

    dfs = {}
    for df_profile in getattr(ida, 'idf_list', []):
        if isinstance(df_profile, str):
            dfs[df_profile] = DeviceFeature(df_name=df_profile,
                                            df_type='idf')
            dfs[df_profile].push_data = getattr(ida, DAI.get_df_function_name(df_profile), None)

            # check push data   interval
            interval[df_profile] = interval[df_profile] or push_interval
        elif isinstance(df_profile, tuple) and len(df_profile) == 2:
            dfs[df_profile[0]] = DeviceFeature(df_name=df_profile[0],
                                               df_type='idf',
                                               param_type=df_profile[1])
            dfs[df_profile[0]].push_data = getattr(ida, DAI.get_df_function_name(df_profile[0]), None)

            # check push data interval
            interval[df_profile[0]] = interval[df_profile[0]] or push_interval
        else:
            raise RegistrationError('unknown idf_list, usage: [df_name, ...]')

    for df_profile in getattr(ida, 'odf_list', []):
        if isinstance(df_profile, str):
            dfs[df_profile] = DeviceFeature(df_name=df_profile,
                                            df_type='odf')
            dfs[df_profile].on_data = getattr(ida, DAI.get_df_function_name(df_profile), None)
        elif isinstance(df_profile, tuple) and len(df_profile) == 2:
            dfs[df_profile[0]] = DeviceFeature(df_name=df_profile[0],
                                               df_type='odf',
                                               param_type=df_profile[1])
            dfs[df_profile[0]].on_data = getattr(ida, DAI.get_df_function_name(df_profile[0]), None)
        else:
            raise RegistrationError('unknown odf_list, usage: [df_name, ...]')

    dai = DAI(api_url, device_model, device_addr, device_name,
              persistent_binding, username,
              extra_setup_webpage, device_webpage,
              register_callback, on_register, on_deregister,
              on_connect, on_disconnect,
              push_interval, interval, dfs)
    return dai


if __name__ == '__main__':
    dai = load_module(sys.argv[1] if len(sys.argv) > 1 else 'ida')
    dai.start()
    dai.join()
