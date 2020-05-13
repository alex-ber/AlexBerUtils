import logging
from pathlib import Path
import pytest

logger = logging.getLogger(__name__)

from alexber.utils.mains import fixabscwd, logger as real_logger
import os
import sys


_real_info = real_logger.info

@pytest.fixture(scope='module')
def loggingCaptureWarnings():
    logging.captureWarnings(True)

@pytest.fixture
def mock_os(mocker):
    ret_mock = mocker.patch('.'.join(['alexber.utils.mains', '_os']), autospec=True, spec_set=True)

    cwd = str(Path(__file__).resolve().parent)
    ret_mock.getcwd.return_value = cwd
    ret_mock.path = os.path

    return ret_mock

@pytest.fixture
def mock_info(mocker):
    ret_mock = mocker.patch.object(real_logger, 'info', side_effect=_real_info, autospec=True, spec_set=True)
    return ret_mock

@pytest.fixture
def mock_main_module(mocker):
    ret_mock = sys.modules['__main__']
    mocker.patch.object(ret_mock, '__file__', new=__file__)
    return ret_mock


def test_fixabscwd(request, loggingCaptureWarnings, mock_os, mock_info, mock_main_module):
    logger.info(f'{request._pyfuncitem.name}()')

    fixabscwd()

    pytest.assume(mock_info.call_count > 0)

    pytest.assume(mock_os.chdir.call_count == 1)
    (newcwd,), _ = mock_os.chdir.call_args
    pytest.assume(str(Path(__file__).parent)==newcwd)




if __name__ == "__main__":
    pytest.main([__file__])
