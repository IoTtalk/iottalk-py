import atexit
import logging
import os.path
import platform
import re
import signal
import sys
import time

from multiprocessing import Process, Manager
from threading import Thread, Event
from uuid import UUID

from iottalkpy.color import DAIColor
from iottalkpy.dan import Client, DeviceFeature, NoData
from iottalkpy.exceptions import RegistrationError
from iottalkpy.utils import cd

log = logging.getLogger(DAIColor.wrap(DAIColor.logger, 'DAI'))
log.setLevel(level=logging.INFO)

try:  # Python 3 only
    import importlib
    import importlib.util
except ImportError:
    pass


class DAI(Process):
    daemon = True

    def __init__(self, api_url, device_model, device_addr=None,
                 device_name=None, persistent_binding=False, username=None,
                 extra_setup_webpage='', device_webpage='',
                 register_callback=None, on_register=None, on_deregister=None,
                 on_connect=None, on_disconnect=None,
                 push_interval=1, interval=None, device_features=None):
        super(DAI, self).__init__()

        self._manager = Manager()
        self._event = self._manager.Event()  # create Event proxy object at main process

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
        self.interval = interval if interval else {}

        self.device_features = device_features if device_features else {}
        self.flags = {}

    def push_data(self, df_name):
        if not self.device_features[df_name].push_data:
            return
        log.debug('%s:%s', df_name, self.flags[df_name])
        while self.flags[df_name]:
            _data = self.device_features[df_name].push_data()
            if not isinstance(_data, NoData) and _data is not NoData:
                self.dan.push(df_name, _data)
            time.sleep(self.interval.get(df_name, self.push_interval))

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
    def df_func_name(df_name):
        return re.sub(r'-(I|O)$', r'_\1', df_name)

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

        if self.persistent_binding and self.device_addr is None:
                msg = ('In case of `persistent_binding` set to `True`, '
                       'the `device_addr` should be set and fixed.')
                raise ValueError(msg)

        if not self.device_features.keys():
            raise RegistrationError('Neither idf_list nor odf_list is empty.')

        return True

    def finalizer(self):
        try:
            if not self.persistent_binding:
                self.dan.deregister()
        except Exception as e:
            log.warning('dai process cleanup exception: %s', e)

    def start(self, *args, **kwargs):
        ret = super(DAI, self).start(*args, **kwargs)
        # conduct deregistration properly,
        # if one doesn't stop process before main process ends
        atexit.register(self.terminate)
        return ret

    def run(self):  # this function will be executed in child process
        self._check_parameter()

        self.dan = Client()

        idf_list = []
        odf_list = []
        for df in self.device_features.values():
            if df.df_type == 'idf':
                idf_list.append(df.profile())
            else:
                odf_list.append(df.profile())

        def f():
            for key in self.flags:
                self.flags[key] = False
            log.debug('on_disconnect: _flag = %s', str(self.flags))
            if self.on_disconnect:
                return self.on_disconnect()

        self.dan.register(
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

        log.info('Press Ctrl+C to exit DAI.')
        try:
            self._event.wait()
        except KeyboardInterrupt:
            pass
        finally:
            self.finalizer()

    def wait(self):
        try:
            if platform.system() == 'Windows' or sys.version_info.major == 2:
                # workaround for https://bugs.python.org/issue35935
                while True:
                    time.sleep(86400)
            else:
                Event().wait()
        except KeyboardInterrupt:
            self.join()  # wait for deregistration

    def terminate(self, *args, **kwargs):
        '''
        Terminate DAI.

        This is a blocking call.
        '''
        try:
            self._event.set()
        except Exception:
            # this is triggered if the ``run`` function ended already.
            pass

        self.join()
        return super(DAI, self).terminate(*args, **kwargs)


def parse_df_profile(sa, typ):
    def f(p):
        if isinstance(p, str):
            df_name, param_type = p, None
        elif isinstance(p, tuple) and len(p) == 2:
            df_name, param_type = p
        else:
            raise RegistrationError(
                'Invalid `{}_list`, usage: [df_name, ...] '
                'or [(df_name, type), ...]'.format(typ))

        on_data = push_data = getattr(sa, DAI.df_func_name(df_name), None)

        df = DeviceFeature(
            df_name=df_name, df_type=typ, param_type=param_type,
            push_data=push_data, on_data=on_data)
        return df_name, df

    profiles = getattr(sa, '{}_list'.format(typ), [])
    return dict(map(f, profiles))


def module_to_sa(sa):
    kwargs = {
        k: getattr(sa, k, d)
        for k, d in [
            ('api_url', None),
            ('device_model', None),
            ('device_addr', None),
            ('device_name', None),
            ('persistent_binding', False),
            ('username', None),
            ('extra_setup_webpage', ''),
            ('device_webpage', ''),
            ('push_interval', 1),
            ('interval', {}),

            # callbacks
            ('register_callback', None),
            ('on_register', None),
            ('on_deregister', None),
            ('on_connect', None),
            ('on_disconnect', None),
        ]
    }
    kwargs['device_features'] = dict(
        parse_df_profile(sa, 'idf'),
        **parse_df_profile(sa, 'odf'))

    return DAI(**kwargs)


def load_module(fname):
    if sys.version_info.major > 2:  # python 3+
        if fname.endswith('.py'):
            # https://stackoverflow.com/a/67692
            if sys.version_info >= (3, 5):
                spec = importlib.util.spec_from_file_location('sa', fname)
                sa = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(sa)
            else:  # case of python 3.4
                # this import only for python 3.4-
                from importlib.machinery import SourceFileLoader
                sa = SourceFileLoader('sa', fname).load_module()
        else:
            fname = os.path.normpath(fname)
            m = fname[1:] if fname.startswith('/') else fname

            # mapping ``my/path/sa`` to ``my.path.sa``
            m = '.'.join(m.split(os.path.sep))

            # well, seems we need to hack sys.path
            if fname.startswith('/'):
                with cd('/'):
                    sys.path.append(os.getcwd())
                    sa = importlib.import_module(m, )
            else:
                sys.path.append(os.getcwd())
                sa = importlib.import_module(m)

            sys.path.pop()

        return sa
    else:  # in case of python 2, only single file is supported
        if os.path.isdir(fname):
            raise RuntimeError(
                "Only single file loading is supported in Python 2")

        class App(object):
            def __init__(self, d):
                self.__dict__ = d

        d = {}
        with open(fname) as f:
            exec(f, d)

        return App(d)


def main(dai):
    dai.start()
    dai.wait()


if __name__ == '__main__':
    main(module_to_sa(load_module(sys.argv[1] if len(sys.argv) > 1 else 'sa')))
