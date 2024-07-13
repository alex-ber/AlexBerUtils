#inspired by https://stackoverflow.com/questions/1408171/thread-local-storage-in-python
import threading
import asyncio

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

