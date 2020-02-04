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
    fp, path = tempfile.mkstemp(suffix='.py', prefix='iottalkpy')

    str_ = [
        "api_url = 'http://localhost:9992'",
        "device_module = 'Dummy_Device'",
        "idf_list = ['Dummy_Sensor']",
        "push_interval = 10",
        "interval = {",
        "    'Dummy_Sensor': 1",
        "}",
    ]

    f = open(path, "w")

    for line in str_:
        f.write(line)
        f.write('\n')
    f.close()

    if request.param == ('abs', 'py'):
        yield path
    elif request.param == ('abs', 'no-py'):
        yield os.path.splitext(path)[0]
    elif request.param[0] == 'rel':
        h, t = os.path.split(path)
        os.chdir(h)

        if request.param == ('rel', 'py'):
            yield t
        elif request.param == ('rel', 'no-py'):
            yield os.path.splitext(t)[0]
    else:
        raise ValueError('unknown dai path type: {}',format(request.param))

    os.unlink(path)


@pytest.fixture
def dai_path_nonmodule(request):
    if request.param == ('abs', 'no-py'):
        yield '/tmp/nondir/nonfile'
    elif request.param == ('rel', 'no-py'):
        yield 'nondir/nonfile'
    elif request.param == ('abs', 'py'):
        yield '/tmp/nondir/nonfile.py'
    elif request.param == ('rel', 'py'):
        yield 'nondir/nonfile.py'


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


@pytest.mark.parametrize('dai_path_nonmodule', dai_path_cases, indirect=True)
def test_load_module_nonmodule(dai_path_nonmodule):
    with pytest.raises(Exception):
        load_module(dai_path_nonmodule)
