import functools
import time
from collections import defaultdict, deque
from typing import Any, Optional, Union
from .thread_locals import RLock
from .mains import make_hashable, HashableWrapper
import inspect

class _LRUCache:
    """A simple LRU (Least Recently Used) cache implementation."""

    def __init__(self, maxsize: int):
        self.maxsize = maxsize
        self.cache = {}
        self.order = deque()

    def __getitem__(self, key: Any) -> Any:
        if key not in self.cache:
            raise KeyError(f"Key '{key}' not found in cache.")
        self.order.remove(key)
        self.order.append(key)
        return self.cache[key]

    def __setitem__(self, key: Any, value: Any):
        if key in self.cache:
            self.order.remove(key)
        elif len(self.cache) >= self.maxsize:
            oldest_key = self.order.popleft()
            del self.cache[oldest_key]
        self.cache[key] = value
        self.order.append(key)

    def __len__(self) -> int:
        return len(self.cache)

    def __contains__(self, key: Any) -> bool:
        return key in self.cache
    def clear(self):
        self.cache.clear()
        self.order.clear()


class _LFUCache:
    """A simple LFU (Least Frequently Used) cache implementation."""

    def __init__(self, maxsize: int):
        self.maxsize = maxsize
        self.cache = {}
        self.freq = defaultdict(int)
        self.min_freq = 0
        self.freq_list = defaultdict(deque)

    def __getitem__(self, key: Any) -> Any:
        if key not in self.cache:
            raise KeyError(f"Key '{key}' not found in cache.")
        self._increase_freq(key)
        return self.cache[key]

    def __setitem__(self, key: Any, value: Any):
        if key in self.cache:
            self.cache[key] = value
            self._increase_freq(key)
        else:
            if len(self.cache) >= self.maxsize:
                self._evict()
            self.cache[key] = value
            self.freq[key] = 1
            self.min_freq = 1
            self.freq_list[1].append(key)

    def _increase_freq(self, key: Any):
        freq = self.freq[key]
        self.freq[key] += 1
        self.freq_list[freq].remove(key)
        if not self.freq_list[freq]:
            del self.freq_list[freq]
            if self.min_freq == freq:
                self.min_freq += 1
        self.freq_list[freq + 1].append(key)

    def _evict(self):
        evict_key = self.freq_list[self.min_freq].popleft()
        if not self.freq_list[self.min_freq]:
            del self.freq_list[self.min_freq]
        del self.cache[evict_key]
        del self.freq[evict_key]

    def __len__(self) -> int:
        return len(self.cache)

    def __contains__(self, key: Any) -> bool:
        return key in self.cache

    def clear(self):
        self.cache.clear()
        self.freq.clear()
        self.freq_list.clear()
        self.min_freq = 0


