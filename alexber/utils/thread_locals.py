import logging
import concurrent.futures
import contextvars
import functools
import inspect
from concurrent.futures import Executor, Future
from contextvars import copy_context
from typing import Callable, Optional, TypeVar, Awaitable, Union
from threading import local
import asyncio
import threading
from collections import deque
from contextvars import ContextVar
from typing import Callable, Any, List, Dict

# Define type variables for the function signature
T = TypeVar('T')

# Define a type that can be awaited and will return T, compatible with both asyncio.Future and concurrent.futures.Future
FutureType = Union[Awaitable[T], concurrent.futures.Future]

logger = logging.getLogger(__name__)


#should be initlialzied via initConfig() method, see below.
_EVENT_LOOP = None


# _GLOBAL_EXECUTOR is a global variable that holds the default executor for executing tasks
# when no specific executor is provided to the exec_in_executor() function.
#
# This allows for centralized management of task execution resources, ensuring that tasks are
# executed in a consistent and controlled manner across the application.
#
# The executor can be set during the initialization of the application or through configuration
# functions like initConfig(), providing flexibility in how tasks are managed and executed.
#
# If _GLOBAL_EXECUTOR is not set, the default asyncio executor will be used.
_GLOBAL_EXECUTOR = None

# Thread-local storage to hold the event loop for each thread
_event_loops_thread_locals = local()

# _CLOSE_SENTINEL is a unique object used as a marker to signal the worker to stop processing tasks.
# It is enqueued into the task queue to indicate that no more tasks will be added and the worker should exit.
# This approach allows for a clean shutdown of the worker loop without requiring additional control structures.
_CLOSE_SENTINEL = object()

def threadlocal_var(thread_locals, varname, factory, *args, **kwargs):
  v = getattr(thread_locals, varname, None)
  if v is None:
    v = factory(*args, **kwargs)
    setattr(thread_locals, varname, v)
  return v

def get_threadlocal_var(thread_locals, varname):
    v = threadlocal_var(thread_locals, varname, lambda : None)
    if v is None:
        raise ValueError(f"threadlocal's {varname} is not initilized")
    return v

def del_threadlocal_var(thread_locals, varname):
    try:
        delattr(thread_locals, varname)
    except AttributeError:
        pass


class RootMixin:
    """
    A mixin class that serves as the root of a delegation chain.

    The `RootMixin` class provides an initializer that stops the delegation chain,
    ensuring that no further delegation occurs.

    Methods:
    __init__(**kwargs): Initializes the mixin and stops the delegation chain.
    """
    def __init__(self, **kwargs):
        # The delegation chain stops here
        pass

def validate_param(param_value, param_name):
    """
     Validates that a required parameter is not None.

     param_value (any): The value of the parameter to be validated.
     param_name (str): The name of the parameter to be used in the error message.

     Raises:
     ValueError: If the parameter value is None, indicating that the required parameter is missing.
     """
    if param_value is None:
        raise ValueError(f"Expected {param_name} param not found")



class RLock:
    """
    A reentrant lock that supports both synchronous and asynchronous operations.
    The `RLock` class provides mechanisms to acquire and release locks in both synchronous
    and asynchronous contexts, ensuring proper synchronization and reentrancy.

    See https://alex-ber.medium.com/a6b9a9021be8 for more details.
    """

    def __init__(self):
        """
        Initializes the RLock instance with both synchronous and asynchronous locks.
        """
        self._sync_lock = threading.RLock()  # Synchronous reentrant lock
        self._async_lock = asyncio.Lock()  # Asynchronous lock

        self._sync_owner = None  # Owner of the synchronous lock
        self._async_owner = None  # Owner of the asynchronous lock

        self._sync_count = 0  # Reentrancy count for synchronous lock
        self._async_count = 0  # Reentrancy count for asynchronous lock

        self._sync_condition = threading.Condition(self._sync_lock)  # Condition variable for synchronization
        self._async_condition = asyncio.Condition()  # Asynchronous condition variable

        self._sync_waiting = deque()  # Queue for waiting synchronous threads
        self._async_waiting = deque()  # Queue for waiting asynchronous tasks

    def acquire(self):
        """
        Acquires the synchronous lock, blocking until it is available.
        Returns:
            bool: True if the lock was successfully acquired.
        """
        with self._sync_condition:
            current_thread = threading.current_thread()
            if self._sync_owner is current_thread:
                self._sync_count += 1
                return True  # Already acquired, no need to acquire again

            self._sync_waiting.append(current_thread)
            while self._sync_owner is not None or self._sync_waiting[0] != current_thread:
                self._sync_condition.wait()  # Wait until the lock is available

            self._sync_waiting.popleft()
            self._sync_owner = current_thread
            self._sync_count = 1
            return True  # Successfully acquired

    def release(self):
        """
        Releases the synchronous lock.
        Returns:
            bool: True if the lock was successfully released.
        Raises:
            RuntimeError: If the current thread does not own the lock.
        """
        with self._sync_condition:
            current_thread = threading.current_thread()
            if self._sync_owner is current_thread:
                self._sync_count -= 1
                if self._sync_count == 0:
                    self._sync_owner = None
                    self._sync_condition.notify_all()  # Notify all waiting threads
                return True  # Successfully released
            else:
                raise RuntimeError("Cannot release a lock that's not owned by the current thread")

    async def async_acquire(self):
        """
        Acquires the asynchronous lock, blocking until it is available.
        Returns:
            bool: True if the lock was successfully acquired.
        """
        async with self._async_condition:
            current_task = asyncio.current_task()
            if self._async_owner is current_task:
                self._async_count += 1
                return True  # Already acquired, no need to acquire again

            self._async_waiting.append(current_task)

            while self._async_owner is not None or self._async_waiting[0] != current_task:
                await self._async_condition.wait()  # Wait until the lock is available

            self._async_waiting.popleft()  # Remove the task from waiting queue once it acquires the lock
            self._async_owner = current_task
            self._async_count = 1
            return True  # Successfully acquired

    async def async_release(self):
        """
        Releases the asynchronous lock.
        Returns:
            bool: True if the lock was successfully released.
        Raises:
            RuntimeError: If the current task does not own the lock.
        """
        async with self._async_condition:
            current_task = asyncio.current_task()
            if self._async_owner is current_task:
                self._async_count -= 1
                if self._async_count == 0:
                    self._async_owner = None
                    self._async_condition.notify_all()  # Notify all waiting tasks
                return True  # Successfully released
            else:
                raise RuntimeError("Cannot release a lock that's not owned by the current task")

    def __enter__(self):
        """
        Enters the runtime context related to this object, acquiring the synchronous lock.
        """
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb):
        """
        Exits the runtime context related to this object, releasing the synchronous lock.
        """
        self.release()

    async def __aenter__(self):
        """
        Enters the runtime context related to this object, acquiring the asynchronous lock.
        """
        await self.async_acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """
        Exits the runtime context related to this object, releasing the asynchronous lock.
        """
        await self.async_release()

