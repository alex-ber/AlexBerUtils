from __future__ import annotations

import asyncio
import concurrent.futures
import contextlib
import contextvars
import functools
import inspect
import logging
import threading
from collections import deque
from concurrent.futures import Executor, Future
from contextvars import ContextVar, copy_context
from threading import local
from typing import Any, Callable, List, Optional, TypeAlias, TypeVar, Awaitable

from alexber.utils.warning import deprecated


# Define type variables for the function signature
T = TypeVar('T')

FutureType: TypeAlias = (
    asyncio.Future[T]
    | concurrent.futures.Future[T]
)

AwaitableSource: TypeAlias = (
    Awaitable[T]
    | concurrent.futures.Future[T]
)

_CANCELLED_ERRORS = (
    asyncio.CancelledError,
    concurrent.futures.CancelledError,
)

_INVALID_STATE_ERRORS = (
    asyncio.InvalidStateError,
    concurrent.futures.InvalidStateError,
)

_STOP_ITERATION_ERRORS = (
    StopIteration,
    StopAsyncIteration,
)

logger = logging.getLogger(__name__)


# Should be initialized via initConfig() method, see below.
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

# _CLOSE_SENTINEL is retained for backward compatibility; worker shutdown is now coordinated
# via queue.join() and task cancellation in AsyncExecutionQueue.aclose().
_CLOSE_SENTINEL = object()

def threadlocal_var(thread_locals, varname, factory, *args, **kwargs):
    v = getattr(thread_locals, varname, None)
    if v is None:
        v = factory(*args, **kwargs)
        setattr(thread_locals, varname, v)
    return v

def get_threadlocal_var(thread_locals, varname):
    v = threadlocal_var(thread_locals, varname, lambda: None)
    if v is None:
        raise ValueError(f"threadlocal's {varname} is not initialized")
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
    A reentrant lock supporting independent synchronous and asynchronous locking.

    Synchronous and asynchronous operations use separate locking mechanisms,
    each providing reentrancy and fair policy (FIFO ordering) within its own domain.

    The synchronous lock is owned by a thread, while the asynchronous lock
    is owned by an asyncio.Task.

    Important:
        The synchronous and asynchronous locks are independent by design.
        Acquiring one does not prevent acquisition of the other.
        Mutual exclusion is guaranteed only within the same locking domain,
        not between synchronous and asynchronous operations.

        The asynchronous locking mechanism is intended for use within
        a single event loop and is not thread-safe.

    See https://alex-ber.medium.com/a6b9a9021be8 for more details.

    """

    def __init__(self):
        """
        Initialize the RLock instance with independent synchronous and asynchronous locking state.
        """
        self._sync_lock = threading.RLock()  # Synchronous reentrant lock

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

            try:
                while (
                        self._async_owner is not None
                        or self._async_waiting[0] != current_task
                ):
                    await self._async_condition.wait()
            except asyncio.CancelledError:
                self._async_waiting.remove(current_task)
                self._async_condition.notify_all()
                raise

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
        return LockingAsyncIterator(aiter(self._obj), self._lock)


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
            return await anext(self._async_iterator)

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
    """Mixin to provide thread-safe access for collection-like objects.

    This mixin ensures that the `__getitem__` method is thread-safe by using a lock.
    It is intended to be used with objects that support item access, such as lists or dictionaries.

    Attributes:
        _obj: The object being proxied, which supports item access.
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
        await self._lock.async_release()

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
        with self._lock:
            attr = getattr(self._obj, name)
            if inspect.isroutine(attr):
                if self._is_pedantic_obj and name == '_copy_and_set_values':
                    # Special case for Pydantic
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
        lock = kwargs.get("lock")
        if lock is None:
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


def ensure_thread_event_loop():
    """
    Initializes an event loop for the current thread if it does not already exist.

    This function first checks if the current thread has an event loop stored in thread-local storage.
    If not, it attempts to retrieve the current event loop. If no event loop is present, it creates a new one
    and sets it as the current event loop for the thread. The event loop is then also stored in thread-local storage.
    """
    loop = getattr(_event_loops_thread_locals, 'loop', None)
    if loop is None or loop.is_closed():
        try:
            # Try to get the currently running event loop in this thread
            loop = asyncio.get_running_loop()
            _event_loops_thread_locals.is_dedicated_worker_loop = False
        except RuntimeError:
            # If no running event loop is present in this thread, create a new dedicated one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            _event_loops_thread_locals.is_dedicated_worker_loop = True

        # Store the event loop in thread-local storage
        _event_loops_thread_locals.loop = loop
    else:
        # Ensure the thread's current event loop points to its dedicated loop
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.set_event_loop(loop)