class AsyncCache:
    """
    An asynchronous cache that supports both LFU (Least Frequently Used) and LRU
    (Least Recently Used) eviction policies and an optional Time-to-Live (TTL) for cache entries.
    """

    def __init__(self, maxsize, ttl=None, policy="LFU"):
        """
        Initializes the AsyncCache with the given parameters.

        Args:
            maxsize (int): Maximum size of the cache.
            ttl (Optional[int]): Time-to-Live for cache entries in seconds. Defaults to None.
            policy (str): Cache eviction policy. Can be either "LFU" or "LRU". Defaults to "LFU".
        """
        if policy == "LFU":
            self.cache = _LFUCache(maxsize=maxsize)
        elif policy == "LRU":
            self.cache = _LRUCache(maxsize=maxsize)
        else:
            raise ValueError("Invalid policy. Use 'LFU' or 'LRU'.")

        self.ttl = ttl
        self.expiry_times = {}  # To track expiry times of keys when ttl is not None
        self.lock = RLock()
        self.hits = 0
        self.misses = 0
        self.total_time_ns = 0
        self.total_calls = 0
        self.max_time_ns = 0
        self.min_time_ns = float('inf')

    def _wrap_key(self, key: Any) -> Union[HashableWrapper, Any]:
        try:
            _ = hash(key)
            return key
        except TypeError:
            return HashableWrapper(key)

    async def __getitem__(self, key):
        key = self._wrap_key(key)

        async with self.lock:
            current_time = time.perf_counter_ns()
            if key in self.cache:
                if self.ttl is not None:
                    if current_time < self.expiry_times.get(key, float('inf')):
                        # Cache hit
                        self.hits += 1
                        return self.cache[key]
                    else:
                        # Expired, remove it from both caches
                        self.cache._evict()
                        self.expiry_times.pop(key, None)
                        self.misses += 1
                        raise KeyError(f"Key '{key}' has expired.")
                else:
                    # Cache hit without TTL
                    self.hits += 1
                    return self.cache[key]
            else:
                self.misses += 1
                raise KeyError(f"Key '{key}' not found in cache.")

    async def __setitem__(self, key, value):
        key = self._wrap_key(key)

        async with self.lock:
            self.cache[key] = value
            if self.ttl is not None:
                self.expiry_times[key] = time.perf_counter_ns() + self.ttl * 1e9  # ttl is in seconds, convert to ns

    async def update_profiling(self, exec_time_ns):
        async with self.lock:
            self.total_calls += 1
            self.total_time_ns += exec_time_ns
            self.max_time_ns = max(self.max_time_ns, exec_time_ns)
            self.min_time_ns = min(self.min_time_ns, exec_time_ns)

    async def get_stats(self):
        async with self.lock:
            avg_time_ns = self.total_time_ns / self.total_calls if self.total_calls > 0 else 0.0
            hit_miss_ratio = self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0.0
            return {
                'hits': self.hits,
                'misses': self.misses,
                'hit_miss_ratio': f"{hit_miss_ratio:.4f}",
                'max_time': f"{self.max_time_ns / 1e9:.4f} s",
                'min_time': f"{(self.min_time_ns / 1e9) if self.min_time_ns != float('inf') else 0.0:.4f} s",
                'avg_time': f"{avg_time_ns / 1e9:.4f} s",
                'total_calls': self.total_calls,
                'current_size': len(self.cache),
                'max_size': self.cache.maxsize,
                'ttl_sec': f"{self.ttl:.4f}" if self.ttl is not None else "None"
            }

    async def clear(self):
        """Clear the cache and reset all stats."""
        async with self.lock:
            self.cache.clear()
            self.expiry_times.clear()
            self.hits = 0
            self.misses = 0
            self.total_time_ns = 0
            self.total_calls = 0
            self.max_time_ns = 0
            self.min_time_ns = float('inf')




_MAX_SIZE_SENTINEL = object()
_TTL_SENTINEL = object()

def async_cache(maxsize=_MAX_SIZE_SENTINEL, ttl=_TTL_SENTINEL, policy="LFU"):
    """
    A decorator to apply asynchronous caching to a function.

    Args:
        maxsize (int): Maximum size of the cache.
        ttl (Optional[int]): Time-to-Live for cache entries in seconds. Defaults to None.
        policy (str): Cache eviction policy. Can be either "LFU" or "LRU". Defaults to "LFU".
    """
    kwargs = {}
    if maxsize is not _MAX_SIZE_SENTINEL:
        kwargs['maxsize'] = maxsize
    if ttl is not _TTL_SENTINEL:
        kwargs['ttl'] = ttl

    cache_instance = AsyncCache(**kwargs, policy=policy)

    def decorator(fn):
        @functools.wraps(fn)
        async def wrapped_instance(*args, **kwargs):
            if not args:
                # No positional arguments; cache key based only on keyword arguments
                cache_key = make_hashable((None, frozenset(kwargs.items())))
            else:
                # Check if the first argument is a class instance (indicating a bound method)
                b = inspect.isclass(args[0].__class__)
                if b:
                    # The function is a method bound to an instance
                    instance_id = id(args[0])
                    cache_key = make_hashable((instance_id, args[1:], frozenset(kwargs.items())))
                else:
                    # The function is a standalone function
                    cache_key = make_hashable((args, frozenset(kwargs.items())))

            # Try to get the result from the cache
            try:
                value = await cache_instance.__getitem__(cache_key)
                return value
            except KeyError:
                pass
            # Calculate the result and store it in the cache
            start_time_ns = time.perf_counter_ns()
            result = await fn(*args, **kwargs)
            exec_time_ns = time.perf_counter_ns() - start_time_ns
            await cache_instance.update_profiling(exec_time_ns)
            await cache_instance.__setitem__(cache_key, result)
            return result

        wrapped_instance.cache_instance = cache_instance  # Attach the cache instance to the function
        return wrapped_instance

    return decorator
