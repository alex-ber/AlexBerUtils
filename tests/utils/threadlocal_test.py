import logging
import pytest
import threading

logger = logging.getLogger(__name__)

from alexber.utils.thread_locals import threadlocal_var, get_threadlocal_var, del_threadlocal_var
import random

def test_get_threadlocal_var_empty(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    thread_locals = threading.local()

    with pytest.raises(ValueError):
        get_threadlocal_var(thread_locals, 'value')

    with pytest.raises(ValueError):
        get_threadlocal_var(thread_locals, 'nonexist')


def test_get_threadlocal_var_exist(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    thread_locals = threading.local()

    expValue = 1
    thread_locals.value = expValue

    value = get_threadlocal_var(thread_locals, 'value')
    assert expValue == value

    with pytest.raises(ValueError):
        get_threadlocal_var(thread_locals, 'nonexist')


ns = threading.local()
stop = 10

class Worker(threading.Thread):

    def run(self):
        w_logger = logging.getLogger(self.name)
        i = 0
        ns.val = 0

        for i in range(stop):
            ns.val += 1
            i+=1
            w_logger.debug(f"Thread: {self.name}, value: {ns.val}")
            value = get_threadlocal_var(ns, "val")
            assert i == value
        value = get_threadlocal_var(ns, "val")
        assert stop==value


def test_get_threadlocal_var_exist_different_thread(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')

    w1 = Worker()
    w2 = Worker()
    w1.start()
    w2.start()
    w1.join()
    w2.join()

    with pytest.raises(ValueError):
        get_threadlocal_var(ns, 'val')

    with pytest.raises(ValueError):
        get_threadlocal_var(ns, 'nonexist')


def test_del_threadlocal_var_empy(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    thread_locals = threading.local()

    del_threadlocal_var(thread_locals, 'value')

    with pytest.raises(ValueError):
        get_threadlocal_var(ns, 'value')

    with pytest.raises(ValueError):
        get_threadlocal_var(thread_locals, 'nonexist')


def test_del_threadlocal_var_exist(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    thread_locals = threading.local()

    thread_locals.value = 1

    del_threadlocal_var(thread_locals, 'value')

    with pytest.raises(ValueError):
        get_threadlocal_var(ns, 'value')

    with pytest.raises(ValueError):
        get_threadlocal_var(thread_locals, 'nonexist')

class Box(object):

    def __init__(self, value):
        self._value = value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value


def test_threadlocal_var_empty(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    thread_locals = threading.local()

    expValue = 5
    box = threadlocal_var(thread_locals, 'value', Box, value=expValue)
    value = box.value
    assert expValue == value

    box2 = get_threadlocal_var(thread_locals, 'value')
    value2 = box2.value
    assert expValue == value2

    assert box == box2

    with pytest.raises(ValueError):
        get_threadlocal_var(thread_locals, 'nonexist')


def test_threadlocal_var_exists(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    thread_locals = threading.local()

    expValue = 5
    box = threadlocal_var(thread_locals, 'value', Box, value=expValue)
    value = box.value
    assert expValue == value

    box2= threadlocal_var(thread_locals, 'value', Box, value=100)
    value2 = box2.value
    assert expValue == value2

    assert box == box2

    box3 = threadlocal_var(thread_locals, 'value', Box)
    value3 = box3.value
    assert expValue == value3

    assert box == box3

    with pytest.raises(ValueError):
        get_threadlocal_var(thread_locals, 'nonexist')







if __name__ == "__main__":
    pytest.main([__file__])
