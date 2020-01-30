import os
import shutil
import tempfile

import pytest

from iottalkpy.dai import load_module


def fname():
    fp_dir1 = tempfile.mkdtemp()
    fp1 = tempfile.NamedTemporaryFile(suffix='.py', dir=fp_dir1, delete=False)
    fp1.write(b'''
api_url = 'http://localhost:9992'
device_module = 'Dummy_Device'
idf_list = ['Dummy_Sensor']
push_interval = 10
interval = {
    'Dummy_Sensor': 1,
}
''')
    fp1.close()

    a = fp1.name
    b = os.path.splitext(fp1.name)[0]

    fp_dir2 = tempfile.mkdtemp(dir='/home/ken/iottalk-py/tests/')
    fp2 = tempfile.NamedTemporaryFile(suffix='.py', dir=fp_dir2, delete=False)
    fp2.write(b'''
api_url = 'http://localhost:9992'
device_module = 'Dummy_Device'
idf_list = ['Dummy_Sensor']
push_interval = 10
interval = {
    'Dummy_Sensor': 1,
}
''')
    fp2.close()

    fp_dir2_name = os.path.basename(fp_dir2)
    c = os.path.basename(fp2.name)
    c = os.path.splitext(c)[0]
    c = os.path.join(fp_dir2_name, c)

    d = os.path.basename(fp2.name)
    d = os.path.join(fp_dir2_name, d)

    yield a
    yield b
    yield c
    yield d


@pytest.mark.parametrize("fname", fname())
def test_load_module(fname):
    m = load_module(fname)
    assert m
    assert m.__dict__
    assert m.__dict__['api_url'] == 'http://localhost:9992'
    assert m.__dict__['device_module'] == 'Dummy_Device'
    assert m.__dict__['idf_list'] == ['Dummy_Sensor']
    assert m.__dict__['push_interval'] == 10
    assert m.__dict__['interval'] == {'Dummy_Sensor': 1, }