def _is_dedicated_worker_loop(loop: asyncio.AbstractEventLoop) -> bool:
    """
    Checks whether `loop` is a private worker event loop created for the current thread
    rather than the main application event loop.
    """
    return  getattr(_event_loops_thread_locals, 'loop', None) is loop \
        and getattr(_event_loops_thread_locals, 'is_dedicated_worker_loop', True) \
        and loop is not _EVENT_LOOP



def _execute_async_in_sync(afunc_call):
    """
    Executes an asynchronous function call in a synchronous context.

    Args:
        afunc_call: The asynchronous function call to be executed.

    Returns:
        The result of the asynchronous function call.

    Raises:
        RuntimeError: If the function is called from the thread of the target event loop,
                      or if no target event loop is available.
    """
    logger.info("_execute_async_in_sync()")
    loop, is_current_thread_loop = _resolve_active_loop()

    if is_current_thread_loop:
        # If called from inside a dedicated worker loop, we cannot block the worker loop
        # waiting on itself, so fall back to _EVENT_LOOP if available.
        if (
            _is_dedicated_worker_loop(loop)
            and _EVENT_LOOP is not None
            and not _EVENT_LOOP.is_closed()
            and _EVENT_LOOP.is_running()
        ):
            loop = _EVENT_LOOP
        else:
            raise RuntimeError(
                "Cannot synchronously wait for a coroutine "
                "from its own event loop thread."
            )

    logger.info("The event loop is NOT running in the current thread.")
    logger.info("Submitting a coroutine to _EVENT_LOOP from a different thread in a thread-safe manner.")
    logger.info("The current thread will block waiting for the result.")

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

    # See https://github.com/alex-ber/AlexBerUtils/issues/14
    def wrapper():
        try:
            return afunc(*args, **kwargs)
        except _STOP_ITERATION_ERRORS as exc:
            # StopIteration / StopAsyncIteration can't be set on an asyncio.Future
            # directly without risking TypeError or leaving the Future pending forever,
            # so we convert it to a RuntimeError.
            raise RuntimeError("Async callable or generator exhausted unexpectedly") from exc

    ctx = contextvars.copy_context()
    afunc_call = functools.partial(ctx.run, wrapper)
    result = _execute_async_in_sync(afunc_call)
    return result


class FutureWrapper:
    """
    A proxy for an asyncio.Future that intercepts consumption.
    """
    def __init__(self, fut: asyncio.Future):
        self._fut = fut
        self._consumed = False  # Set to True if the user awaits or calls result()/exception()

    def __await__(self):
        self._consumed = True
        return self._fut.__await__()

    def result(self):
        try:
            return self._fut.result()
        finally:
            if self._fut.done():
                self._consumed = True

    def exception(self):
        try:
            return self._fut.exception()
        finally:
            if self._fut.done():
                self._consumed = True

    def add_done_callback(
            self,
            callback: Callable[[Any], Any],
            *,
            context: contextvars.Context | None = None,
    ) -> None:
        self._fut.add_done_callback(callback, context=context)

    def done(self):
        return self._fut.done()

    # Proxy any other attribute access to the underlying future.
    def __getattr__(self, name):
        return getattr(self._fut, name)

    # Optionally, you might implement __repr__ for debugging.
    def __repr__(self):
        return f"<FutureWrapper consumed={self._consumed} wrapping: {self._fut!r}>"


def check_and_log_exception(wrapper: FutureWrapper):
    """
    Check a wrapped future for unconsumed exceptions and log them if present.

    This function inspects the underlying future (accessed via the `wrapper`) without marking
    it as consumed. If the future is complete but its result has not been retrieved (i.e., not
    consumed), the function attempts to obtain any exception that may have occurred. If an
    exception is found, it is logged to help identify errors in tasks whose results were never
    explicitly handled.

    Args:
        wrapper: An instance of FutureWrapper that encapsulates an asyncio Future.
    """
    # Note: We check the underlying future directly to avoid accidentally marking it as consumed.
    wrapper, _ = _unwrap_future(wrapper, is_mark_consumed=False)
    if not wrapper._consumed and wrapper._fut.done():
        if wrapper._fut.cancelled():
            return
        try:
            exc = wrapper._fut.exception()
        except Exception as e:
            logger.warning("Unexpected failure in retrieving exception from future: %s", e, exc_info=True)
            return
        if exc is not None:
            logger.exception("Unhandled exception in fire-and-forget task", exc_info=exc)