class LockingIterableMixin(RootMixin):
    """
    A mixin class that provides locking for iterable objects.

    The `LockingIterableMixin` class ensures that iteration over the wrapped
    iterable object is thread-safe by using a provided lock.

    """
    def __init__(self, **kwargs):
        """
        Initializes the mixin with the iterable object and lock.

        Parameters:
        **kwargs: Arbitrary keyword arguments, including 'obj' for the iterable object
                  and 'lock' for the lock.
        """
        super().__init__(**kwargs)
        self._obj = kwargs.get('obj')
        validate_param(self._obj, 'obj')
        self._lock = kwargs.get('lock')
        validate_param(self._lock, 'lock')

    def __iter__(self):
        """
        Returns a locking iterator for the iterable object.

        Returns:
        LockingIterator: A locking iterator for the iterable object.
        """
        return LockingIterator(iter(self._obj), self._lock)

class LockingIterator:
    """
    An iterator that provides locking for thread-safe iteration.

    The `LockingIterator` class ensures that iteration over the wrapped
    iterator is thread-safe by using a provided lock.

    """
    def __init__(self, iterator, lock):
        """
        Initializes the iterator with the wrapped iterator and lock.

        Parameters:
        iterator (iterator): The wrapped iterator.
        lock (RLock): The lock to be used for synchronization.
        """
        self._iterator = iterator
        self._lock = lock

    def __iter__(self):
        """
        Returns the iterator itself.

        Returns:
        LockingIterator: The iterator itself.
        """
        return self

    def __next__(self):
        """
        Returns the next item from the iterator, acquiring the lock.

        Returns:
        any: The next item from the iterator.

        Raises:
        StopIteration: If the iterator is exhausted.
        """
        with self._lock:
            return next(self._iterator)

class LockingAsyncIterableMixin(RootMixin):
    """
    A mixin class that provides locking for asynchronous iterable objects.

    The `LockingAsyncIterableMixin` class ensures that iteration over the wrapped
    asynchronous iterable object is thread-safe by using a provided lock.

    """
    def __init__(self, **kwargs):
        """
        Initializes the mixin with the asynchronous iterable object and lock.

        Parameters:
        **kwargs: Arbitrary keyword arguments, including 'obj' for the asynchronous iterable object
                  and 'lock' for the lock.
        """
        super().__init__(**kwargs)
        self._obj = kwargs.get('obj')
        validate_param(self._obj, 'obj')
        self._lock = kwargs.get('lock')
        validate_param(self._lock, 'lock')

    def __aiter__(self):
        """
        Returns a locking asynchronous iterator for the iterable object.

        Returns:
        LockingAsyncIterator: A locking asynchronous iterator for the iterable object.
        """
        return LockingAsyncIterator(self._obj, self._lock)


