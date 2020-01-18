import tempfile
import os
import pytest
import shutil
from iottalkpy.dai import load_module

@pytest.fixture
def fname():
    fp_dir1 = tempfile.mkdtemp()
    fp1 = tempfile.NamedTemporaryFile(suffix='.py', 
        dir = fp_dir1, delete=False)

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
    fp2 = tempfile.NamedTemporaryFile(suffix='.py',
        dir=fp_dir2, delete=False)

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

    yield [a, b, c, d]
    os.unlink(fp1.name)
    shutil.rmtree(fp_dir2)
    shutil.rmtree(fp_dir1)

def test_load_module1(fname):
    m = load_module(fname[0])
    assert m
    assert m.__dict__
    assert m.__dict__['api_url'] == 'http://localhost:9992'
    assert m.__dict__['device_module'] == 'Dummy_Device'
    assert m.__dict__['idf_list'] == ['Dummy_Sensor']
    assert m.__dict__['push_interval'] == 10
    assert m.__dict__['interval'] == {'Dummy_Sensor': 1,}

def test_load_module2(fname):
    m = load_module(fname[1])
    assert m
    assert m.__dict__
    assert m.__dict__['api_url'] == 'http://localhost:9992'
    assert m.__dict__['device_module'] == 'Dummy_Device'
    assert m.__dict__['idf_list'] == ['Dummy_Sensor']
    assert m.__dict__['push_interval'] == 10
    assert m.__dict__['interval'] == {'Dummy_Sensor': 1,}

def test_load_module3(fname):
    m = load_module(fname[2])
    assert m
    assert m.__dict__
    assert m.__dict__['api_url'] == 'http://localhost:9992'
    assert m.__dict__['device_module'] == 'Dummy_Device'
    assert m.__dict__['idf_list'] == ['Dummy_Sensor']
    assert m.__dict__['push_interval'] == 10
    assert m.__dict__['interval'] == {'Dummy_Sensor': 1,}

def test_load_module4(fname):
    m = load_module(fname[3])
    assert m
    assert m.__dict__
    assert m.__dict__['api_url'] == 'http://localhost:9992'
    assert m.__dict__['device_module'] == 'Dummy_Device'
    assert m.__dict__['idf_list'] == ['Dummy_Sensor']
    assert m.__dict__['push_interval'] == 10
    assert m.__dict__['interval'] == {'Dummy_Sensor': 1,}
