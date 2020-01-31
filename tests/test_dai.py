import os
import shutil
import tempfile

import pytest

from iottalkpy.dai import load_module

dai_path_cases = [
    ('abs', 'py'),
    ('abs', 'no-py'),
    ('rel', 'py'),
    ('rel', 'no-py')
]


@pytest.fixture
def dai_path(request):
    dir_ = tempfile.mkdtemp(prefix='iottalkpy')
    dir_ = os.path.abspath(dir_)

    with tempfile.NamedTemporaryFile(suffix='.py', dir=dir_, delete=False) as f:
        f.write(b'\n'.join([
            b"api_url = 'http://localhost:9992'",
            b"device_module = 'Dummy_Device'",
            b"idf_list = ['Dummy_Sensor']",
            b"push_interval = 10",
            b"interval = {",
            b"    'Dummy_Sensor': 1,",
            b"}",
        ]))

    if request.param == ('abs', 'py'):
        yield f.name
    elif request.param == ('abs', 'no-py'):
        yield os.path.splitext(f.name)[0]
    elif request.param[0] == 'rel':
        h, t = os.path.split(f.name)
        os.chdir(h)

        if request.param == ('rel', 'py'):
            yield t
        elif request.param == ('rel', 'no-py'):
            yield os.path.splitext(t)[0]
    else:
        raise ValueError('unknown dai path type: {}',format(request.param))

    shutil.rmtree(dir_)


@pytest.mark.parametrize('dai_path', dai_path_cases, indirect=True)
def test_load_module(dai_path):
    m = load_module(dai_path)
    assert m
    assert m.__dict__
    assert m.__dict__['api_url'] == 'http://localhost:9992'
    assert m.__dict__['device_module'] == 'Dummy_Device'
    assert m.__dict__['idf_list'] == ['Dummy_Sensor']
    assert m.__dict__['push_interval'] == 10
    assert m.__dict__['interval'] == {'Dummy_Sensor': 1}
