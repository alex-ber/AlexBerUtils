#inspired by https://stackoverflow.com/questions/1408171/thread-local-storage-in-python
import logging
import concurrent.futures
import contextvars
import functools
import inspect

logger = logging.getLogger(__name__)


#should be initlialzied via initConfig() method, see below.
_EVENT_LOOP = None


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


import asyncio
import threading
from collections import deque


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

class LockingProxy(LockingDefaultAndBaseLanguageModelMixin, LockingIterableMixin, LockingAsyncIterableMixin, LockingAccessMixin, LockingCallableMixin):
    """
    A proxy class that combines multiple locking mixins.

    The `LockingProxy` class ensures that access to the wrapped object is thread-safe
    by using a provided lock. It supports iterable, async iterable, attribute access,
    and callable objects.

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

    ctx = contextvars.copy_context()
    afunc_call = functools.partial(ctx.run, afunc, *args, **kwargs)
    result = _execute_async_in_sync(afunc_call)
    return result


def initConfig(**kwargs):
    """
    Initializes the configuration required for using the lift_to_async() method.

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
