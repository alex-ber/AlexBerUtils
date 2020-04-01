import logging
from pathlib import Path
import pytest

logger = logging.getLogger(__name__)
from io import StringIO

from alexber.utils.mains import initConfig as mainInitConfig, fixabscwd, sys
import os


def test_fixabscwd(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')

    buf = StringIO()
    mainInitConfig(warns={'file':buf, 'log_name':request._pyfuncitem.name})

    mock_os = mocker.patch('.'.join(['alexber.utils.mains', '_os']), autospec=True, spec_set=True)

    cwd = str(Path(__file__).resolve().parent)
    mock_os.getcwd.return_value = cwd
    mock_os.path = os.path

    main_module = sys.modules['__main__']
    mocker.patch.object(main_module, '__file__', new=__file__)

    fixabscwd()

    result = buf.getvalue().rstrip()
    result = result.split()
    length = len(result)
    pytest.assume(length>0)

    pytest.assume(mock_os.chdir.call_count == 1)
    (newcwd,), _ = mock_os.chdir.call_args
    pytest.assume(str(Path(__file__).parent)==newcwd)




if __name__ == "__main__":
    pytest.main([__file__])
