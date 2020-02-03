import os
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
    fp = tempfile.mktemp(prefix='iottalkpy', suffix='.py')

    if request.param == ('abs', 'py'):
        yield fp
    elif request.param == ('abs', 'no-py'):
        yield os.path.splitext(fp)[0]
    elif request.param[0] == 'rel':
        h, t = os.path.split(fp)
        os.chdir(h)

        if request.param == ('rel', 'py'):
            yield t
        elif request.param == ('rel', 'no-py'):
            yield os.path.splitext(t)[0]
    else:
        raise ValueError('unknow dai path type: {}',format(request.param))


@pytest.mark.parametrize('dai_path', dai_path_cases, indirect=True)
def test_load_module_nonexists(dai_path):
    m = load_module(dai_path)
    assert m
