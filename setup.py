import os
import sys

from setuptools import find_packages, setup
from setuptools import __version__ as setuptools_ver

import iottalkpy

BASE_DIR = os.path.dirname(__file__)
REQUIRE_DIR = os.path.join(BASE_DIR, 'requirements')


def readlines(fname):
    with open(os.path.join(REQUIRE_DIR, fname)) as f:
        return tuple(map(str.strip, f.readlines()))


def get_requires():
    if (sys.version_info.major, sys.version_info.minor) == (3, 4):
        fname = 'python34.txt'
    else:
        fname = 'python3.txt'

    # in case of setuptools is old and not support `install_requires` with version
    # e.g. The setuptools of Arduino Yun Rev1 is v0.6.
    major = int(setuptools_ver.partition('.')[0])
    if major < 20:
        fname = 'compat.txt'

    return readlines(fname)


def get_test_requires():
    return readlines('test.txt')


setup(
    name='iottalk-py',
    version=iottalkpy.version,
    author='the IoTtalk team',
    author_email='iblis@hs.ntnu.edu.tw',
    maintainer='Iblis Lin',
    maintainer_email=('iblis@hs.ntnu.edu.tw'),
    url='https://github.com/IoTtalk/iottalk-py',
    packages=find_packages(exclude=['tests']),
    install_requires=get_requires(),
    tests_require=get_test_requires(),
    long_description=open(os.path.join(BASE_DIR, 'README.rst')).read(),
    long_description_content_type='text/x-rst',
    platforms=['Linux', 'FreeBSD'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
)