def handle_future_exception(
    future: asyncio.Future | FutureWrapper,
    delay: float = 0.1,
) -> None:
    """
    Schedule logging of an unconsumed exception from an asyncio Future.

    The exception check is scheduled after the future completes,
    with an additional configurable delay to allow the consumer
    time to retrieve the result or exception.

    Nested FutureWrappers are unwrapped to locate the underlying
    asyncio Future, while preserving the innermost wrapper for
    consumption tracking.

    The callback is always registered on the future's owning
    event loop, including when called from another thread.

    Cancelled futures are ignored.

    Note:
        Consumption tracking is reliable only when the caller uses
        the monitored FutureWrapper. If a raw asyncio.Future is
        supplied, direct consumption cannot be detected.

    Args:
        future: The asyncio Future or FutureWrapper to monitor.
        delay: Seconds to wait after completion before checking
            for an unconsumed exception. Defaults to 0.1.
    """
    source_wrapper, raw_fut = _unwrap_future(future, is_mark_consumed=False)
    loop = raw_fut.get_loop()

    if loop.is_closed():
        return

    def _on_done(_):
        loop.call_later(delay, check_and_log_exception, source_wrapper)

    def _register():
        raw_fut.add_done_callback(_on_done)

    try:
        running_loop, is_current_thread_loop = _resolve_active_loop()
    except RuntimeError:
        running_loop, is_current_thread_loop = None, False

    if is_current_thread_loop and running_loop is loop:
        _register()
    else:
        try:
            loop.call_soon_threadsafe(_register)
        except RuntimeError:
            # Event loop closed concurrently.
            pass


async def _await_source(source: Awaitable[T]) -> T:
    """
    Await a source object and return its result.
    """
    return await source


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



def _unwrap_future(
    future: asyncio.Future | FutureWrapper,
    *,
    is_mark_consumed: bool = True,
) -> tuple[FutureWrapper, asyncio.Future]:
    """
    Unwrap nested FutureWrapper instances to obtain the underlying asyncio.Future.

    If no wrapper exists, create one around the original future.

    Args:
        future: An asyncio.Future or a potentially nested FutureWrapper.
        is_mark_consumed: Whether to mark all encountered wrappers as consumed.

    Returns:
        A tuple containing the innermost FutureWrapper and the underlying
        asyncio.Future.
    """
    wrapper: FutureWrapper | None = None
    raw_fut = future

    while isinstance(raw_fut, FutureWrapper):
        wrapper = raw_fut

        if is_mark_consumed:
            wrapper._consumed = True

        raw_fut = raw_fut._fut

    if wrapper is None:
        wrapper = FutureWrapper(raw_fut)

    return wrapper, raw_fut


def _resolve_returned_awaitable_in_thread(value: Any) -> Any:
    """
    Unwraps an Awaitable or Future returned by a callable running inside a worker thread.

    If `value` is an `asyncio.Future` (or `FutureWrapper`) bound to a different event loop,
    it is safely bridged via `resolve_awaitable` into a `concurrent.futures.Future` to avoid
    cross-loop RuntimeError. Otherwise, it is awaited on the worker thread's event loop.
    """
    while isinstance(value, (Awaitable, concurrent.futures.Future, FutureWrapper)):
        if isinstance(value, FutureWrapper):
            _, value = _unwrap_future(value, is_mark_consumed=True)
        if isinstance(value, concurrent.futures.Future):
            value = value.result()
        elif isinstance(value, asyncio.Future):
            ensure_thread_event_loop()
            thread_loop = _event_loops_thread_locals.loop
            if value.get_loop() is thread_loop:
                value = _run_coroutine_in_thread(_await_source(value))
            else:
                sync_fut: concurrent.futures.Future = concurrent.futures.Future()
                resolve_awaitable(value, sync_fut, loop=value.get_loop())
                value = sync_fut.result()
        else:
            value = _run_coroutine_in_thread(_await_source(value))

    return value


