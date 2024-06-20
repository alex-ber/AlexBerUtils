#one-time setup
import os
cwd = os.getcwd()
if cwd.endswith('AlexBerUtils'):
    os.chdir(os.path.join(cwd, 'data'))

import pytest


isyamlrelatedfound = False
try:
    #python -m pip install .[yaml]
    import alexber.utils._ymlparsers_extra as ymlparsers_extra
    if ymlparsers_extra._isHiYaPyCoAvailable and ymlparsers_extra._isJinja2DefaultAvailable:
        isyamlrelatedfound = True
except ImportError:
    pass

isnumpyfound = False
try:
    import numpy as np
    isnumpyfound = True
except ImportError:
    pass



#see https://docs.pytest.org/en/latest/example/simple.html#control-skipping-of-tests-according-to-command-line-option
def skip_tests(config=None, items=None, keyword=None, reason=None):
    if items is None:
        TypeError("items can't be None")

    if reason is None:
        TypeError("reason can't be None")

    if keyword is None:
        TypeError("keyword can't be None")

    skip = pytest.mark.skip(reason=reason)
    for item in items:
        if keyword in item.keywords:
            item.add_marker(skip)



#see https://docs.pytest.org/en/latest/example/simple.html#control-skipping-of-tests-according-to-command-line-option
def pytest_collection_modifyitems(config, items):
    if not isyamlrelatedfound:
        skip_tests(items=items, keyword="yml", reason="yml is not installed..")

    if not isnumpyfound:
        skip_tests(items=items, keyword="np", reason="numpy is not installed..")

#see https://docs.pytest.org/en/latest/mark.html
#see https://docs.pytest.org/en/latest/example/simple.html#control-skipping-of-tests-according-to-command-line-option
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "yml: yml is not installed.."
    )
    config.addinivalue_line(
        "markers", "np: numpy is not installed.."
    )