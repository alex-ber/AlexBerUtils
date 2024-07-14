import logging
import pytest
import asyncio
import threading
import types
from alexber.utils.thread_locals import RLock, LockingCallableMixin, \
    LockingIterableMixin, LockingIterator, LockingAsyncIterableMixin, LockingAsyncIterator, LockingAccessMixin, \
    LockingPedanticObjMixin, LockingDefaultLockMixin, _coerce_base_language_model, LockingBaseLanguageModelMixin, \
    _is_pydantic_obj
from alexber.utils.thread_locals import threadlocal_var, get_threadlocal_var, del_threadlocal_var

logger = logging.getLogger(__name__)

async def example_task(return_value):
    return return_value

def create_coroutine_mock(mocker, return_value=None):
    async def mock_coroutine(*args, **kwargs):
        return return_value

    mock = mocker.AsyncMock(wraps=mock_coroutine)
    mock.__code__ = mock_coroutine.__code__
    mock.__class__ = types.FunctionType
    return mock

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

def test_sync_acquire_release(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    lock = RLock()
    assert lock.acquire() is True
    assert lock._sync_owner == threading.current_thread()
    assert lock._sync_count == 1
    lock.release()
    assert lock._sync_owner is None
    assert lock._sync_count == 0

def test_sync_reentrant(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
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
async def test_async_acquire_release(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    lock = RLock()
    assert await lock.async_acquire() is True
    assert lock._async_owner == asyncio.current_task()
    assert lock._async_count == 1
    await lock.async_release()
    assert lock._async_owner is None
    assert lock._async_count == 0

@pytest.mark.asyncio
async def test_async_reentrant(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
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

def test_sync_context_manager(request, mocker):
    lock = RLock()
    with lock:
        assert lock._sync_owner == threading.current_thread()
        assert lock._sync_count == 1
    assert lock._sync_owner is None
    assert lock._sync_count == 0

@pytest.mark.asyncio
async def test_async_context_manager(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    lock = RLock()
    async with lock:
        assert lock._async_owner == asyncio.current_task()
        assert lock._async_count == 1
    assert lock._async_owner is None
    assert lock._async_count == 0

def test_multiple_threads(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
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
async def test_multiple_tasks(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
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

def test_mixed_threads_and_tasks(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
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

@pytest.mark.asyncio
async def test_condition_variable_avoids_deadlock(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
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


def test_call_synchronous_function(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    obj = mocker.Mock(return_value="result")
    lock = mocker.Mock()
    lock.__enter__ = mocker.Mock(return_value=None)
    lock.__exit__ = mocker.Mock(return_value=None)
    mixin = LockingCallableMixin(obj=obj, lock=lock)
    result = mixin()
    assert result == "result"
    obj.assert_called_once()
    lock.__enter__.assert_called_once()
    lock.__exit__.assert_called_once()

@pytest.mark.asyncio
async def test_locking_call_asynchronous_function(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    obj = create_coroutine_mock(mocker, return_value="result")
    lock = mocker.AsyncMock()
    lock.__aenter__ = mocker.AsyncMock(return_value=None)
    lock.__aexit__ = mocker.AsyncMock(return_value=None)
    mixin = LockingCallableMixin(obj=obj, lock=lock)
    result = await mixin()
    assert result == "result"
    obj.assert_awaited_once()
    lock.__aenter__.assert_awaited_once()
    lock.__aexit__.assert_awaited_once()

def test_locking_iterable_mixin(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    obj = [1, 2, 3]
    lock = mocker.Mock()
    lock.__enter__ = mocker.Mock(return_value=None)
    lock.__exit__ = mocker.Mock(return_value=None)
    mixin = LockingIterableMixin(obj=obj, lock=lock)
    iterator = iter(mixin)
    assert isinstance(iterator, LockingIterator)

    # Iterate over the iterator once
    result = list(iterator)
    assert result == [1, 2, 3]

    # Verify the exact number of calls to __enter__ and __exit__
    assert lock.__enter__.call_count == 3 + 1   #1 for iterator exhaustion
    assert lock.__exit__.call_count == 3 + 1    #1 for iterator exhaustion

def test_locking_iterator(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    obj = iter([1, 2, 3])
    lock = mocker.Mock()
    lock.__enter__ = mocker.Mock(return_value=None)
    lock.__exit__ = mocker.Mock(return_value=None)
    iterator = LockingIterator(obj, lock)
    assert next(iterator) == 1
    assert next(iterator) == 2
    assert next(iterator) == 3
    with pytest.raises(StopIteration):
        next(iterator)
    assert lock.__enter__.call_count == 3 + 1   #1 for iterator exhaustion
    assert lock.__exit__.call_count == 3 + 1   #1 for iterator exhaustion


@pytest.mark.asyncio
async def test_locking_async_iterable_mixin(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')

    async def async_gen():
        for i in range(3):
            yield i

    obj = async_gen()
    lock = mocker.AsyncMock()
    lock.__aenter__ = mocker.AsyncMock(return_value=None)
    lock.__aexit__ = mocker.AsyncMock(return_value=None)
    mixin = LockingAsyncIterableMixin(obj=obj, lock=lock)
    async_iterator = mixin.__aiter__()
    assert isinstance(async_iterator, LockingAsyncIterator)

    result = []
    async for item in async_iterator:
        result.append(item)
    assert result == [0, 1, 2]

    # Verify the exact number of calls to __aenter__ and __aexit__
    assert lock.__aenter__.call_count == 3 + 1   #1 for iterator exhaustion
    assert lock.__aexit__.call_count == 3 + 1   #1 for iterator exhaustion


@pytest.mark.asyncio
async def test_locking_async_iterator(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')

    async def async_gen():
        for i in range(3):
            yield i

    obj = async_gen()
    lock = mocker.AsyncMock()
    lock.__aenter__ = mocker.AsyncMock(return_value=None)
    lock.__aexit__ = mocker.AsyncMock(return_value=None)
    async_iterator = LockingAsyncIterator(obj, lock)

    result = []
    async for item in async_iterator:
        result.append(item)
    assert result == [0, 1, 2]

    # Verify the exact number of calls to __aenter__ and __aexit__
    assert lock.__aenter__.call_count == 3 + 1   #1 for iterator exhaustion
    assert lock.__aexit__.call_count == 3 + 1   #1 for iterator exhaustion


def test_property_locking_access_mixin(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')

    class TestClass:
        @property
        def prop(self):
            return "value"

    obj = TestClass()
    lock = mocker.Mock()
    mixin = LockingAccessMixin(obj=obj, lock=lock)
    assert mixin.prop == "value"


def test_locking_access_sync_method(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    obj = mocker.Mock()
    lock = mocker.Mock()
    lock.__enter__ = mocker.Mock(return_value=None)
    lock.__exit__ = mocker.Mock(return_value=None)

    mixin = LockingAccessMixin(obj=obj, lock=lock)

    def sync_method():
        return "result"

    obj.sync_method = sync_method
    wrapped_method = mixin.sync_method
    result = wrapped_method()
    assert result == "result"
    lock.__enter__.assert_called_once()
    lock.__exit__.assert_called_once()


@pytest.mark.asyncio
async def test_locking_access_async_method(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    obj = mocker.Mock()
    lock = mocker.AsyncMock()
    lock.__aenter__ = mocker.AsyncMock(return_value=None)
    lock.__aexit__ = mocker.AsyncMock(return_value=None)

    mixin = LockingAccessMixin(obj=obj, lock=lock)

    async def async_method():
        return "result"

    obj.async_method = async_method
    wrapped_method = mixin.async_method()
    result = await wrapped_method
    assert result == "result"
    lock.__aenter__.assert_called_once()
    lock.__aexit__.assert_called_once()


def test_locking_access_property_handling(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')

    class TestClass:
        @property
        def prop(self):
            return "value"

    obj = TestClass()
    lock = mocker.Mock()
    lock.__enter__ = mocker.Mock(return_value=None)
    lock.__exit__ = mocker.Mock(return_value=None)

    mixin = LockingAccessMixin(obj=obj, lock=lock)
    assert mixin.prop == "value"


def test_locking_access_special_case_for_pydantic(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    mocker.patch('alexber.utils.thread_locals._is_pydantic_obj', return_value=True)

    class PydanticModel:
        def _copy_and_set_values(self):
            pass

    obj = PydanticModel()
    lock = mocker.Mock()
    lock.__enter__ = mocker.Mock(return_value=None)
    lock.__exit__ = mocker.Mock(return_value=None)

    mixin = LockingAccessMixin(obj=obj, lock=lock)
    wrapped_method = mixin._copy_and_set_values
    result = wrapped_method()
    assert result == mixin
    lock.__enter__.assert_called_once()
    lock.__exit__.assert_called_once()

def test_locking_default_lock_initialization_with_provided_lock(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    obj = mocker.Mock()
    lock = mocker.Mock()
    mixin = LockingDefaultLockMixin(obj=obj, lock=lock)
    assert mixin._lock == lock

def test_locking_default_lock_initialization_without_provided_lock(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    obj = mocker.Mock()
    mock_rlock = mocker.patch('alexber.utils.thread_locals.RLock', autospec=True)
    mixin = LockingDefaultLockMixin(obj=obj)
    assert isinstance(mixin._lock, RLock)
    mock_rlock.assert_called_once()

def test_coerce_base_language_model_not_available(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    mocker.patch('alexber.utils.thread_locals._is_available_base_language_model', False)

    obj = mocker.Mock()
    _coerce_base_language_model(obj)
    # Ensure that no further action is taken when the model is not available
    # Since we are mocking, we should check that BaseLanguageModel.register is not called
    assert not mocker.patch('alexber.utils.thread_locals.BaseLanguageModel').register.called


def test_coerce_base_language_model_with_base_language_model(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    mocker.patch('alexber.utils.thread_locals._is_available_base_language_model', True)

    class MockBaseLanguageModel:
        @staticmethod
        def register(cls):
            pass

    mocker.patch('alexber.utils.thread_locals.BaseLanguageModel', MockBaseLanguageModel)

    class TestModel:
        _obj = MockBaseLanguageModel()

    obj = TestModel()
    mock_register = mocker.patch.object(MockBaseLanguageModel, 'register')
    _coerce_base_language_model(obj)
    mock_register.assert_called_once_with(type(obj))


def test_coerce_base_language_model_with_non_base_language_model(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    mocker.patch('alexber.utils.thread_locals._is_available_base_language_model', True)

    class MockBaseLanguageModel:
        @staticmethod
        def register(cls):
            pass

    mocker.patch('alexber.utils.thread_locals.BaseLanguageModel', MockBaseLanguageModel)

    class TestModel:
        _obj = mocker.Mock()

    proxy = TestModel()
    mock_register = mocker.patch.object(MockBaseLanguageModel, 'register')
    _coerce_base_language_model(proxy)
    mock_register.assert_not_called()


def test_locking_base_language_model_mixin_calls_coerce(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    # Mock the availability flag
    mocker.patch('alexber.utils.thread_locals._is_available_base_language_model', True)

    # Mock the BaseLanguageModel as a type
    class MockBaseLanguageModel:
        @staticmethod
        def register(cls):
            pass

    mocker.patch('alexber.utils.thread_locals.BaseLanguageModel', MockBaseLanguageModel)

    # Mock the _coerce_base_language_model function
    mock_coerce = mocker.patch('alexber.utils.thread_locals._coerce_base_language_model')
    class MockRootMixin:
        pass
    class LockingBaseLanguageModelMixin(MockRootMixin, MockBaseLanguageModel):
        def __init__(self, **kwargs):
            self._obj = kwargs.get('obj')
            mock_coerce(self)
    obj = mocker.Mock()
    instance = LockingBaseLanguageModelMixin(obj=obj)
    mock_coerce.assert_called_once_with(instance)

def test_coerce_base_language_model_checks_proxy_obj(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    mocker.patch('alexber.utils.thread_locals._is_available_base_language_model', True)
    class MockBaseLanguageModel:
        @staticmethod
        def register(cls):
            pass
    mocker.patch('alexber.utils.thread_locals.BaseLanguageModel', MockBaseLanguageModel)
    class TestModel:
        _obj = MockBaseLanguageModel()
    proxy = TestModel()
    mock_register = mocker.patch.object(MockBaseLanguageModel, 'register')
    _coerce_base_language_model(proxy)
    mock_register.assert_called_once_with(type(proxy))
    # Ensure that the function checks proxy.obj and not just obj
    assert isinstance(proxy._obj, MockBaseLanguageModel)


# Define a mock BaseModel class
class MockBaseModel:
    pass


@pytest.fixture
def mocker_pydantic(mocker):
    # Mock the availability of pydantic v1 and v2
    mocker.patch('alexber.utils.thread_locals._is_available_pydantic_v1', True)
    mocker.patch('alexber.utils.thread_locals._is_available_pydantic_v2', True)
    # Mock the import of pydantic and its BaseModel
    mocker.patch.dict('sys.modules', {
        'pydantic': mocker.MagicMock(BaseModel=MockBaseModel),
        'pydantic.v1': mocker.MagicMock(BaseModel=MockBaseModel)
    })
    return mocker


def test_is_pydantic_obj_with_pydantic_model(request, mocker_pydantic):
    logger.info(f'{request.node.name}()')

    # Create an instance of the mock BaseModel
    obj = MockBaseModel()

    # Call the function and assert the result
    result = _is_pydantic_obj(obj)
    assert result is True


def test_is_pydantic_obj_with_pydantic_v1_unavailable(request, mocker):
    logger.info(f'{request.node.name}()')

    # Mock the availability of pydantic v1
    mocker.patch('alexber.utils.thread_locals._is_available_pydantic_v1', False)
    mocker.patch('alexber.utils.thread_locals._is_available_pydantic_v2', True)

    # Mock the import of pydantic.v1 to raise ImportError
    mocker.patch.dict('sys.modules', {'pydantic.v1': None})
    mocker.patch.dict('sys.modules', {'pydantic': mocker.MagicMock(BaseModel=MockBaseModel)})

    # Create an instance of the mock BaseModel
    obj = MockBaseModel()

    # Call the function and assert the result
    result = _is_pydantic_obj(obj)
    assert result is True


def test_is_pydantic_obj_with_pydantic_v2_unavailable(request, mocker):
    logger.info(f'{request.node.name}()')

    # Mock the availability of pydantic v2
    mocker.patch('alexber.utils.thread_locals._is_available_pydantic_v1', True)
    mocker.patch('alexber.utils.thread_locals._is_available_pydantic_v2', False)

    # Mock the import of pydantic to raise ImportError
    mocker.patch.dict('sys.modules', {'pydantic': None})
    mocker.patch.dict('sys.modules', {'pydantic.v1': mocker.MagicMock(BaseModel=MockBaseModel)})

    # Create an instance of the mock BaseModel
    obj = MockBaseModel()

    # Call the function and assert the result
    result = _is_pydantic_obj(obj)
    assert result is True


def test_is_pydantic_obj_with_import_error(request, mocker):
    logger.info(f'{request.node.name}()')

    # Mock the import of pydantic to raise ImportError
    mocker.patch.dict('sys.modules', {'pydantic': None, 'pydantic.v1': None})

    # Create an instance of the mock BaseModel
    obj = MockBaseModel()

    # Call the function and assert the result
    result = _is_pydantic_obj(obj)
    assert result is False


def test_is_pydantic_obj_with_non_pydantic_object(request, mocker_pydantic):
    logger.info(f'{request.node.name}()')

    # Create an instance of a non-pydantic object
    class NonPydanticObject:
        pass

    obj = NonPydanticObject()

    # Call the function and assert the result
    result = _is_pydantic_obj(obj)
    assert result is False


def test_is_pydantic_obj_with_pydantic_object_mixin(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    mocker.patch('alexber.utils.thread_locals._is_pydantic_obj', return_value=True)
    obj = mocker.Mock()
    mixin = LockingPedanticObjMixin(obj=obj)
    assert mixin._is_pedantic_obj is True


def test_is_pydantic_obj_with_non_pydantic_object_mixin(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    mocker.patch('alexber.utils.thread_locals._is_pydantic_obj', return_value=False)
    obj = mocker.Mock()
    mixin = LockingPedanticObjMixin(obj=obj)
    assert mixin._is_pedantic_obj is False

if __name__ == "__main__":
    pytest.main([__file__])
