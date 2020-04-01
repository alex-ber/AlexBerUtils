import logging
import pytest

logger = logging.getLogger(__name__)
from io import StringIO

from alexber.utils.warns import warnings, initConfig as warnsInitConfig
from alexber.utils.mains import fixabscwd, initConfig as mainInitConfig

def test_warns(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')

    buf = StringIO()
    warnsInitConfig(file=buf, log_name=request._pyfuncitem.name)

    filename = __name__
    message = f"This is the message"

    warnings.showwarning(message, filename=filename)

    result = buf.getvalue().rstrip()
    pytest.assume(result.endswith(message))
    pytest.assume(result.startswith(filename))


def get_content(full_filename):
    with open(full_filename) as f:
        content = f.read().splitlines()
    return content


def test_warns_file(request, tmp_path, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    log_file_name = 'a.log'

    log_file_path = tmp_path / log_file_name

    full_log_file_name = str(log_file_path.resolve())  # relative to cwd

    warnsInitConfig(file=full_log_file_name, log_name=request._pyfuncitem.name)

    filename = __name__
    message = f"This is the message"

    warnings.showwarning(message, filename=filename)

    file_lines = get_content(full_log_file_name)
    length = len(file_lines)
    assert length == 1
    result = file_lines[0]

    pytest.assume(result.endswith(message))
    pytest.assume(result.startswith(filename))


def confiugeLogger(stream, log_name):
    # simulate logger initilaization
    warnings_logger = logging.getLogger(log_name)
    h = logging.StreamHandler(stream=stream)
    formatter = logging.Formatter('%(asctime)-15s %(levelname)s [%(name)s.%(funcName)s] %(message)s')
    h.setFormatter(formatter)
    warnings_logger.addHandler(h)


def test_warns_configured_log(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')

    buf = StringIO()
    warnsInitConfig(log_level=logging.INFO, log_name=request._pyfuncitem.name)

    confiugeLogger(buf, log_name=request._pyfuncitem.name)

    filename = __name__
    message = f"This is the message"
    logLevel = logging.getLevelName(logging.INFO)

    warnings.showwarning(message, filename=filename)

    result = buf.getvalue()
    result = result.rstrip()
    pytest.assume(result.endswith(message))
    pytest.assume(logLevel in result)
    pytest.assume(__name__ in result)


def test_warns_preconfigured_log(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')

    buf = StringIO()
    confiugeLogger(buf, log_name=request._pyfuncitem.name)

    warnsInitConfig(log_level=logging.INFO, log_name=request._pyfuncitem.name)

    filename = __name__
    message = f"This is the message"
    logLevel = logging.getLevelName(logging.INFO)

    warnings.showwarning(message, filename=filename)

    result = buf.getvalue()
    result = result.rstrip()
    pytest.assume(result.endswith(message))
    pytest.assume(logLevel in result)
    pytest.assume(__name__ in result)

def test_warns_it(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')

    buf_stdout = StringIO()
    buf_stderr = StringIO()


    mainInitConfig(warns={'file': buf_stdout,
                           'log_level': logging.INFO})
    fixabscwd()

    warnsInitConfig(file=buf_stderr, log_level=logging.WARNING)
    warnings.showwarning(f"This is last warning", filename=__name__)

    result_out = buf_stdout.getvalue()
    result_out = result_out.rstrip()
    length = len(result_out)
    pytest.assume(length>0)

    result_err = buf_stderr.getvalue()
    result_err = result_err.rstrip()
    length = len(result_err)
    pytest.assume(length > 0)



    logger.info(result_out)
    logger.warning(result_err)



if __name__ == "__main__":
    pytest.main([__file__])