def _prepare_executor_callable(
    ctx: contextvars.Context,
    func: Callable[..., T],
    *args,
    **kwargs,
) -> Callable[[], T]:
    """
    Prepares a callable that executes `func` (sync or async) inside `ctx`
    within a worker thread, unwrapping any returned Awaitable and converting
    `StopIteration` / `StopAsyncIteration` to `RuntimeError`.
    """
    if asyncio.iscoroutinefunction(func):
        async def _coro_wrapper():
            try:
                return await func(*args, **kwargs)
            except _STOP_ITERATION_ERRORS as exc:
                # StopIteration / StopAsyncIteration can't be set on an asyncio.Future
                # It raises a TypeError and leaves the Future pending forever
                raise RuntimeError from exc
            except Exception:
                # Re-raise any other exceptions to propagate them properly
                raise

        def run_async_in_thread() -> T:
            # Create the coroutine right before running it in the worker thread to avoid
            # 'RuntimeWarning: coroutine was never awaited' if the executor rejects the task.
            coro = _coro_wrapper()
            try:
                res = _run_coroutine_in_thread(coro)
                if isinstance(res, (Awaitable, concurrent.futures.Future)):
                    res = _resolve_returned_awaitable_in_thread(res)
                return res
            except _STOP_ITERATION_ERRORS as exc:
                raise RuntimeError from exc

        return lambda: ctx.run(run_async_in_thread)
    else:
        @functools.wraps(func)
        def wrapper() -> T:
            ensure_thread_event_loop()
            try:
                res = func(*args, **kwargs)
                if isinstance(res, (Awaitable, concurrent.futures.Future)):
                    res = _resolve_returned_awaitable_in_thread(res)
                return res
            except _STOP_ITERATION_ERRORS as exc:
                # StopIteration / StopAsyncIteration can't be set on an asyncio.Future
                # it raises a TypeError and leaves the Future pending forever
                # so we need to convert it to a RuntimeError
                raise RuntimeError from exc
            except Exception:
                # Re-raise any other exceptions to propagate them properly
                raise

        return lambda: ctx.run(wrapper)



def exec_in_executor(
    executor: Optional[Executor],
    func: Callable[..., T],
    *args,
    **kwargs,
) -> FutureWrapper:
    """
    Execute a function or coroutine in an executor while preserving ContextVars.

    The executor is resolved in the following order:
    1. The explicitly provided executor.
    2. The executor configured via initConfig().
    3. The default asyncio executor.

    The event loop is resolved in the following order:
    1. The currently running event loop in the current thread.
    2. The main event loop configured via initConfig().

    If called from another thread, submission is dispatched to the
    target event loop in a thread-safe manner. The call blocks only
    until the task has been submitted, not until it completes.

    The returned FutureWrapper tracks explicit consumption via
    await, result(), or exception(). Exceptions from unconsumed
    futures are logged automatically after a short delay.

    Note:
        The returned wrapper remains bound to the target event loop.
        It cannot be awaited from a different event loop while pending.

    Args:
        executor: Optional executor. Defaults to the configured
            executor or the default asyncio executor.
        func: Function or coroutine function to execute.
        *args: Positional arguments for func.
        **kwargs: Keyword arguments for func.

    Returns:
        asyncio.Future-proxy: An awaitable proxy representing the
        submitted execution.
    """
    loop, is_current_thread_loop = _resolve_active_loop()
    resolved_executor = executor if executor is not None else _GLOBAL_EXECUTOR

    ctx = copy_context()
    callable_task = _prepare_executor_callable(
        ctx, func, *args, **kwargs
    )

    def _submit() -> FutureWrapper:
        fut = loop.run_in_executor(resolved_executor, callable_task)
        wrapper = FutureWrapper(fut)

        handle_future_exception(wrapper)

        return wrapper

    if is_current_thread_loop:
        return _submit()

    async def _schedule_on_loop():
        return _submit()

    concurrent_fut = asyncio.run_coroutine_threadsafe(
        _schedule_on_loop(), loop
    )

    return concurrent_fut.result()


def exec_in_executor_threading_future(executor: Optional[Executor], func: Callable[..., T], *args, **kwargs) -> Future:
    """
    Execute a function or coroutine within a given executor and return a concurrent.futures.Future.

    This function executes a function or coroutine while preserving `ContextVars`, ensuring that context is maintained across asynchronous boundaries. It provides a concurrent.futures.Future to handle the result or exception of the task execution.

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
        concurrent.futures.Future: A future representing the execution of the function or coroutine.
    """
    future = concurrent.futures.Future()
    ctx = copy_context()
    callable_task = _prepare_executor_callable(ctx, func, *args, **kwargs)

    def _worker_task() -> None:
        if not future.set_running_or_notify_cancel():
            return
        try:
            res = callable_task()
        except _CANCELLED_ERRORS:
            future.cancel()
        except Exception as exc:
            future.set_exception(exc)
        else:
            future.set_result(res)

    exec_in_executor(executor, _worker_task)
    return future