class LockingAsyncIterator:
    """
    An asynchronous iterator that provides locking for thread-safe iteration.

    The `LockingAsyncIterator` class ensures that iteration over the wrapped
    asynchronous iterator is thread-safe by using a provided lock.

    """
    def __init__(self, async_iterator, lock):
        """
        Initializes the iterator with the wrapped asynchronous iterator and lock.

        Parameters:
        async_iterator (async iterator): The wrapped asynchronous iterator.
        lock (RLock): The lock to be used for synchronization.
        """
        self._async_iterator = async_iterator
        self._lock = lock

    def __aiter__(self):
        """
        Returns the iterator itself.

        Returns:
        LockingAsyncIterator: The iterator itself.
        """
        return self

    async def __anext__(self):
        """
        Returns the next item from the iterator, acquiring the lock.

        Returns:
        any: The next item from the iterator.

        Raises:
        StopAsyncIteration: If the iterator is exhausted.
        """
        async with self._lock:
            return await self._async_iterator.__anext__()

class LockingPedanticObjMixin(RootMixin):
    """
    A mixin class that provides locking for Pydantic objects.

    The `LockingPedanticObjMixin` class ensures that access to the wrapped
    Pydantic object is thread-safe by using a provided lock.

    """
    def __init__(self, **kwargs):
        """
        Initializes the mixin with the Pydantic object.

        Parameters:
        **kwargs: Arbitrary keyword arguments, including 'obj' for the Pydantic object.
        """
        super().__init__(**kwargs)
        self._obj = kwargs.get('obj')
        validate_param(self._obj, 'obj')
        self._is_pedantic_obj = _is_pydantic_obj(self._obj)

class LockingGetItemMixin(RootMixin):
    """Mixin to provide thread-safe access and modification for collection-like objects.

    This mixin ensures that the `__getitem__` and `__setitem__` methods are thread-safe by using a lock.
    It is intended to be used with objects that support item access and modification, such as lists or dictionaries.

    Attributes:
        _obj: The object being proxied, which supports item access and modification.
        _lock: A threading lock to ensure thread-safe operations.
    """

    def __init__(self, **kwargs):
        """
        Initializes the mixin with the object and lock.

        Parameters:
        **kwargs: Arbitrary keyword arguments, including 'obj' for the object
                  and 'lock' for the lock.
        """
        super().__init__(**kwargs)

    def __getitem__(self, key):
        """Retrieve an item from the collection in a thread-safe manner.

        Parameters:
            key: The key or index of the item to retrieve.

        Returns:
            The item associated with the given key.
        """
        @functools.wraps(self._obj.__getitem__)
        def call(key):
            with self._lock:
                return self._obj[key]
        return call(key)

    def __setitem__(self, key, value):
        """Set an item in the collection in a thread-safe manner.

        Parameters:
            key: The key or index of the item to set.
            value: The value to associate with the given key.

        Returns:
            The value that was set.
        """
        @functools.wraps(self._obj.__setitem__)
        def call(key, value):
            with self._lock:
                self._obj[key] = value
            return value
        return call(key, value)


class LockingSetItemMixin(RootMixin):
    """Mixin to provide thread-safe modification of items in a collection.

    This mixin ensures that the `__setitem__` method is thread-safe by using a lock.
    It is intended to be used with objects that support item modification, such as lists or dictionaries.

    Attributes:
        _obj: The object being proxied, which supports item modification.
        _lock: A threading lock to ensure thread-safe modification.
    """

    def __init__(self, **kwargs):
        """
        Initializes the mixin with the object and lock.

        Parameters:
        **kwargs: Arbitrary keyword arguments, including 'obj' for the object
                  and 'lock' for the lock.
        """
        super().__init__(**kwargs)

    def __setitem__(self, key, value):
        """Set an item in the collection in a thread-safe manner.

        Parameters:
            key: The key or index of the item to set.
            value: The value to associate with the given key.

        Returns:
            The value that was set.
        """
        @functools.wraps(self._obj.__setitem__)
        def call(key, value):
            with self._lock:
                self._obj[key] = value
            return value
        return call(key, value)

class SyncContextManagerMixin:
    """
    Mixin to add synchronous context management to a class.
    """

    def __init__(self, **kwargs):
        """
        Initializes the mixin with the object and lock.

        Parameters:
        **kwargs: Arbitrary keyword arguments, including 'obj' for the object
                  and 'lock' for the lock.
        """
        super().__init__(**kwargs)
    def __enter__(self):
        self._lock.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._lock.release()

class AsyncContextManagerMixin:
    """
    Mixin to add asynchronous context management to a class.
    """

    def __init__(self, **kwargs):
        """
        Initializes the mixin with the object and lock.

        Parameters:
        **kwargs: Arbitrary keyword arguments, including 'obj' for the object
                  and 'lock' for the lock.
        """
        super().__init__(**kwargs)

    async def __aenter__(self):
        await self._lock.async_acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._lock.async_release()

