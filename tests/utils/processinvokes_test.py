import logging
import shlex
import os as _os
import tempfile
from pathlib import Path
import pytest
import alexber.utils.processinvokes as processinvokes
from alexber.utils.processinvokes import LogPipe, LogSubProcessCall

logger = logging.getLogger(__name__)
process_invokes_logger = None
_process_invokes_logger_log = None

@pytest.fixture
def mock_log(mocker):
    ret_mock = mocker.patch.object(process_invokes_logger, 'log', side_effect=_process_invokes_logger_log, autospec=True, spec_set=True)
    return ret_mock


@pytest.fixture
def mock_file(mocker):
    open_mock = mocker.patch('.'.join(['alexber.utils.processinvokes', 'open']), create=True)
    mock_close = mocker.MagicMock()
    mock_write = mocker.MagicMock()
    open_mock.return_value.close = mock_close
    open_mock.return_value.write = mock_write

    return open_mock


def _reset_processinvokes():
    processinvokes.default_log_name  = None
    processinvokes.default_log_level = None
    processinvokes.default_logpipe_cls = None

    executor = processinvokes.executor
    if executor is not None:
        executor.shutdown(wait=False)
        # see https://gist.github.com/clchiou/f2608cbe54403edb0b13
        #import concurrent.futures.thread
        #executor._threads.clear()
        #concurrent.futures.thread._threads_queues.clear()
    processinvokes.executor = None

@pytest.fixture
def processinvokesFixture(mocker):
    _reset_processinvokes()

    global process_invokes_logger
    process_invokes_logger = logging.getLogger('process_invoke_run')
    global _process_invokes_logger_log
    _process_invokes_logger_log = process_invokes_logger.log
    processinvokes.initConfig(**{'default_log_name': 'process_invoke_run'})
    yield None
    _reset_processinvokes()



def test_process_invokes(request, mocker, processinvokesFixture, mock_log):
    logger.info(f'{request._pyfuncitem.name}()')
    exp_log_msg = "simulating run_sub_process"
    process_invoke_run = f"echo '{exp_log_msg}'"
    cmd = shlex.split(process_invoke_run)

    process_invoke_cwd = _os.getcwd()
    processinvokes.run_sub_process(*cmd, **{'kwargs':{'cwd':process_invoke_cwd}})

    pytest.assume(mock_log.call_count == 1)
    (_,logmsg), _ = mock_log.call_args
    pytest.assume(exp_log_msg == logmsg)

class MyLogPipe(LogPipe):
    pass

class MyLogSubProcessCall(LogSubProcessCall):
    pass

def test_init_config(request, mocker, processinvokesFixture):
    logger.info(f'{request._pyfuncitem.name}()')

    logPipeClassName = '.'.join([__name__, MyLogPipe.__name__])
    logSubProcessCallClassName = '.'.join([__name__, MyLogSubProcessCall.__name__])

    processinvokes.initConfig(**{'default_log_name': 'process_invoke_run',
                                 'default_logpipe_cls': logPipeClassName,
                                 'default_log_subprocess_cls': logSubProcessCallClassName,
                                 })

    pytest.assume(processinvokes.default_logpipe_cls == MyLogPipe)
    pytest.assume(processinvokes.default_log_subprocess_cls == MyLogSubProcessCall)


def test_process_invokes_file_pipe1(request, mocker, processinvokesFixture, mock_file):
    logger.info(f'{request._pyfuncitem.name}()')
    exp_log_msg = "simulating run_sub_process"
    process_invoke_run = f"echo '{exp_log_msg}'"
    cmd = shlex.split(process_invoke_run)

    process_invoke_cwd = _os.getcwd()
    filename = "my.log"
    mock_close = mocker.MagicMock()
    mock_write = mocker.MagicMock()
    mock_file.close = mock_close
    mock_file.write = mock_write
    processinvokes.initConfig(**{'default_log_name': 'process_invoke_run',
                                 'default_logpipe_cls': 'alexber.utils.processinvokes.FilePipe'
                                 })

    processinvokes.run_sub_process(*cmd, **{'cwd':process_invoke_cwd,
                                                      'logPipe': {
                                                          'kwargs' : {'fileName': filename}
                                                      }
                                                      })

    pytest.assume(mock_file.return_value.close.call_count == 1)
    pytest.assume(mock_file.return_value.write.call_count > 0)
    (logmsg,), _ = mock_file.return_value.write.call_args
    pytest.assume(f'{exp_log_msg}\n' == logmsg)

def test_process_invokes_file_pipe2(request, mocker, processinvokesFixture, mock_file):
    logger.info(f'{request._pyfuncitem.name}()')
    exp_log_msg = "simulating run_sub_process"
    process_invoke_run = f"echo '{exp_log_msg}'"
    cmd = shlex.split(process_invoke_run)

    process_invoke_cwd = _os.getcwd()
    filename = "my.log"


    processinvokes.run_sub_process(*cmd, **{'cwd':process_invoke_cwd,
                                                  'logPipe': {
                                                      'cls': 'alexber.utils.processinvokes.FilePipe',
                                                      'kwargs' : {'fileName': filename}
                                                  }
                                                  })

    pytest.assume(mock_file.return_value.close.call_count == 1)
    pytest.assume(mock_file.return_value.write.call_count > 0)
    (logmsg,), _ = mock_file.return_value.write.call_args
    pytest.assume(f'{exp_log_msg}\n' == logmsg)



if __name__ == "__main__":
    pytest.main([__file__])