@deprecated(version='1.0.0', reason="Use resolve_awaitable() instead.", for_removal=False)
def chain_future_results(
    source_future: FutureType[T],
    target_future: FutureType[T],
) -> None:
    """
    Propagate the outcome of a Future to another Future.

    This function is retained for backward compatibility. It delegates
    to resolve_awaitable(), which also supports arbitrary awaitable sources.
    The source result, exception, or cancellation is propagated to
    target_future. asyncio.Future instances owned by different event loops
    are supported, provided the relevant loops remain operational.

    Args:
        source_future:
            The source Future.
        target_future:
            The Future that receives the source outcome.
    """
    resolve_awaitable(source_future, target_future)


def resolve_awaitable(
    source: AwaitableSource[T],
    target_future: FutureType[T],
    *,
    loop: Optional[asyncio.AbstractEventLoop] = None
) -> None:
    """
    Resolve an awaitable source and propagate its outcome to a target Future.

    Supported sources include asyncio.Future, asyncio.Task, FutureWrapper,
    concurrent.futures.Future, coroutine objects, and other awaitables.
    Existing Future objects are chained directly. Other awaitables are
    scheduled in the selected event loop and their outcomes are propagated
    to target_future.

    Source cancellation propagates as target cancellation. Ordinary
    exceptions and explicitly handled cancellation exceptions are propagated
    to the target. Other BaseException subclasses are not caught.
    """
    # Unwrap FutureWrapper and mark it as consumed since its outcome
    # is now being forwarded to target_future.
    if isinstance(source, FutureWrapper):
        _, source = _unwrap_future(source)
    if isinstance(target_future, FutureWrapper):
        _, target_future = _unwrap_future(target_future, is_mark_consumed=False)


    if isinstance(
        source,
        (asyncio.Future, concurrent.futures.Future),
    ):
        _chain_future_results(source, target_future)
        return

    if loop is None:
        loop, _ = _resolve_active_loop()

    coro = _await_source(source)
    try:
        source_future = asyncio.run_coroutine_threadsafe(
            coro,
            loop,
        )
    except RuntimeError as exc:
        # Close the wrapper coroutine and underlying coroutine if the loop is closed/stopped
        # to prevent 'RuntimeWarning: coroutine was never awaited'.
        coro.close()
        if inspect.iscoroutine(source):
            source.close()
        _deliver_exception(target_future, exc)
        return

    _chain_future_results(source_future, target_future)


def _chain_future_results(
    source_future: FutureType[T],
    target_future: FutureType[T],
) -> None:
    """
    Transfer the outcome of a completed Future to a target Future.
    """

    def on_source_done(source: FutureType[T]) -> None:
        if source.cancelled():
            _deliver_cancel(target_future)
            return

        try:
            # Always retrieve the result/exception from source to avoid
            # "Future exception was never retrieved" warnings, even if target_future is already done.
            result = source.result()
        except _CANCELLED_ERRORS as exc:
            _deliver_exception(target_future, exc)
        except Exception as exc:
            _deliver_exception(target_future, exc)
        else:
            _deliver_result(target_future, result)

    if isinstance(source_future, asyncio.Future):
        if source_future.done():
            # Already completed; read state and forward directly without requiring an active source loop.
            on_source_done(source_future)
            return

        source_loop = source_future.get_loop()
        if source_loop.is_closed():
            _deliver_exception(
                target_future,
                RuntimeError("Source future's event loop is closed before completion."),
            )
            return

        try:
            source_loop.call_soon_threadsafe(
                source_future.add_done_callback,
                on_source_done,
            )
        except RuntimeError as exc:
            # The source event loop was closed concurrently.
            if source_future.done():
                on_source_done(source_future)
            else:
                _deliver_exception(target_future, exc)
    else:
        source_future.add_done_callback(on_source_done)


def _deliver_cancel(target: FutureType[T]) -> None:
    """
    Schedule cancellation of the target Future if it is still pending.
    """
    _dispatch_to_target_loop(target, _cancel_if_pending)


def _deliver_result(
    target: FutureType[T],
    result: T,
) -> None:
    """
    Schedule delivery of a result to the target Future.
    """
    _dispatch_to_target_loop(
        target,
        _set_result_if_pending,
        result,
    )