class LockingAccessMixin(LockingPedanticObjMixin):
    """
    A mixin class that provides locking for attribute access.

    The `LockingAccessMixin` class ensures that access to the attributes of the
    wrapped object is thread-safe by using a provided lock.

    """
    def __init__(self, **kwargs):
        """
        Initializes the mixin with the object and lock.

        Parameters:
        **kwargs: Arbitrary keyword arguments, including 'obj' for the object
                  and 'lock' for the lock.
        """
        super().__init__(**kwargs)
        self._obj = kwargs.get('obj')
        validate_param(self._obj, 'obj')
        self._lock = kwargs.get('lock')
        validate_param(self._lock, 'lock')

    def __getattr__(self, name):
        """
        Returns the attribute, acquiring the lock if necessary.

        Parameters:
        name (str): The name of the attribute.

        Returns:
        any: The attribute value.
        """
        attr = getattr(self._obj, name)
        if inspect.isroutine(attr):
            if self._is_pedantic_obj and name == '_copy_and_set_values':
                # special case for Pydantic
                @functools.wraps(attr)
                def synchronized_method(*args, **kwargs):
                    with self._lock:
                        attr(*args, **kwargs)
                    return self
                return synchronized_method
            elif inspect.iscoroutinefunction(attr):
                @functools.wraps(attr)
                async def asynchronized_method(*args, **kwargs):
                    async with self._lock:
                        return await attr(*args, **kwargs)
                return asynchronized_method
            else:
                @functools.wraps(attr)
                def synchronized_method(*args, **kwargs):
                    with self._lock:
                        return attr(*args, **kwargs)
                return synchronized_method
        elif hasattr(attr, '__get__') or hasattr(attr, '__set__') or hasattr(attr, '__delete__'):
            # Handle property or descriptor
            if hasattr(attr, '__get__'):
                return attr.__get__(self._obj, type(self._obj))
            return attr
        else:
            return attr

class LockingCallableMixin(RootMixin):
    """
    A mixin class that provides locking for callable objects.

    The `LockingCallableMixin` class ensures that calls to the wrapped
    callable object are thread-safe by using a provided lock.

    """
    def __init__(self, **kwargs):
        """
        Initializes the mixin with the callable object and lock.

        Parameters:
        **kwargs: Arbitrary keyword arguments, including 'obj' for the callable object
                  and 'lock' for the lock.
        """
        super().__init__(**kwargs)
        self._obj = kwargs.get('obj')
        validate_param(self._obj, 'obj')
        self._lock = kwargs.get('lock')
        validate_param(self._lock, 'lock')

    def __call__(self, *args, **kwargs):
        """
        Calls the wrapped callable object, acquiring the lock.

        Parameters:
        *args: Positional arguments for the callable object.
        **kwargs: Keyword arguments for the callable object.

        """
        if inspect.iscoroutinefunction(self._obj):
            @functools.wraps(self._obj)
            async def acall(*args, **kwargs):
                async with self._lock:
                    return await self._obj(*args, **kwargs)
            return acall(*args, **kwargs)
        else:
            @functools.wraps(self._obj)
            def call(*args, **kwargs):
                with self._lock:
                    return self._obj(*args, **kwargs)
            return call(*args, **kwargs)

class LockingDefaultLockMixin(RootMixin):
    """
    A mixin class that provides a default lock if none is provided.

    The `LockingDefaultLockMixin` class ensures that a default lock is used
    if no lock is provided during initialization.

    """
    def __init__(self, **kwargs):
        """
        Initializes the mixin with the object and lock.

        Parameters:
        **kwargs: Arbitrary keyword arguments, including 'obj' for the object
                  and 'lock' for the lock.
        """
        lock = kwargs.get("lock", None)
        if not lock:
            lock = RLock()
        kwargs['lock'] = lock
        self._lock = lock
        super().__init__(**kwargs)

def _coerce_base_language_model(proxy):
    """
    Coerces the proxy object to be recognized as a BaseLanguageModel.

    Parameters:
    proxy (LockingProxy): The proxy object to be coerced.
    """
    if not _is_available_base_language_model:
        return
    if isinstance(proxy._obj, BaseLanguageModel):
        BaseLanguageModel.register(type(proxy))

class LockingBaseLanguageModelMixin(RootMixin):
    """
    A mixin class that provides locking for BaseLanguageModel objects.

    The `LockingBaseLanguageModelMixin` class ensures that access to the wrapped
    BaseLanguageModel object is thread-safe by using a provided lock.

    """
    def __init__(self, **kwargs):
        """
        Initializes the mixin with the BaseLanguageModel object.

        Parameters:
        **kwargs: Arbitrary keyword arguments, including 'obj' for the BaseLanguageModel object.
        """
        self._obj = kwargs.get('obj')
        validate_param(self._obj, 'obj')
        _coerce_base_language_model(self)
        super().__init__(**kwargs)

class LockingDefaultAndBaseLanguageModelMixin(LockingDefaultLockMixin, LockingBaseLanguageModelMixin):
    """
    A mixin class that combines default lock and BaseLanguageModel locking.

    The `LockingDefaultAndBaseLanguageModelMixin` class ensures that a default lock is used
    if no lock is provided and that access to the wrapped BaseLanguageModel object is thread-safe.

    """
    def __init__(self, **kwargs):
        """
        Initializes the mixin with the object and lock.

        Parameters:
        **kwargs: Arbitrary keyword arguments, including 'obj' for the object
                  and 'lock' for the lock.
        """
        super().__init__(**kwargs)


