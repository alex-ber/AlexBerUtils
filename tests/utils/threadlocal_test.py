import logging
import pytest
import asyncio
import threading
from alexber.utils.thread_locals import RLock
from alexber.utils.thread_locals import threadlocal_var, get_threadlocal_var, del_threadlocal_var


logger = logging.getLogger(__name__)



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




def test_sync_acquire_release():
    lock = RLock()
    assert lock.acquire() is True
    assert lock._sync_owner == threading.current_thread()
    assert lock._sync_count == 1
    lock.release()
    assert lock._sync_owner is None
    assert lock._sync_count == 0

def test_sync_reentrant():
    lock = RLock()
    assert lock.acquire() is True
    assert lock.acquire() is True
    assert lock._sync_owner == threading.current_thread()
    assert lock._sync_count == 2
    lock.release()
    assert lock._sync_count == 1
    lock.release()
    assert lock._sync_owner is None
    assert lock._sync_count == 0

@pytest.mark.asyncio
async def test_async_acquire_release():
    lock = RLock()
    assert await lock.async_acquire() is True
    assert lock._async_owner == asyncio.current_task()
    assert lock._async_count == 1
    await lock.async_release()
    assert lock._async_owner is None
    assert lock._async_count == 0

@pytest.mark.asyncio
async def test_async_reentrant():
    lock = RLock()
    assert await lock.async_acquire() is True
    assert await lock.async_acquire() is True
    assert lock._async_owner == asyncio.current_task()
    assert lock._async_count == 2
    await lock.async_release()
    assert lock._async_count == 1
    await lock.async_release()
    assert lock._async_owner is None
    assert lock._async_count == 0

def test_sync_context_manager():
    lock = RLock()
    with lock:
        assert lock._sync_owner == threading.current_thread()
        assert lock._sync_count == 1
    assert lock._sync_owner is None
    assert lock._sync_count == 0

@pytest.mark.asyncio
async def test_async_context_manager():
    lock = RLock()
    async with lock:
        assert lock._async_owner == asyncio.current_task()
        assert lock._async_count == 1
    assert lock._async_owner is None
    assert lock._async_count == 0

def test_multiple_threads():
    lock = RLock()
    results = []

    def thread_task(thread_id):
        for _ in range(5):
            with lock:
                results.append(f"Thread {thread_id} acquired lock")
                assert lock._sync_owner == threading.current_thread()
                assert lock._sync_count == 1
            results.append(f"Thread {thread_id} released lock")

    threads = [threading.Thread(target=thread_task, args=(i,)) for i in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(results) == 30  # 3 threads * 5 iterations * 2 messages per iteration

@pytest.mark.asyncio
async def test_multiple_tasks():
    lock = RLock()
    results = []

    async def task_task(task_id):
        for _ in range(5):
            async with lock:
                results.append(f"Task {task_id} acquired lock")
                assert lock._async_owner == asyncio.current_task()
                assert lock._async_count == 1
            results.append(f"Task {task_id} released lock")

    tasks = [task_task(i) for i in range(3)]
    await asyncio.gather(*tasks)

    assert len(results) == 30  # 3 tasks * 5 iterations * 2 messages per iteration

def test_mixed_threads_and_tasks():
    lock = RLock()
    results = []

    def thread_task(thread_id):
        for _ in range(5):
            with lock:
                results.append(f"Thread {thread_id} acquired lock")
                assert lock._sync_owner == threading.current_thread()
                assert lock._sync_count == 1
            results.append(f"Thread {thread_id} released lock")

    async def async_task(task_id):
        for _ in range(5):
            async with lock:
                results.append(f"Task {task_id} acquired lock")
                assert lock._async_owner == asyncio.current_task()
                assert lock._async_count == 1
            results.append(f"Task {task_id} released lock")

    threads = [threading.Thread(target=thread_task, args=(i,)) for i in range(2)]
    for thread in threads:
        thread.start()

    async def run_async_tasks():
        tasks = [asyncio.create_task(async_task(i)) for i in range(2)]
        await asyncio.gather(*tasks)

    asyncio.run(run_async_tasks())

    for thread in threads:
        thread.join()

    assert len(results) == 40  # 2 threads * 5 iterations * 2 messages per iteration + 2 tasks * 5 iterations * 2 messages per iteration

if __name__ == "__main__":
    pytest.main([__file__])
