import os

from contextlib import contextmanager


@contextmanager
def cd(p):
    '''
    ``cd`` with preserved current dir.
    '''
    curdir = os.getcwd()
    os.chdir(p)
    try:
        yield
    finally:
        os.chdir(curdir)