class LockingBaseLanguageModelMixin(RootMixin):
    """
    A mixin class that provides locking for BaseLanguageModel objects.

    The `LockingBaseLanguageModelMixin` class ensures that access to the wrapped
    BaseLanguageModel object is thread-safe by using a provided lock.

    """
    def __init__(self, **kwargs):
        """
        Initializes the mixin with the BaseLanguageModel object.

        Parameters:
        **kwargs: Arbitrary keyword arguments, including 'obj' for the BaseLanguageModel object.
        """
        self._obj = kwargs.get('obj')
        validate_param(self._obj, 'obj')
        _coerce_base_language_model(self)
        super().__init__(**kwargs)



# Flags to check the availability of Pydantic and BaseLanguageModel
try:
    from langchain_core.language_models import BaseLanguageModel

    _is_available_base_language_model = True
except ImportError:
    BaseLanguageModel = None
    _is_available_base_language_model = False

try:
    from pydantic import BaseModel

    _is_available_pydantic_v2 = True
except ImportError:
    _is_available_pydantic_v2 = False

try:
    from pydantic.v1 import BaseModel

    _is_available_pydantic_v1 = True
except ImportError:
    _is_available_pydantic_v1 = False


def _is_pydantic_v1_obj(obj):
    """
    Checks if the object is a Pydantic v1 object.

    Parameters:
    obj (any): The object to be checked.

    Returns:
    bool: True if the object is a Pydantic v1 object, False otherwise.
    """
    if not _is_available_pydantic_v1:
        return False
    ret = None
    try:
        from pydantic.v1 import BaseModel as BaseModelv1
        ret = isinstance(obj, BaseModelv1)
    except ImportError:
        ret = False
    return ret


def _is_pydantic_v2_obj(obj):
    """
    Checks if the object is a Pydantic v2 object.

    Parameters:
    obj (any): The object to be checked.

    Returns:
    bool: True if the object is a Pydantic v2 object, False otherwise.
    """
    if not _is_available_pydantic_v2:
        return False
    ret = None
    try:
        from pydantic import BaseModel as BaseModelv2
        ret = isinstance(obj, BaseModelv2)
    except ImportError:
        ret = False
    return ret

def _is_pydantic_obj(obj):
    """
    Checks if the given object is an instance of either Pydantic v1 or v2 models.


    Args:
        obj (Any): The object to be checked.

    Returns:
        bool: True if the object is an instance of either Pydantic v1 or v2 models, False otherwise.
    """

    ret = _is_pydantic_v1_obj(obj) or _is_pydantic_v2_obj(obj)
    return ret

class LockingProxy(LockingDefaultAndBaseLanguageModelMixin,
                   LockingIterableMixin,
                   LockingAsyncIterableMixin,
                   LockingAccessMixin,
                   LockingCallableMixin,
                   LockingGetItemMixin,
                   LockingSetItemMixin,
                   SyncContextManagerMixin,
                   AsyncContextManagerMixin):
    """
    A proxy class that combines multiple locking mixins.

    The `LockingProxy` class ensures that access to the wrapped object is thread-safe
    by using a provided lock. It supports iterable, async iterable, attribute access,
    and callable objects, and thread-safe item access and modification
    and context management, async context management.

    See https://alex-ber.medium.com/7a7a14021427 for more details.

    """
    def __init__(self, **kwargs):
        """
        Initializes the proxy with the object and lock.

        Parameters:
        **kwargs: Arbitrary keyword arguments, including 'obj' for the object
                  and 'lock' for the lock.
        """
        super().__init__(**kwargs)


def is_running_in_main_thread():
    """
    Checks if the current thread is the main thread.

    Returns:
        bool: True if the current thread is the main thread, False otherwise.
    """
    logger.info("is_running_in_main_thread()")

    ret = threading.current_thread() is threading.main_thread()
    logger.info(f"Going to return {ret}")
    return ret


def _execute_async_in_sync(afunc_call):
    """
    Executes an asynchronous function call in a synchronous context.

    Args:
        afunc_call: The asynchronous function call to be executed.

    Returns:
        The result of the asynchronous function call.

    Raises:
        RuntimeError: If the function is called from the main thread while an event loop is running.
    """
    logger.info("_execute_async_in_sync()")

    has_running_loop = False

    try:
        loop = asyncio.get_running_loop()
        has_running_loop = True
    except RuntimeError:
        logger.info("Resetting EVENT_LOOP")
        loop = _EVENT_LOOP
        asyncio.set_event_loop(loop)

    if has_running_loop:
        logger.info('The event loop is running.')
        if is_running_in_main_thread():
            s = """
            If we have a running event loop, we should be on a non-MainThread; otherwise, we will block the event loop. 
            The easiest way to achieve this is to use asyncio.to_thread() before making the call. 
            In any case, you should execute your synchronous function on a separate thread, so any blocking will occur 
            on that thread and not on the main thread that runs the event loop.			
            """

            raise RuntimeError(s)

        logger.info("But we're running on a non-MainThread, so we're good.")
        logger.info("Going to submit a coroutine to a given event loop from a different thread and execute it in a thread-safe way.")
        logger.info("Going to block current thread and wait for result")

        future = concurrent.futures.Future()

        # Define a callback to set the result of the concurrent.futures.Future
        def on_complete(task):
            if task.exception():
                future.set_exception(task.exception())
            else:
                future.set_result(task.result())

        # Schedule the coroutine and add the callback
        task = asyncio.run_coroutine_threadsafe(afunc_call(), loop)
        task.add_done_callback(lambda t: on_complete(t))
        result = future.result()

    else:
        logger.info("The event loop is NOT running.")
        logger.info("Submitting a coroutine to the event loop from a different thread in a thread-safe manner.")
        logger.info("This will start the event loop.")
        logger.info("The current thread will continue to run.")

        result = asyncio.run_coroutine_threadsafe(afunc_call(), loop).result()

    return result