def _deliver_exception(
    target: FutureType[T],
    exc: BaseException,
) -> None:
    """
    Schedule delivery of an exception to the target Future.
    """
    _dispatch_to_target_loop(
        target,
        _set_exception_if_pending,
        exc,
    )


def _dispatch_to_target_loop(
    target: FutureType[T],
    callback: Callable[..., None],
    *args: object,
) -> None:
    """
    Dispatch a Future update in the context required by its implementation.
    """
    if isinstance(target, asyncio.Future):
        loop = target.get_loop()
        if loop.is_closed():
            return
        try:
            loop.call_soon_threadsafe(
                callback,
                target,
                *args,
            )
        except RuntimeError:
            # The event loop was closed concurrently; ignore delivery.
            pass
    else:
        callback(target, *args)

def _cancel_if_pending(target: FutureType[T]) -> None:
    """
    Cancel the target Future if it has not already completed.
    """
    if target.done():
        return

    try:
        target.cancel()
    except _INVALID_STATE_ERRORS:
        if not target.done():
            raise


def _set_result_if_pending(
    target: FutureType[T],
    result: T,
) -> None:
    """
    Set the target Future's result if it is still pending.
    """
    if target.done():
        return

    try:
        target.set_result(result)
    except _INVALID_STATE_ERRORS:
        if not target.done():
            raise


def _set_exception_if_pending(
    target: FutureType[T],
    exc: BaseException,
) -> None:
    """
    Set the target Future's exception if it is still pending.
    """
    if target.done():
        return

    try:
        target.set_exception(exc)
    except _INVALID_STATE_ERRORS:
        if not target.done():
            raise


def get_main_event_loop():
    """
    Returns the event loop that was set via initConfig(). This function should be called from the MainThread
    during the application startup. If such a call was not made, None will be returned.

    Returns:
        asyncio.AbstractEventLoop or None: The main event loop if set, otherwise None.
    """
    return _EVENT_LOOP


@deprecated(version="1.0.0", reason="Not in use", for_removal=True)
def _execute_task(task, task_future, executor):
    """
    Executes a task in the executor and propagates its outcome to task_future.

    Exception monitoring for base_future is handled by exec_in_executor().
    """
    func, args, kwargs = task
    base_future_wrapper = exec_in_executor(executor, func, *args, **kwargs)
    resolve_awaitable(base_future_wrapper, task_future)
    return base_future_wrapper



def _resolve_active_loop() -> tuple[asyncio.AbstractEventLoop, bool]:
    """
    Resolves the active event loop for scheduling tasks.

    First checks if there is an event loop running in the current thread
    (including a dedicated worker event loop). If not, falls back to the
    main `_EVENT_LOOP` initialized via `initConfig()`.

    Returns:
        tuple[asyncio.AbstractEventLoop, bool]: A tuple of (loop, is_current_thread_loop).

    Raises:
        RuntimeError: If no running event loop is found in the current thread and `_EVENT_LOOP`
                      is not initialized or not running.
    """
    try:
        running_loop = asyncio.get_running_loop()
        return running_loop, True
    except RuntimeError:
        pass

    if _EVENT_LOOP is not None and not _EVENT_LOOP.is_closed() and _EVENT_LOOP.is_running():
        return _EVENT_LOOP, False

    raise RuntimeError(
        "No running event loop in the current thread and _EVENT_LOOP is not running. "
        "Ensure initConfig() was called from the main thread with a running event loop."
    )

