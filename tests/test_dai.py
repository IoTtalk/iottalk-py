import os
import shutil
import sys
import tempfile

import pytest

from iottalkpy.dai import load_module
from iottalkpy.dai import parse_df_profile
from iottalkpy.dan import RegistrationError

dai_path_cases = [
    ('abs', 'py'),
    pytest.param(
        ('abs', 'no-py'),
        marks=pytest.mark.skipif(
            sys.version_info.major == 2,
            reason='Not supported in Python 2'
        )
    ),
    ('rel', 'py'),
    pytest.param(
        ('rel', 'no-py'),
        marks=pytest.mark.skipif(
            sys.version_info.major == 2,
            reason='Not supported in Python2'
        )
    )
]
sa_profile_cases = [
    ('sa', 'str'),
    ('sa', 'tuple', 'len=2'),
    ('RegistrationError',)
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
        cwd = os.getcwd()
        os.chdir(h)

        if request.param == ('rel', 'py'):
            yield t
        elif request.param == ('rel', 'no-py'):
            yield os.path.splitext(t)[0]

        os.chdir(cwd)
    else:
        raise ValueError('unknown dai path type: {}'.format(request.param))

    shutil.rmtree(dir_)


@pytest.fixture
def dai_path_nonexists(request):
    if request.param == ('abs', 'no-py'):
        yield '/tmp/nondir/nonfile'
    elif request.param == ('rel', 'no-py'):
        yield 'nondir/nonfile'
    elif request.param == ('abs', 'py'):
        yield '/tmp/nondir/nonfile.py'
    elif request.param == ('rel', 'py'):
        yield 'nondir/nonfile.py'


@pytest.fixture
def sa_profile(request):
    dir_ = tempfile.mkdtemp(prefix='iottalkpy')
    dir_ = os.path.abspath(dir_)

    if request.param == ('sa', 'str'):
        content = '\n'.join([
            "idf_list = ['Dummy_Sensor']",
            "odf_list = ['Dummy_Control']"])
    elif request.param == ('sa', 'tuple', 'len=2',):
        content = '\n'.join([
            "idf_list = [('Dummy_Sensor', 'type',)]",
            "odf_list = [('Dummy_Control', 'type',)]"])
    else:
        content = '\n'.join([
            "idf_list = [1, 2, 3,]",
            "odf_list = [10,]"])

    with tempfile.NamedTemporaryFile(suffix='.py', dir=dir_, delete=False) as f:
        f.write(content.encode())
    yield load_module(f.name)

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


@pytest.mark.parametrize('dai_path_nonexists', dai_path_cases, indirect=True)
def test_load_module_nonexists(dai_path_nonexists):
    with pytest.raises(Exception):
        load_module(dai_path_nonexists)


@pytest.mark.parametrize('sa_profile', sa_profile_cases[:2], indirect=True)
def test_parse_df_profile(sa_profile):
    idf = parse_df_profile(sa_profile, 'idf')
    odf = parse_df_profile(sa_profile, 'odf')
    assert idf
    assert odf
    assert idf['Dummy_Sensor'].df_type == 'idf'
    assert odf['Dummy_Control'].df_type == 'odf'


@pytest.mark.parametrize('sa_profile', sa_profile_cases[-1], indirect=True)
def test_parse_df_profile_RegistrationError(sa_profile):
    with pytest.raises(RegistrationError):
        parse_df_profile(sa_profile, 'idf')
    with pytest.raises(RegistrationError):
        parse_df_profile(sa_profile, 'odf')