def lift_to_async(afunc, /, *args, **kwargs):
    """
    Executes an asynchronous function in a synchronous context preserving ContextVar's context.

    Args:
        afunc: The asynchronous function to be executed.
        *args: Positional arguments to pass to the function.
        **kwargs: Keyword arguments to pass to the function.

    Returns:
        The result of the asynchronous function call.
    """
    logger.info("lift_to_async()")

    #see https://github.com/alex-ber/AlexBerUtils/issues/14
    def wrapper():
        try:
            return afunc(*args, **kwargs)
        except StopAsyncIteration as exc:
            # StopIteration can't be set on an asyncio.Future
            # it raises a TypeError and leaves the Future pending forever
            # so we need to convert it to a RuntimeError
            raise RuntimeError("Async generator exhausted unexpectedly") from exc

    ctx = contextvars.copy_context()
    afunc_call = functools.partial(ctx.run, wrapper)
    result = _execute_async_in_sync(afunc_call)
    return result


def ensure_thread_event_loop():
    """
    Initializes an event loop for the current thread if it does not already exist.

    This function first checks if the current thread has an event loop stored in thread-local storage.
    If not, it attempts to retrieve the current event loop. If no event loop is present, it creates a new one
    and sets it as the current event loop for the thread. The event loop is then also stored in thread-local storage.
    """
    # Check if the current thread already has an event loop in thread-local storage
    if not hasattr(_event_loops_thread_locals, 'loop'):
        try:
            # Try to get the current event loop
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # If no event loop is present, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Store the event loop in thread-local storage
        _event_loops_thread_locals.loop = loop

def _run_coroutine_in_thread(coro):
    """
    Runs a coroutine in the event loop of the current thread.

    This function ensures that the current thread has an event loop initialized. It then runs the given coroutine
    until it is complete using the thread's event loop.

    Args:
        coro: The coroutine to be executed.

    Returns:
        The result of the coroutine execution.
    """
    # Ensure the thread has an event loop
    ensure_thread_event_loop()
    loop = _event_loops_thread_locals.loop
    return loop.run_until_complete(coro)


def exec_in_executor(executor: Optional[Executor], func: Callable[..., T], *args, **kwargs) -> asyncio.Future:
    """
    Execute a function or coroutine within a given executor while preserving `ContextVars`, ensuring that context is maintained across asynchronous boundaries.


    The executor is resolved in the following order:
    1. If the `executor` parameter is provided, it is used.
    2. If an executor was passed via `initConfig()`, it is used.
    3. If neither is set, `None` is used, which means the default asyncio executor will be used.

    Note: as a side fact, threads in the executor may have an event loop attached. This allows for the execution of asynchronous tasks within those threads.

    Args:
        executor (Optional[Executor]): The executor to run the function or coroutine. If None, the default asyncio executor is used.
        func (Callable[..., T]): The function or coroutine to execute.
        *args: Positional arguments to pass to the function or coroutine.
        **kwargs: Keyword arguments to pass to the function or coroutine.

    Returns:
        asyncio.Future: A future representing the execution of the function or coroutine.
    """
    loop = asyncio.get_running_loop()
    resolved_executor = executor if executor is not None else _GLOBAL_EXECUTOR

    # Copy the current context
    ctx = copy_context()

    if asyncio.iscoroutinefunction(func):
        # Wrap the coroutine function to handle exceptions, including StopIteration
        async def _coro_wrapper():
            try:
                return await func(*args, **kwargs)
            except Exception as exc:
                logging.error(f"Exception occurred in coroutine | Error: {str(exc)}", exc_info=True)
                # Re-raise the exception to propagate it
                raise exc

        # Create the coroutine in the original context
        coro = _coro_wrapper()
        # run it in the same context in an executor guarded against StopIteration
        return loop.run_in_executor(resolved_executor,
                                    lambda: ctx.run(_run_coroutine_in_thread, coro))
    else:

        @functools.wraps(func)
        def wrapper() -> T:
            ensure_thread_event_loop()
            try:
                return func(*args, **kwargs)
            except StopIteration as exc:
                # StopIteration can't be set on an asyncio.Future
                # it raises a TypeError and leaves the Future pending forever
                # so we need to convert it to a RuntimeError
                raise RuntimeError from exc

        # run it in the same context in an executor guarded against StopIteration
        return loop.run_in_executor(resolved_executor, lambda: ctx.run(wrapper))