class AsyncExecutionQueue(RootMixin):
    """
    An asynchronous execution queue supporting synchronous functions
    and coroutine functions, with per-task executor selection.

    Tasks are submitted through a shared asyncio.Queue. The worker
    dispatches each task through exec_in_executor(), preserving
    ContextVars and propagating the final result or exception.
    """

    def __init__(self, **kwargs):
        custom_queue = kwargs.pop("queue", None)
        self._is_owns_queue = custom_queue is None
        self.queue = custom_queue if custom_queue is not None else asyncio.Queue()
        # If None, default asyncio ThreadPoolExecutor will be used.
        self.executor = kwargs.pop("executor", None)
        self._worker_task: Optional[asyncio.Task] = None
        self._closing: bool = False
        super().__init__(**kwargs)

    async def __aenter__(self):
        if self._closing:
            raise RuntimeError(
                "Cannot enter AsyncExecutionQueue while closing."
            )

        if self._worker_task is None or self._worker_task.done():
            loop, _ = _resolve_active_loop()
            self._worker_task = loop.create_task(self.worker())

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Wait for queued tasks to finish and stop the worker."""
        await self.aclose()
        return False

    async def aclose(self):
        """Wait for queued tasks to finish and stop the worker."""
        self._closing = True
        try:
            if self._worker_task is not None:
                await self.queue.join()
                self._worker_task.cancel()

                with contextlib.suppress(asyncio.CancelledError):
                    await self._worker_task

                self._worker_task = None

            if self._is_owns_queue:
                # Recreate the internal queue so the instance can be safely reused
                # across different event loops after closing.
                self.queue = asyncio.Queue()
        finally:
            self._closing = False

    async def aadd_task(self, func, /, *args, **kwargs) -> asyncio.Future:
        """
        Adds a task to the queue for asynchronous execution.

        The returned FutureWrapper tracks explicit consumption via
        await, result(), or exception(). Exceptions from unconsumed
        futures are logged automatically after a short delay.

        Args:
            func (Callable[..., Any]):
                The function or coroutine to execute.
            *args (Any):
                Positional arguments passed to func.
            **kwargs (Any):
                Keyword arguments passed to func.

        Returns:
            asyncio.Future:
                An awaitable future proxy representing the execution of func.
        """
        if self._worker_task is not None and not self._worker_task.done():
            worker_loop = self._worker_task.get_loop()
            loop, _ = _resolve_active_loop()
            if worker_loop is not loop and not worker_loop.is_closed() and worker_loop.is_running():
                # The queue worker is running on a different event loop (e.g. _EVENT_LOOP
                # while caller is in a worker_loop); bridge via add_task().
                bridged_fut = asyncio.wrap_future(
                    self.add_task(func, *args, **kwargs),
                    loop=loop,
                )
                wrapper = FutureWrapper(bridged_fut)
                handle_future_exception(wrapper)
                return wrapper

        return await self._aadd_task_with_executor(
            None,
            func,
            *args,
            **kwargs,
        )

    async def _aadd_task_with_executor(
        self,
        ctx: Optional[contextvars.Context],
        func,
        /,
        *args,
        **kwargs,
    ) -> asyncio.Future:
        """Enqueue a task together with its executor and context."""
        loop, _ = _resolve_active_loop()

        if self._closing:
            raise RuntimeError(
                "Cannot add task while AsyncExecutionQueue is closing."
            )

        if self._worker_task is None or self._worker_task.done():
            self._worker_task = loop.create_task(self.worker())

        if ctx is None:
            ctx = copy_context()

        # Pass the raw Future to the worker so internal completion/chaining
        # does not prematurely mark the public FutureWrapper as consumed.
        task_future = loop.create_future()
        wrapper = FutureWrapper(task_future)
        handle_future_exception(wrapper)

        await self.queue.put(
            (
                (func, args, kwargs),
                task_future,
                ctx,
            )
        )

        return wrapper

    async def worker(self):
        """
        Consume queued tasks and dispatch them for execution.

        A single consumer worker processes submissions sequentially,
        but submitted functions may execute concurrently in the executor.
        The worker does not wait for each function to finish before
        dispatching the next task. queue.join() waits for completion
        of all dispatched tasks.
        """
        loop, _ = _resolve_active_loop()
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.current_task()

        while True:
            task, task_future, ctx = await self.queue.get()

            if task_future.cancelled():
                self.queue.task_done()
                continue

            func, args, kwargs = task
            resolved_executor = self.executor if self.executor is not None else _GLOBAL_EXECUTOR

            try:
                execution_future: FutureWrapper = ctx.run(
                    exec_in_executor,
                    resolved_executor,
                    func,
                    *args,
                    **kwargs,
                )
            except Exception as exc:
                if not task_future.done():
                    task_future.set_exception(exc)

                self.queue.task_done()
                continue

            execution_future, _ = _unwrap_future(execution_future)

            def on_execution_done(
                source_future,
                *,
                target_future=task_future,
                queue=self.queue,
            ):

                unwrapping_awaitable = False
                try:
                    if target_future.done():
                        # If target_future was already cancelled/completed, ensure that any
                        # coroutine returned by source_future is properly closed to avoid RuntimeWarning.
                        if not source_future.cancelled():
                            try:
                                unused_res = source_future.result()
                            except Exception:
                                pass
                            else:
                                if inspect.iscoroutine(unused_res):
                                    unused_res.close()
                        return

                    try:
                        result = source_future.result()
                    except _CANCELLED_ERRORS:
                        target_future.cancel()
                    except Exception as exc:
                        target_future.set_exception(exc)
                    else:
                        # If source_future resolved to an Awaitable or Future (e.g. when exec_in_executor
                        # is overridden/mocked or returns an awaitable directly), unwrap it via resolve_awaitable.
                        if isinstance(result, (Awaitable, concurrent.futures.Future)):
                            try:
                                resolve_awaitable(result, target_future, loop=loop)
                            except Exception as exc:
                                if not target_future.done():
                                    target_future.set_exception(exc)
                            else:
                                target_future.add_done_callback(
                                    lambda _: queue.task_done()
                                )
                                # Mark as unwrapping and delay task_done() only after resolve_awaitable
                                # succeeds without raising a synchronous exception.
                                unwrapping_awaitable = True
                        else:
                            target_future.set_result(result)

                except asyncio.InvalidStateError:
                    # The target may have been cancelled concurrently.
                    pass
                finally:
                    if not unwrapping_awaitable:
                        queue.task_done()

            execution_future.add_done_callback(on_execution_done)

    def add_task(self, func, /, *args, **kwargs):
        """
        Adds a task to the queue for asynchronous execution and returns a future.

        The returned concurrent Future resolves to the final result of func,
        rather than the intermediate asyncio.Future returned by aadd_task().

        Args:
            func (Callable[..., Any]):
                The function to execute, which can be synchronous or asynchronous.
            *args (Any):
                Positional arguments to pass to func.
            **kwargs (Any):
                Keyword arguments to pass to func.

        Returns:
            concurrent.futures.Future:
                A future representing the final result of func.
        """
        result_future = concurrent.futures.Future()

        if self._closing:
            result_future.set_exception(
                RuntimeError("Cannot add task while AsyncExecutionQueue is closing.")
            )
            return result_future

        try:
            if  self._worker_task is not None \
                and not self._worker_task.done() \
                and not self._worker_task.get_loop().is_closed() \
                and self._worker_task.get_loop().is_running():

                loop = self._worker_task.get_loop()
            else:
                loop, _ = _resolve_active_loop()
        except RuntimeError as exc:
            result_future.set_exception(exc)
            return result_future


        if loop is None or loop.is_closed() or not loop.is_running():
            result_future.set_exception(
                RuntimeError("The configured event loop is not running.")
            )
            return result_future

        # Keep a reference to the submitted task Future so cancellation
        # of the concurrent Future can be propagated to the event loop.
        task_future_ref = []

        def cancel_task_if_needed(future):
            if not future.cancelled():
                return

            if task_future_ref:
                task_future = task_future_ref[0]

                if not task_future.done() and not loop.is_closed():
                    with contextlib.suppress(RuntimeError):
                        loop.call_soon_threadsafe(task_future.cancel)

        result_future.add_done_callback(cancel_task_if_needed)

        # Capture the caller's context in the synchronous thread before scheduling on the loop
        caller_ctx = copy_context()

        async def submit_task():
            if result_future.cancelled():
                return

            if self._closing:
                result_future.set_exception(
                    RuntimeError("Cannot add task while AsyncExecutionQueue is closing.")
                )
                return

            # Pass caller_ctx directly so the task executes with the synchronous caller's
            # ContextVars rather than the event loop task's context.
            task_future = await self._aadd_task_with_executor(
                caller_ctx,
                func,
                *args,
                **kwargs,
            )

            task_future_ref.append(task_future)

            if result_future.cancelled():
                task_future.cancel()
                return

            resolve_awaitable(task_future, result_future, loop=loop)

        coro = submit_task()

        try:
            submission_future = asyncio.run_coroutine_threadsafe(
                coro,
                loop,
            )
        except RuntimeError as exc:
            coro.close()

            try:
                result_future.set_exception(exc)
            except concurrent.futures.InvalidStateError:
                pass

            return result_future

        def on_submission_done(future):
            try:
                future.result()
            except _CANCELLED_ERRORS:
                if not result_future.done():
                    result_future.cancel()
            except Exception as exc:
                try:
                    result_future.set_exception(exc)
                except _INVALID_STATE_ERRORS:
                    pass

        submission_future.add_done_callback(on_submission_done)

        return result_future

def get_context_vars(*modules, factory_method_creator=None) -> List:
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
    _loop = asyncio.get_running_loop()  # Raises exception if there is no running event loop
    global _EVENT_LOOP
    _EVENT_LOOP = _loop

    global _GLOBAL_EXECUTOR
    # Set the global executor if provided
    _GLOBAL_EXECUTOR = kwargs.get('executor', None)

