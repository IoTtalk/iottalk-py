import os
import sys

from setuptools import find_packages, setup

BASE_DIR = os.path.dirname(__file__)


def get_requires():
    with open(os.path.join(BASE_DIR, 'requirements.txt')) as f:
        return tuple(map(str.strip, f.readlines()))


def get_test_requires():
    with open(os.path.join(BASE_DIR, 'test-requirements.txt')) as f:
        return tuple(map(str.strip, f.readlines()))


setup(
    name='iottalk',
    version='0.0.1',
    author='the IoTtalk team',
    author_email='IoTtalkcontributors',
    maintainer='Iblis Lin',
    maintainer_email=('iblis@hs.ntnu.edu.tw'),
    url='https://github.com/IoTtalk/iottalk-py',
    packages=find_packages(exclude=['tests']),
    install_requires=get_requires(),
    tests_require=get_test_requires(),
    platforms=['Linux', 'FreeBSD'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
)