def exec_in_executor_threading_future(executor: Optional[Executor], func: Callable[..., T], *args, **kwargs) -> Future:
    """
    Execute a function or coroutine within a given executor and return a threading.Future.

    This function executes a function or coroutine while preserving `ContextVars`, ensuring that context is maintained across asynchronous boundaries. It provides a threading.Future to handle the result or exception of the task execution.

    The executor is resolved in the following order:
    1. If the `executor` parameter is provided, it is used.
    2. If an executor was passed via `initConfig()`, it is used.
    3. If neither is set, `None` is used, which means the default asyncio executor will be used.

    Note: as a side fact, threads in the executor may have an event loop attached. This allows for the execution of asynchronous tasks within those threads.

    Args:
        executor (Optional[Executor]): The executor to run the function or coroutine. If None, the default asyncio executor is used.
        func (Callable[..., T]): The function or coroutine to execute.
        *args: Positional arguments to pass to the function or coroutine.
        **kwargs: Keyword arguments to pass to the function or coroutine.

    Returns:
        threading.Future: A future representing the execution of the function or coroutine.
    """

    future = concurrent.futures.Future()

    if asyncio.iscoroutinefunction(func):
        @functools.wraps(func)
        async def wrapper(fut):
            coro = func(*args, **kwargs)
            result = await coro
            fut.set_result(result)
    else:
        @functools.wraps(func)
        def wrapper(fut):
            result = func(*args, **kwargs)
            fut.set_result(result)

    exec_in_executor(executor, wrapper, future)
    return future


def chain_future_results(source_future: FutureType, target_future: FutureType):
    """
    Safely propagates the outcome from a source future to a target future.

    This function is called when the source_future is completed. It retrieves the result or exception
    from the source_future and sets it on the target_future, ensuring that the outcome of the task execution
    is properly propagated. This function is generic and can be used with any types of futures.

    To use this function, add it as a callback to the source_future:

    Typically, this function is added as a callback to `source_future`:

        source_future.add_done_callback(lambda fut: chain_future_results(fut, target_future))

    Args:
        source_future: The future from which to retrieve the result or exception.
        target_future: The future on which to set the result or exception.
    """

    def chain_future_results(source_future: FutureType, target_future: FutureType):
        if target_future.done():
            return  # Already resolved by another callback

        try:
            result = source_future.result()
            if not target_future.done():
                target_future.set_result(result)
        except Exception as e:
            if not target_future.done():
                target_future.set_exception(e)

def get_main_event_loop():
    """
    Returns the event loop that was set via initConf(). This function should be called from the MainThread
    during the application startup. If such a call was not made, None will be returned.

    Returns:
        asyncio.AbstractEventLoop or None: The main event loop if set, otherwise None.
    """
    return _EVENT_LOOP

