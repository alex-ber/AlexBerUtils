#inspired by https://stackoverflow.com/questions/1408171/thread-local-storage-in-python
import threading
import asyncio
import inspect
import functools

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
    def __init__(self, **kwargs):
        # The delegation chain stops here
        pass

def validate_param(param_value, param_name):
    if param_value is None:
        raise ValueError(f"Expected {param_name} param not found")




class RLock:
    def __init__(self):
        self._sync_lock = threading.RLock()  # Synchronous reentrant lock
        self._async_lock = asyncio.Lock()  # Asynchronous lock
        self._sync_owner = None  # Owner of the synchronous lock
        self._async_owner = None  # Owner of the asynchronous lock
        self._sync_count = 0  # Reentrancy count for synchronous lock
        self._async_count = 0  # Reentrancy count for asynchronous lock

    def acquire(self):
        self._sync_lock.acquire()  # Acquire the underlying lock to enter the critical section
        try:
            current_thread = threading.current_thread()
            if self._sync_owner == current_thread:
                self._sync_count += 1
                return True  # Already acquired, no need to acquire again
            self._sync_owner = current_thread
            self._sync_count = 1
            return True  # Successfully acquired
        finally:
            self._sync_lock.release()  # Release the underlying lock to exit the critical section

    def release(self):
        self._sync_lock.acquire()  # Acquire the underlying lock to enter the critical section
        try:
            current_thread = threading.current_thread()
            if self._sync_owner == current_thread:
                self._sync_count -= 1
                if self._sync_count == 0:
                    self._sync_owner = None
                    self._sync_lock.release()  # Release the underlying lock
        finally:
            if self._sync_count != 0:
                self._sync_lock.release()  # Ensure the lock is released if not fully released

    async def async_acquire(self):
        await self._async_lock.acquire()  # Acquire the underlying lock to enter the critical section
        try:
            current_task = asyncio.current_task()
            if self._async_owner == current_task:
                self._async_count += 1
                return True  # Already acquired, no need to acquire again
            self._async_owner = current_task
            self._async_count = 1
            return True  # Successfully acquired
        finally:
            self._async_lock.release()  # Release the underlying lock to exit the critical section

    async def async_release(self):
        await self._async_lock.acquire()  # Acquire the underlying lock to enter the critical section
        try:
            current_task = asyncio.current_task()
            if self._async_owner == current_task:
                self._async_count -= 1
                if self._async_count == 0:
                    self._async_owner = None
                    self._async_lock.release()  # Release the underlying lock
        finally:
            if self._async_count != 0:
                self._async_lock.release()  # Ensure the lock is released if not fully released

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()

    async def __aenter__(self):
        await self.async_acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.async_release()

class LockingIterableMixin(RootMixin):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._obj = kwargs.get('obj')
        validate_param(self._obj, 'obj')
        self._lock = kwargs.get('lock')
        validate_param(self._lock, 'lock')

    def __iter__(self):
        return LockingIterator(iter(self._obj), self._lock)

class LockingIterator:
    def __init__(self, iterator, lock):
        self._iterator = iterator
        self._lock = lock

    def __iter__(self):
        return self

    def __next__(self):
        with self._lock:
            return next(self._iterator)

class LockingAsyncIterableMixin(RootMixin):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._obj = kwargs.get('obj')
        validate_param(self._obj, 'obj')
        self._lock = kwargs.get('lock')
        validate_param(self._lock, 'lock')

    def __aiter__(self):
        return LockingAsyncIterator(self._obj, self._lock)

class LockingAsyncIterator:
    def __init__(self, async_iterator, lock):
        self._async_iterator = async_iterator
        self._lock = lock

    def __aiter__(self):
        return self

    async def __anext__(self):
        async with self._lock:
            return await self._async_iterator.__anext__()


try:
    from langchain_core.language_models import BaseLanguageModel

    _is_available_base_language_model = True
except ImportError:
    BaseLanguageModel = None
    _is_available_base_language_model = False



try:
    from pydantic import BaseModel

    _is_available_pydantic = True
except ImportError:
    _is_available_pydantic = False



def _is_pydantic_obj(obj):
    if not _is_available_pydantic:
        return False
    ret = None
    try:
        from pydantic import BaseModel
        ret = isinstance(obj, BaseModel)
    except ImportError:
        ret = False
    return ret

class LockingPedanticObjMixin(RootMixin):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._obj = kwargs.get('obj')
        validate_param(self._obj, 'obj')
        self._is_pedantic_obj = _is_pydantic_obj(self._obj)


class LockingAccessMixin(LockingPedanticObjMixin):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._obj = kwargs.get('obj')
        validate_param(self._obj, 'obj')
        self._lock = kwargs.get('lock')
        validate_param(self._lock, 'lock')

    def __getattr__(self, name):
        attr = getattr(self._obj, name)

        if inspect.isroutine(attr):
            if self._is_pedantic_obj and name == '_copy_and_set_values':  # special case for Pydantic
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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._obj = kwargs.get('obj')
        validate_param(self._obj, 'obj')
        self._lock = kwargs.get('lock')
        validate_param(self._lock, 'lock')

    def __call__(self, *args, **kwargs):
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
    def __init__(self, **kwargs):
        lock = kwargs.get("lock", None)
        if not lock:
            lock = RLock()
            kwargs['lock'] = lock
        self._lock = lock

        super().__init__(**kwargs)

def _coerce_base_language_model(obj):
    if not _is_available_base_language_model:
        return
    if isinstance(obj, BaseLanguageModel):
        BaseLanguageModel.register(type(obj))

class LockingBaseLanguageModelMixin(RootMixin):
    def __init__(self, **kwargs):
        self._obj = kwargs.get('obj')
        validate_param(self._obj, 'obj')
        _coerce_base_language_model(self)



class LockingDefaultAndBaseLanguageModelMixin(LockingDefaultLockMixin, LockingBaseLanguageModelMixin):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class LockingProxy(LockingDefaultAndBaseLanguageModelMixin, LockingIterableMixin, LockingAsyncIterableMixin,
                   LockingAccessMixin, LockingCallableMixin):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
