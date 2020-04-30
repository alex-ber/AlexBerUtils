import logging
import shlex
import os as _os
import pytest
import alexber.utils.processinvokes as processinvokes

logger = logging.getLogger(__name__)
process_invokes_logger = None
_process_invokes_logger_log = None

@pytest.fixture
def mock_log(mocker):
    ret_mock = mocker.patch.object(process_invokes_logger, 'log', side_effect=_process_invokes_logger_log, autospec=True, spec_set=True)
    return ret_mock


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


if __name__ == "__main__":
    pytest.main([__file__])