class AsyncExecutionQueue(RootMixin):
    """
    A class representing an asynchronous task queue that manages task execution using a specified executor.

    This class provides a context manager interface to start and stop a worker that processes tasks from the queue.
    Tasks are executed asynchronously, and the queue can be closed gracefully.

    The executor is resolved in the following order:
    1. If the `executor` parameter is provided, it is used.
    2. If an executor was passed via `initConfig()`, it is used.
    3. If neither is set, `None` is used, which means the default asyncio executor will be used.

    Note: as a side fact, threads in the executor may have an event loop attached. This allows for the execution of asynchronous tasks within those threads.


    Attributes:
        queue (asyncio.Queue): The queue that holds tasks to be executed.
        executor (Executor): The executor to run tasks.

    Methods:
        worker(): Continuously processes tasks from the queue until the `aclose()` method is called.
        aadd_task(func, *args, **kwargs): Asynchronously adds a task to the queue for execution and returns a future.
        aclose(): Asynchronously closes the queue and waits for the worker to finish processing.
    """

    def __init__(self, **kwargs):
        """
        Initializes the TaskQueue with a specified queue and executor.

        Args:
            **kwargs: Optional keyword arguments to configure the queue and executor.
                - queue (asyncio.Queue, optional): A custom queue to use. If not provided, a new asyncio.Queue is created.
                - executor (Executor): The executor to run tasks. This parameter is required.

        Execute a function or coroutine within a given executor while preserving `ContextVars`, ensuring that context is maintained across asynchronous boundaries.
        """
        self.queue = kwargs.pop("queue", None)
        if not self.queue:
            self.queue = asyncio.Queue()
        #if None, default asyncio ThreadPoolExecutor will be used.
        self.executor = kwargs.pop("executor", None)
        self._worker_task = None
        super().__init__(**kwargs)

    async def __aenter__(self):
        """
        Starts the worker when entering the context.
        """
        self._worker_task = asyncio.create_task(self.worker())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Closes the queue and stops the worker when exiting the context.
        """
        await self.aclose()

    async def worker(self):
        """
        Continuously processes tasks from the queue until the `aclose()` method is called.

        This method continuously fetches tasks from the queue and executes them asynchronously using the specified executor.
        Execute a function or coroutine within a given executor while preserving `ContextVars`, ensuring that context is maintained across asynchronous boundaries.
        """
        while True:
            task, task_future = await self.queue.get()
            try:
                if task is _CLOSE_SENTINEL:
                    return  # Exit the worker loop
                func, args, kwargs = task
                result_future = exec_in_executor(self.executor, func, *args, **kwargs)
                result_future.add_done_callback(lambda fut: chain_future_results(fut, task_future))
            finally:
                # Mark the task as done, regardless of what the task was
                self.queue.task_done()


    async def aadd_task(self, func, /, *args, **kwargs):
        """
        Asynchronously adds a task to the queue for execution and returns a future.

        Args:
            func (Callable): The function to be executed, which can be synchronous or asynchronous.
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Execute a function or coroutine within a given executor while preserving `ContextVars`, ensuring that context is maintained across asynchronous boundaries.

        Returns:
            asyncio.Future: A future representing the execution of the function or coroutine.
        """
        future = asyncio.get_running_loop().create_future()
        await self.queue.put(((func, args, kwargs), future))
        return future

    def add_task(self, executor, func, /, *args, **kwargs):
        """
        Adds a task to the queue for asynchronous execution and returns a future.

        The executor is resolved in the following order:
        1. If the `executor` parameter is provided, it is used.
        2. If an executor was passed via `initConfig()`, it is used.
        3. If neither is set, `None` is used, which means the default asyncio executor will be used.


        Args:
            executor (Executor): The executor to run the asynchronous task.
            func (Callable[..., Any]): The function to be executed, which can be synchronous or asynchronous.
            *args (Any): Positional arguments to pass to the function.
            **kwargs (Any): Keyword arguments to pass to the function.

        Execute a function or coroutine within a given executor while preserving `ContextVars`, ensuring that context is maintained across asynchronous boundaries.

        Returns:
            threading.Future: A future representing the execution of the function or coroutine.
        """
        fut = exec_in_executor_threading_future(executor, self.aadd_task, func, *args, **kwargs)
        return fut


    async def aclose(self):
        """
        Asynchronously closes the queue and waits for the worker to finish processing.

        This method signals the worker to stop processing tasks and waits for the worker task to complete.
        """
        await self.queue.put((_CLOSE_SENTINEL, None))
        if self._worker_task:
            await self._worker_task





def get_context_vars(*modules, factory_method_creator = None) -> List:
    """Collects top-level ContextVar instances from modules and associates them with factory methods.

    Args:
        *modules: Modules to search for ContextVar instances.
        factory_method_creator: Optional function to resolve the factory callable for a ContextVar.
            Signature: `(var: ContextVar, module: ModuleType) -> Callable`.
            Default: Looks for a function named `<var.name>_DEFAULT` in the same module as the ContextVar.

    Returns:
        List of entities containing:
        - 'var': The ContextVar instance
        - 'factory': Callable factory method to produce the default value

    Example:
        # Default usage
        entities = get_context_vars(my_module)

        # Custom factory resolver (e.g., factory in another module)
        def custom_creator(var, module):
            from other_module import factories
            return getattr(factories, f"{var.name}_default")

        entities = get_context_vars(my_module, factory_method_creator=custom_creator)
    """
    if not modules:
        return []

    # Set default factory resolver if none provided
    if not factory_method_creator:
        factory_method_creator = lambda var, module: getattr(module, f"{var.name}_DEFAULT")

    all_entities = []
    for module in modules:
        # List all attributes of the module
        attributes = dir(module)

        # Find all ContextVars in the module
        ctx_vars = [getattr(module, attr) for attr in attributes
                    if isinstance(getattr(module, attr), ContextVar)]

        # Build entities with resolved factory methods
        entities = [
            {
                "var": var,
                "factory": factory_method_creator(var, module),
            }
            for var in ctx_vars
        ]
        all_entities.extend(entities)

    reset_context_vars(*all_entities)
    return all_entities


def reset_context_vars(*entities) -> None:
    """Resets ContextVars to their default values using associated factory methods.

    Args:
        *entities: Entities produced by `get_context_vars`, each containing:
            - 'var': ContextVar to reset
            - 'factory': Factory method to generate its default value

    Raises:
        ValueError: If the factory is not callable.
    """
    for entity in entities:
        var = entity["var"]
        factory = entity["factory"]

        if not callable(factory):
            raise ValueError(f"Factory for ContextVar {var.name} is not callable: {factory}")

        default_value = factory()
        var.set(default_value)


def initConfig(**kwargs):
    """
    Initializes the configuration required for using the lift_to_async(), exec_in_executor() and get_event_loop() methods.

    This function is intended to be called from the MainThread.
    It can be called with empty parameters.
    It should be called with running event loop.

    Args:
        **kwargs: Optional keyword arguments to configure the initialization.

    Returns:
        None
    """
    _loop = asyncio.get_running_loop()  #raises exception, if there is no running event loop
    global _EVENT_LOOP
    _EVENT_LOOP = _loop

    global _GLOBAL_EXECUTOR
    # Set the global executor if provided
    _GLOBAL_EXECUTOR = kwargs.get('executor', None)

