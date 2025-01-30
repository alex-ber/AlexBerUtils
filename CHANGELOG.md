# Changelog
All notable changes to this project will be documented in this file.

\#https://pypi.org/manage/project/alex-ber-utils/releases/


## Unreleased

## Changelog
## [0.12.10] 30.01.2024
### Fixed
- **Context Preservation for Coroutines**: Ensured that coroutine functions are executed 
within a copied context when run in an executor. This fix addresses a bug where coroutine 
functions bypassed `copy_context()`, potentially leading to issues with `ContextVars` 
not being maintained across asynchronous boundaries.

### Changed
- **Optimization for Regular Function Execution Path**: Refactored the creation of 
`func_call` and the `wrapper` function to only occur within the branch handling 
regular functions.

- **BREAKING CHANGE**: Singature of `_run_coroutine_in_thread()` was changed (this is internal
function, so you shouldn't use it anyway), 
`ctx` was added as first parameter. 

## [0.12.9] 19.12.2024

### Changed
- **AsyncContextManagerMixin**: bug fix. Now, it calls `async_acquire()` and `async_release()`.


## [0.12.8] 19.12.2024


### Added
- **SyncContextManagerMixin**: A new mixin to provide synchronous context management 
capabilities to classes. This mixin includes `__enter__()` and `__exit__()` methods to manage 
acquiring and releasing locks.
- **AsyncContextManagerMixin**: A new mixin to provide asynchronous context management
capabilities to classes. This mixin includes `__aenter__()` and `__aexit__()` methods to manage 
acquiring and releasing locks asynchronously.

### Changed
- **LockingProxy**: Enhanced to include synchronous and asynchronous context management 
through the integration of `SyncContextManagerMixin` and `AsyncContextManagerMixin`. 
This update allows `LockingProxy` to be used with both `with` and `async with` statements 
for better resource management in multi-threaded and asynchronous environments.

## [0.12.7] 18.12.2024

### Added
- Introduced `LockingGetItemMixin` to provide thread-safe access to items in a collection.
- Introduced `LockingSetItemMixin` to provide thread-safe modification of items in a collection.

### Changed
- Updated `LockingProxy` class to include `LockingGetItemMixin` and `LockingSetItemMixin` for handling thread-safe item access and modification.
- Updated the docstring of `LockingProxy` to reflect the inclusion of the new mixins.


## [0.12.6] 03.12.2024

### Added
- `get_main_event_loop()` allows retrieving the main event loop that was set during the application configuration
via `initConf()`. `initConf()` is intended to be called from the `MainThread` during the application startup. 
If the event loop has not been set, the function will return `None`. 


### Changed

- **BREAKING CHANGE** `run_coroutine_threadsafe` and `arun_coroutine_threadsafe()` was dropped. You can achieve the same result 
by using `run_coroutine_threadsafe()` (it just scheduled coroutine to run; it's fast), obtaining
`threading.Future` and doing the following 
```asyncio_future = asyncio.wrap_future(threading_future, loop=loop)```. Then if you want to get the 
result you can simply ```await asyncio_future```.


- **Documentation for**
- `asyncio.run_coroutine_threadsafe()` API https://alex-ber.medium.com/asyncio-run-coroutine-threadsafe-api-d24cc56a5255 


## [0.12.5] 01.12.2024

### Changed

- Now, in `AsyncExecutionQueue.__init__()` method executor can be None, not passed at all, or passed None 
explicitly. The executor resolution follows a specific order: directly provided executor, executor 
from `initConfig()`, or the default asyncio executor if None is provided. This change is backward compatible.
- **BREAKING CHANGE** Module `warnings.py` was renamed to `warning.py` to avoid shadowing of built-in `warnings.py`.  
- **BREAKING CHANGE** In `AsyncExecutionQueue` `worker_task` was renamed to `_worker_task`.
- Dosctrings of `AsyncExecutionQueue` executor role description is added. No functionality change.
- Dosctrings of `exec_in_executor()`, `exec_in_executor_threading_future()` side fact that
threads in the executor may have an event loop attached was added for clarity. This is also side effect.
- Nonfunctional change in `exec_in_executor_threading_future()`, avoiding variables scope hidden by renaming.
- `AsyncExecutionQueue.aclose()` guard check (`if self._worker_task`) was added. If somehow, between
`AsyncExecutionQueue.__init__()` and `AsyncExecutionQueue.__aenter__()` exception was raised,
this avoids `await None`.
- Fixing typo in docstring of `chain_future_results()`.

### Added

- `run_coroutine_threadsafe()`.  Sync/regular function,    wrapper around `asyncio.run_coroutine_threadsafe()`. 
Internally it uses `_EVENT_LOOP` that is initialized with MainThread's event loop via `initConfig()`.
It exposes `threading.Future` to the caller. Implementation is pretty **straightforwards**.
- `arun_coroutine_threadsafe()`. Async function/coroutine, wrapper around `asyncio.run_coroutine_threadsafe()`.
Internally it uses `_EVENT_LOOP` that is initialized with MainThread's event loop via `initConfig()`.
It exposes `threading.Future` to the caller. Implementation is **complex**. As intermediate step 
`asyncio_future=asyncio.wrap_future(base_future)` where `base_future` is a result of
`asyncio.run_coroutine_threadsafe()` call is used. `asyncio.wrap_future()` internally, uses private asyncio API.
It chains `base_future` and newly created `asyncio_future` so that when one completes, so does the other.
They progress together towards the completion, so **no "application freeze" occur**.

- **Documentation for**
- My `exec_in_executor()` API https://alex-ber.medium.com/my-exec-in-executor-api-72797e232f99
- My `AsyncExecutionQueue` https://alex-ber.medium.com/my-asyncexecutionqueue-4001ac168675

## [0.12.4] 23.11.2024

### Added

- **`AsyncExecutionQueue.add_task()` method**
  - Added a new method `add_task()` to the `AsyncExecutionQueue`, which allows for asynchronous task execution using an executor. This method supports both synchronous and asynchronous functions.
  - The executor resolution follows a specific order: directly provided executor, executor from `initConfig()`, or the default asyncio executor if none is provided.
  - The method ensures that `ContextVars` are preserved, maintaining context across asynchronous boundaries.
  - The function returns a `threading.Future` object, representing the future result of the task execution.


- **`chain_future_results()` function**:
  - Introduced a new utility function `chain_future_results()` to facilitate the transfer of results or exceptions between two futures. It supports both type of Futures, `threading.Future` and `asyncio.Future`.
  - This function is designed to be used as a callback for a `source_future` to propagate its result or exception to a `target_future`.
  - It ensures that the outcome of asynchronous operations is correctly handled and transferred, making it a versatile tool for managing future results in concurrent programming.



## [0.12.3] 23.11.2024

### Changed

- Now, in `exec_in_executor()` and `exec_in_executor_threading_future()` will preserve the metadata of `func`. 

## [0.12.2] 23.11.2024

**BREAKING CHANGE** 
### Removed 
- All new function that was in 0.12.1 beta-version.


### Added
- Introduced a new type alias `FutureType`. This type is designed to be compatible with both `asyncio.Future` 
and `concurrent.futures.Future`, allowing for functions that can handle both asynchronous and concurrent futures. 

- New unit tests for `exec_in_executor()` and `exec_in_executor_threading_future()`.

### Changed

- Now, in `exec_in_executor()` `ensure_thread_event_loop()` will be called in both async/sync function. Before this it
was only for async functions. That is call to `ensure_thread_event_loop()` is now optional for the users of 
`exec_in_executor()`.

- Inner implementation of `exec_in_executor_threading_future()`. Now, it actually works.


## [0.12.1] 16.11.2024

### Changed
- Updated the `aadd_task()` method in `AsyncExecutionQueue` to explicitly associate futures with the currently running 
event loop. This change enhances the robustness and maintainability of the code by ensuring that futures are bound to 
the correct event loop context, reducing the risk of potential issues related to event loop mismatches in future 
modifications or extensions of the codebase. This update is backward compatible as it does not alter the external 
behavior or interface of the aadd_task method. It only changes the internal implementation detail concerning how 
futures are managed.	  


## [0.12.0] 16.11.2024
### Added
- Introduced a `deprecated` decorator to mark functions as deprecated.
  - The decorator allows specifying the version since which the function is deprecated, the reason for deprecation, and whether the function is marked for removal.
  - It issues a customizable warning (defaulting to `DeprecationWarning`) when the decorated function is called.
  - This addition helps developers communicate deprecation status and future removal plans for functions in the codebase.

- **`exec_in_executor_threading_future()`** a thin wrapper around `exec_in_executor()`, which returns an 
`asyncio.Future`. This function executes a function or coroutine within a specified executor and converts the 
resulting `asyncio.Future` into a `threading.Future`. It preserves `ContextVars`, ensuring that context is 
maintained across asynchronous boundaries. For more details, see description of `exec_in_executor()`.

- **`exec_in_executor()`**: 
  - Added the `exec_in_executor` function to execute a function or coroutine within a specified executor while preserving `ContextVars`.
  - The function ensures context is maintained across asynchronous boundaries and resolves the executor in a prioritized manner:
    1. Uses the provided executor if available.
    2. Falls back to an executor set via `initConfig()`.
    3. Defaults to the asyncio executor if none is set.
  - Supports both coroutine and regular function execution.

- **`ensure_thread_event_loop()`**: 
  - Implemented the `ensure_thread_event_loop()` function to initialize an event loop for the current thread if it does not already exist.


- **`handle_result()`**: Introduced a new `handle_result()` function that transfers the result or exception from one future to another. 
This function is designed to be generic and can be used with any types of futures, ensuring that the outcome of task 
execution is properly propagated between futures.
  - **Usage**: To use this function, add it as a callback to the `source_future`:
    ```python
    # Add the chain_future_results function as a callback to the source_future
    source_future.add_done_callback(lambda fut: handle_result(fut, target_future))
    ```
  - **Arguments**:
    - `source_future`: The future from which to retrieve the result or exception.
    - `target_future`: The future on which to set the result or exception.

- **AsyncExecutionQueue**: 
- Introduced a new `AsyncExecutionQueue` class for managing asynchronous task execution using a specified executor. This class provides:
  - A context manager interface to start and stop a worker that processes tasks from the queue.
  - Asynchronous task execution with graceful queue closure.
  - Note: as a side fact, threads in the executor may have an event loop attached. This allows for the execution of asynchronous tasks within those threads.

#### Attributes

- `executor (Executor)`: The mandatory executor used to run tasks.
- `queue (asyncio.Queue)`: The optional queue that holds tasks to be executed. If not provided, a new `asyncio.Queue` is created by default.

#### Methods

- `worker()`: Continuously processes tasks from the queue until the `aclose()` method is called.
- `aadd_task(func, *args, **kwargs)`: Asynchronously adds a task to the queue for execution and returns a future.
- `aclose()`: Asynchronously closes the queue and waits for the worker to finish processing.

#### Initialization

- The `AsyncExecutionQueue` is initialized with a specified executor and an optional queue. The executor is required to run tasks, while a custom queue can be provided or the default `asyncio.Queue` will be used.

#### Context Management

- The `AsyncExecutionQueue` can be used as a context manager. When entering the context, the worker is started, and when exiting, the queue is closed, and the worker is stopped.


### Changed
- **`initConfig()`**: 
  - The `initConfig` function now also supports `exec_in_executor()` through the `executor` parameter.
  - This function is designed to be called from the main thread.
  - It accepts optional keyword arguments to configure a global executor that can be (optionally) used in `exec_in_executor()`.
- [GitHub Issue #14](https://github.com/alex-ber/AlexBerUtils/issues/14): Enhanced the `lift_to_async` function 
to handle `StopAsyncIteration` exceptions more gracefully. If a `StopAsyncIteration` exception is raised from `afunc`, 
it is now converted to a `RuntimeError` with a descriptive message. This change prevents a `TypeError` from being 
raised and ensures that the `Future` does not remain pending indefinitely.
- Updated `initConfig()`:
  - Initializes the configuration for `lift_to_async()` and `exec_in_executor()`.
  - Ensures it is called from the main thread with a running event loop.
  - Sets a global executor if provided via keyword arguments.
	

#### Example Usage
```python
# Example usage of the decorator
@deprecated(version='1.0', reason="Use `new_function` instead.", for_removal=True)
def old_function(x, y):
    """Returns the sum of two numbers."""
    return x + y

# Call the deprecated function
result = old_function(3, 4)
```



## [0.11.11] 22.10.2024

### Changed
- **OptionalNumpyWarning**: Moved the definition of `OptionalNumpyWarning` to a separate module (`alexber.utils.warnings`) to allow for easier suppression of the warning without triggering it during import. 
This change improves the flexibility and usability of the library for users who do not require NumPy.
  
- **Type Hints**: Fixed and improved type hints across the codebase to enhance code clarity and support for static type checking tools. 
This ensures better integration with IDEs and type checkers, providing more accurate code suggestions and error detection.

## [0.11.10] 22.10.2024 yanked

### Added
- **USE_NUMPY**: Introduced a flag to determine whether NumPy is available and should be used for sampling operations. This allows for performance optimizations when NumPy is installed.
- **SamplingError**: Added a custom exception class to handle errors when sampling fails after a maximum number of retries. It provides detailed error messages, including distribution type, retries, and bounds, aiding in debugging and error handling.
- **OptionalNumpyWarning**: Introduced a custom warning to notify users when NumPy is not available, and the system falls back to standard Python operations. The primary purpose of this warning is to provide users with the ability to suppress it if desired.

### Changed
- **BaseSampler**: Refactored the base class for sampling to support various statistical distributions with configurable parameters. This includes validation for distribution types and bounds.
- **Sampler**: The class can optionally use NumPy for sampling if it is available, allowing for potentially faster and more efficient sampling operations. If NumPy is not available, the class defaults to using Python's standard `random` module, ensuring compatibility across environments.
  - Note: The `expovariate` method has been adjusted to align with NumPy's exponential function, using the scale directly as the mean of the distribution.
- **max_retries**: Added a parameter to limit the number of attempts to sample a valid value, primarily to avoid infinite loops. This ensures that the sampling process terminates gracefully if a valid sample cannot be obtained within the specified number of retries.

## [0.11.9] 21.10.2024
### Added

- **Sampler Class**: Introduced the `Sampler` class, a flexible utility for sampling from various statistical distributions.

## Distribution Support

- The class supports multiple distributions, including:
  - **Log-normal (`lognormvariate`)**: Uses `math.log(self.scale)` for the mean of the underlying normal distribution.
  - **Normal (`normalvariate`)**: Standard normal distribution with specified mean and standard deviation.
  - **Exponential (`expovariate`)**: Uses `1 / self.scale` as the rate parameter (lambda).
  - **Von Mises (`vonmisesvariate`)**: Circular distribution with specified mean and concentration.
  - **Gamma (`gammavariate`)**: Two-parameter distribution with shape and scale.
  - **Gaussian (`gauss`)**: Similar to normalvariate, with mean and standard deviation.
  - **Beta (`betavariate`)**: Distribution defined on the interval [0, 1] with two shape parameters.
  - **Pareto (`paretovariate`)**: Heavy-tailed distribution with a single shape parameter.
  - **Weibull (`weibullvariate`)**: Distribution with shape and scale parameters.

## Configurable Parameters

- The class requires configuration of key parameters:
  - `distribution`: Specifies the distribution to sample from (required).
  - `shape`: Shape parameter for the distribution, controlling the spread and skewness. For log-normal, it represents sigma of the underlying normal distribution (required).
  - `scale`: Scale parameter for the distribution, shifting the distribution and determining its median. For log-normal, it represents exp(mu) of the underlying normal distribution. For exponential, it is the inverse of the rate parameter (1/lambda) (required).
  - `lower_bound`: Optional lower bound for the sampled value, defaulting to `None` (no lower bound).
  - `upper_bound`: Optional upper bound for the sampled value, defaulting to `None` (no upper bound).
  - `random_seed`: Optional seed for the random number generator, allowing for reproducibility.
  - `random_instance`: Optional custom instance of `random.Random` for generating random numbers.


## [0.11.8] 01.08.2024
### Changed
- `find_most_similar()` and `find_most_similar()` was fixed for the edge case when no comparison texts are provided. 
If no texts are provided, `find_most_similar_with_scores()` now returns [(some negative number, input_text), 0.0)], 
and `find_most_similar()` returns (some negative number, input_text). 
Docstrings of both method were also changed to reflect this change. 


## [0.11.7] 01.08.2024
### Changed
- `find_most_similar()` and `find_most_similar()` was fixed for the edge case when no comparison texts are provided. 
If no texts are provided, `find_most_similar_with_scores()` now returns [(some negative number, input_text), 1.0)], 
and `find_most_similar()` returns (some negative number, input_text). 
Docstrings of both method were also changed to reflect this change. 
 

## [0.11.6] 31.07.2024
### Changed

- `_LRUCache` and `_LFUCache` now supports the in operator.
Beforehand the work of the `AsyncCache` was incorrect.

## [0.11.5] 31.07.2024 YANKED

### Changed
- `async_cache()` is now support correctly methods. 

## [0.11.4] 31.07.2024 YANKED

### Changed
- `async_cache()` is now support correctly methods. 


## [0.11.3] 30.07.2024

### Added
- New class `AsyncCache` which supports both LFU (Least Frequently Used) and LRU (Least Recently Used) caching policies 
with optional Time-to-Live (TTL) for cache entries.
Additional profiling and statistics gathering for cache hits, misses, average, max, and min execution times.
- New decorator `async_cache()` for applying asynchronous caching to a function with configurable caching policy and TTL.
- `HashableWrapper` class: This class wraps an object to make it hashable.
It provides a fallback for objects that do not natively support hashing by using the string representation for hashing.
- `make_hashable()` function: A utility to convert various types of objects into hashable types. 
This function handles mappings, iterables, and objects with the `__hash__` method. 
Non-hashable objects are wrapped in a `HashableWrapper` to ensure compatibility as dictionary keys or set members.
- `is_iterable()` function: A utility to check if a value is iterable, excluding `None`, `str`, and `bytes`. 
- `is_mapping()` function: A utility to check if a value is a mapping (dict-like). 
It determines this by checking whether the given value implements the `.items()` method 
and whether that method is callable.

## [0.11.2] 30.07.2024
### Added
- Introduced `is_running_in_main_thread()` utility function to check if the current thread 
is the main thread.

- A configuration initializer `initConfig()` has been added. 
You MUST call `initConfig()` from the MainThread before using `lift_to_async()`.
It initializes the necessary configuration for using the `lift_to_async()` method. 

- `lift_to_async()` primitive ensures seamless execution of async functions in a 
synchronous environment, while preserving the context of ContextVar instances.
It makes easier to integrate async calls within existing synchronous codebases.

### Changed

- In the `RLock` class, the comparison of the lock owner with the current thread/task was changed 
from using the equality operator (`==`) to the `is` operator. 
This change should not affect the functionality because the `__eq__` method was not overridden.


## [0.11.1] 23.07.2024
### Added

- `RLock`  class to provide a reentrant lock that supports both synchronous and asynchronous 
operations. This lock ensures fairness by handling acquisition requests in the order they are made, 
both for threads and asynchronous tasks. See https://alex-ber.medium.com/a6b9a9021be8 for more details

- `LockingProxy` class to provide a comprehensive locking mechanism, ensuring thread-safe access and operations 
for various object types including iterables, async iterables, attributes, and callables. See 
https://alex-ber.medium.com/7a7a14021427 for more details.

- `prof_to_callgrind.sh` script for converting `.prof` files to `.callgrind` format using Docker.
See https://alex-ber.medium.com/converting-prof-files-to-callgrind-f6ae56fae0d3 for more details.
 
- `prof_to_callgrind.py` to handle the conversion of `profile` statistics to `callgrind` files. 
See https://alex-ber.medium.com/converting-prof-files-to-callgrind-f6ae56fae0d3 for more details.

# Profiling Script with High-Resolution Timer

This script demonstrates how to set up a cProfile profiler in Python using a high-resolution timer based on `time.perf_counter_ns()`.

```python
import time
import cProfile

# Define a precise timer function using time.perf_counter_ns()
def precise_timer():
    return time.perf_counter_ns()

# Create a cProfile.Profile object with the precise timer function
profiler = cProfile.Profile(timer=precise_timer)

# Usage note:
# The profiler is now configured to use the precise_timer function, 
# which provides higher resolution timing measurements in nanoseconds.
```

#### Misc
- `pyproject.toml` to specify build system requirements and configurations, 
ensuring compatibility with `setuptools`>=42 and `wheel`.

- `validate_param()` function to check for the presence of required parameters 
and raise a ValueError if they are missing.

- `RootMixin` class with an initializer that stops the delegation chain

- `LockingIterableMixin` to provide locking for iterable objects, ensuring thread-safe iteration.

- `LockingAsyncIterableMixin` to provide locking for asynchronous iterable objects, ensuring thread-safe iteration.

- `LockingAccessMixin` to provide locking for attribute access, ensuring thread-safe access to object attributes.

- `LockingCallableMixin` to provide locking for callable objects, ensuring thread-safe execution of callable objects.

- `LockingDefaultLockMixin` to provide a default lock if none is provided during initialization.

- `LockingBaseLanguageModelMixin` to provide locking for BaseLanguageModel objects, ensuring thread-safe access.

- `LockingDefaultAndBaseLanguageModelMixin` to combine default lock and BaseLanguageModel locking.


## [0.11.0] 22.06.2024
### Added
- New module `in_memory_similarity_search` added. 

This module is usable to calculate cosine similarity for small number of vectors.

It has 2 public function and 1 type hint.

- `find_most_similar()` - this function identifies the most similar text to a given 
input text from a list of provided texts. It uses an embedding class instance to convert 
texts into vectors and calculates the cosine similarity based on the specified Euclidean norm. 
The function returns a tuple containing the index and the most similar text.

- `find_most_similar_with_scores()` - this function finds the most similar texts to a given 
input text from a list of provided texts and returns their cosine similarity scores. 
It uses an embedding class instance to convert texts into vectors and calculates the 
similarity based on the specified Euclidean norm. 
The function returns a list of tuples, each containing the index, text, and similarity score. 

See https://alex-ber.medium.com/in-memory-similarity-search-998582fbb802 for details.


### Changed
- Removed leftover from multidispatch dependecy.
- Rename python3 to python across the documentation.

## [0.10.2] 05.05.2024
- Lose packaging constraint to packaging>=23.2.
- Fixed README.md to include packaging>=23.2.

## [0.10.1] 31.05.2024
### Changed
- Remove no longer supported Python versions 3.6 and 3.7 from setup's classifier.

## [0.10.0] 31.05.2024
### Changed
- Fixed README.md to include packaging<24.0,>=23.2
- Minimum library requirement is Python 3.8 now (not 3.9).
- Dockerfile's base docker image was changed to be based on Python 3.8 (not 3.9).
- importlib-metadata and it's dependency zipp are back. This is backport from Python 3.9.
It is a library that provides access to the metadata of installed packages. It was 
originally developed as a backport of the `importlib.metadata` module introduced in Python 3.8, 
allowing users of earlier Python versions to access package metadata in a consistent way.
It is used by `build`.

## [0.9.1] 31.05.2024
### Changed
- Fixed README.md to reflect changes in 0.9.0.

## [0.9.0] 31.05.2024


### Changed

- Minimum library requirement is Python 3.9 now.
- Dockerfile's base docker image was changed to be based on Python 3.9
- Some functionality was moved from dropped method_overloading_test.py to importer_test.py
- Implementation of inspects.ismethod() and inspects.has_method() was changed. 
- inspect_test.py was changed. inspects.has_method() now expected to return False on descriptors, including property,
(as it should in the first place).
- In Dockerfile setuptools was **downgraded** from 67.8.0 to 65.6.3. 
See https://stackoverflow.com/questions/76043689/pkg-resources-is-deprecated-as-an-api#comment136784284_76044568
- In Dockerfile reference to requirements-md.txt was droped.
- To requirements.in, req-piptools.txt and req-tests.txt packaging<24.0,>=23.2 was added.
- All requirements.txt was regenerated, so version has changed:
- importlib-metadata (and it's dependency zipp) were dropped.
- bcrypt upgraded from 4.1.1 to 4.1.3.
- build from 1.0.3 to 1.2.1.
- cryptography from 41.0.7 to 42.0.7.
- exceptiongroup from 1.2.0 to 1.2.1.
- hiyapyco from 0.5.4 to 0.6.0.
- jinja2 from 3.1.2 to 3.1.4.
- markupsafe from 2.1.3 to 2.1.5.
- paramiko from 3.3.1 to 3.4.0
- pip-tools from 7.3.0 to 7.4.1
- pluggy from 1.3.0 to 1.5.0
- pycparser 2.21 to 2.22.
- pyopenssl from 23.3.0 to 24.1.0.
- pyproject-hooks from 1.0.0 to 1.1.0.
- python-dotenv from 1.0.0 to 1.0.1
- wheel from 0.42.0 to 0.43.0
 
- (minor) Import to dropped enums.py was removed from parsers_test.py 

### Added
- inspects.resolve_function_args() - maps both explicit and default arguments of a function call by parameter name.
It merges args and kwargs, taking into account default values from func.
See https://alex-ber.medium.com/my-inspect-module-aa2d311246cb for more details.
- inspects.update_function_defaults() - decorator to change and remove default value.
See https://alex-ber.medium.com/my-inspect-module-aa2d311246cb for more details.
- pprint.py module. This module effectively changes the default values of the standard `pprint.pprint` module. Intended Usage:
See https://alex-ber.medium.com/my-pprint-module-f25a7b695e5f for more details.

Instead of:

```python
from pprint import pprint
```
use
```python
from alexber.utils.pprint import pprint
```

The defaults are:
- `indent`: 4
- `width`: 120
- `depth`: None
- `stream`: None
- `compact`: False
- `sort_dicts`: False
- `underscore_numbers`: False

See docstring of pprint.py module for more details.

### Removed
- Optional dependency alex-ber-utils[md] was removed. Unit-tests for multidispatch was removed.
Also files req-md.txt and requirements-md.txt was deleted. 
- Module enums was removed. It does monkey-patching to standard library's enums, that breaks them in Python 3.9+.

## [0.8.0] 04.12.2023

### Changed
- In setup.cfg flag mock_use_standalone_module
was changed to false (to use unittest.mock).
- Many version of the packages in extra was updated to latest:
- python-dotenv from 0.15.0 to 1.0.0.
- MarkupSafe is **downgraded** from 2.1.3 to 2.0.1
- bcrypt is upgraded from 3.2.0 to 4.1.1
- cffi is upgraded from 1.14.5 to 1.16.0
- cryptography is upgraded from 38.0.4 to to 41.0.7
- fabric is upgraded from 2.5.0 to 3.2.2
- invoke is upgraded from 1.7.3 to 2.2.0
- paramiko is upgraded from 2.7.2 to 3.3.1
- pycparser is upgraded from 2.20 to 2.21
- PyNaCl is upgraded from 1.3.0 to 1.5.0
- HiYaPyCo is upgraded from 0.5.1 to 0.5.4
 
 


### Added
- new extra-group, with name requirements-piptools.txt is added.
- alexber.utils.props.lazyproperty is added. TODO: add test for it
- New file requirements.in that have all high-level dependecies together.
- New file requirements.all that have pinned low-level dependecies resolution.


### Removed
- mock package was removed. pytest will use unittest.mock. See Changed
p.1 above.
- six was removed.

## [0.7.0] - 04-08-2023

### Changed
 
- Upgrade pyparsing==2.4.7 to 3.1.1.
- Upgrade cryptography from 3.4.7 to 41.0.3.
- Upgrade invoke from 1.4.1 to 1.7.3.
- Upgrade six from 1.15.0 to 1.16.0.
- Upgrade colorama from 0.4.3 to 0.4.4.
- Change declaration of namespace to `declare_namespace()` mechanism.

### Added
- Explicit dependency on pyOpenSSL==22.1.0 (lowest version where cryptography version is 
pinned). cryptography's and pyOpenSSL's version change should be in sync.

## [0.6.6] - 13-06-2021
### Added
- `stdLogging` module. The main function is `initStream()`. This is Thin adapter layer that redirects stdout/stderr 
(or any other stream-like object) to standard Python's logger. Based on 
https://github.com/fx-kirin/py-stdlogging/blob/master/stdlogging.py See https://github.com/fx-kirin/py-stdlogging/pull/1
Quote from  https://stackoverflow.com/questions/47325506/making-python-loggers-log-all-stdout-and-stderr-messages :
"But be careful to capture stdout because it's very fragile". I decided to focus on redirecting stderr only to the 
logger. If you want you can also redirect stdout, by making 2 calls to initStream() package-level method. 
But, because of https://unix.stackexchange.com/questions/616616/separate-stdout-and-stderr-for-docker-run it is 
sufficient only to do it for stderr for me.
See [https://alex-ber.medium.com/stdlogging-module-d5d69ff7103f] for details.
 
#### Changed
- `Doockerfiles` base-image. Now, you can transparentely switch betwee AMD64 to ARM 64 proccessor.
- `cffi` dependency from 1.14.3 to 1.14.5.
- `cryptography` dependency from 3.1.1 to 3.4.7.


## [0.6.5] - 12-04-2021
### Added
- `FixRelCwd` context-manager in `mains` module - This context-manager temporary changes current working directory to 
the one where relPackage is installed. What if you have some script or application that use relative path and you 
want to invoke in from another directory. To get things more complicated. maybe your “external” code also use 
*relative* path, but relative to another directory. 
See [https://alex-ber.medium.com/making-more-yo-relative-path-to-file-to-work-fbf6280f9511] for details.

- `GuardedWorkerException` context-manager in `mains` module - context manager that mitigate exception propogation 
from another process. It is very difficult if not impossible to pickle exceptions back to the parent process.
Simple ones work, but many others don’t. 
For example, CalledProcessError is not pickable (my guess, this is because of stdout, stderr data-members).
This means, that if child process raise CalledProcessError that is not catched, it will propagate to the parent 
process, but the propagation will fail, apparently because of bug in Python itself. 
This cause *pool.join() to halt forever — and thus memory leak!*
See [https://alex-ber.medium.com/exception-propagation-from-another-process-bb09894ba4ce] for details.

- `join_files()` function in `files` module - Suppose, that you have some multi-threaded/multi-process application 
where each thread/process creates some file (each thread/process create different file) 
and you want to join them to one file. 
See [https://alex-ber.medium.com/join-files-cc5e38e3c658] for details.


#### Changed
- `fixabscwd()` function in `mains` module - minour refactoring - moving out some internal helper function for reuse 
in new function.

- Base docker image version to alexberkovich/alpine-anaconda3:0.2.1-slim.
alexberkovich/alpine-anaconda3:0.1.1 has some minor changes relative to alexberkovich/alpine-anaconda3:0.1.1.
See [https://github.com/alex-ber/alpine-anaconda3/blob/master/CHANGELOG.md] for details.

#### Updated
### Documentation
- See [https://github.com/alex-ber/AlexBerUtils/issues/8] Config file from another directory is not resolved
(using `argumentParser` with `--general.config.file` can't be passed to `init_app_conf.parse_config()`) 


## [0.6.4] - 12/12/2020
#### Changed
- Base docker image version to alexberkovich/alpine-anaconda3:0.1.1-slim.
alexberkovich/alpine-anaconda3:0.1.1 has some minor changes relative to alexberkovich/alpine-anaconda3:0.1.0.
See [https://github.com/alex-ber/alpine-anaconda3/blob/master/CHANGELOG.md] for details.
alexberkovich/alpine-anaconda3:0.1.1-slim is "slim" version of the same docker image, most unused packaged are removed.

- update versions to pip==20.3.1 setuptools==51.0.0 wheel==0.36.1 

### Removed
- Script check_d.py

## [0.6.3] - 18/11/2020
#### Changed
- Base docker image version to alexberkovich/alpine-anaconda3:0.1.0, it has fix for potential security risk: Git was changed
not to store credential as plain text, but to keep them in memory for 1 hour,
see https://git-scm.com/docs/git-credential-cache

#### Updated
### Documentation
- My `deploys` module [https://medium.com/analytics-vidhya/my-deploys-module-26c5599f1b15 for documentation] 
is updated to contain `fix_retry_env()` function in `mains` module.

### Added 
### Documentation
- `fix_retry_env()` function in `mains` module. [https://alex-ber.medium.com/make-path-to-file-on-windows-works-on-linux-402ed3624f66]


## [0.6.2] - 17/11/2020
### Deprecation
- `method_overloading_test.py` is deprecated and will be removed once AlexBerUtils will support 
Python 3.9. It will happen approximately at 01.11.2021. 

This test uses `multidispatch` project that wasn't updated since 2014. 
In Python 3.8 it has following warning:

`multidispatch.py:163: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.9 it will stop working
    from collections import MutableMapping`

### Added
- class `OsEnvrionPathRetry`, function `fix_retry_env()` to `mains` module.

### Changed
- `OsEnvrionPathExpender` - refactored, functionality is preserved.


## [0.6.1] - 16/11/2020
### Added
- optional Dockerfile
- optional .env.docker for reference.
- Support of Python 3.8 is validated, see https://github.com/alex-ber/AlexBerUtils/issues/5

- Email formatting changed in Python 3.8, see https://github.com/alex-ber/AlexBerUtils/issues/7

Note that it is possible that `7bit` will be replaced with `8bit` as `Content-Transfer-Encoding`, 
that I'm considering as ok.

- `check_all.py` to run all unit test.

- `check_d.py` for sanity test.

- .dockerignore

- requirements*.txt - dependencies version changed, see https://github.com/alex-ber/AlexBerUtils/issues/6
- Because of pytest upgrade `conftest.py` was changed:
`pytest_configure()` was added to support dynamically used marks.
- In `ymlparsers_test.py` deprecation warning removed (it will be error in Python 3.9)
`collections.Mapping` was changed to `collections.abc.Mapping`. 

### Changed
- README.MD added section about Docker usage. 
- setup.py to indicate support of Python 3.8


## [0.5.3] - 10/09/2020
### Changed
- `alexber.utils.emails.initConfig` is fixed. Before this default variables where ignored.
- 2 Unit tests for `init_app_conf` are fixed. These fix are minors.
  

### Documentation
- `importer` module [https://medium.com/analytics-vidhya/how-to-write-easily-customizable-code-8b00b43406b2]
- `fixabscwd()` function in `mains` module.  [https://medium.com/@alex_ber/making-relative-path-to-file-to-work-d5d0f1da67bf]
- `fix_retry_env()` function in `mains` module. [https://alex-ber.medium.com/make-path-to-file-on-windows-works-on-linux-402ed3624f66]
- My `parser` module [https://medium.com/analytics-vidhya/my-parser-module-429ed1457718]
- My `ymlparsers` module [https://medium.com/analytics-vidhya/my-ymlparsers-module-88221edf16a6]
- My major `init_app_conf` module [https://medium.com/analytics-vidhya/my-major-init-app-conf-module-1a5d9fb3998c]
- My `deploys` module [https://medium.com/analytics-vidhya/my-deploys-module-26c5599f1b15]
- My `emails` module [https://medium.com/analytics-vidhya/my-emails-module-3ad36a4861c5] 
- My `processinvokes` module [https://medium.com/analytics-vidhya/my-processinvokes-module-de4d301518df]

## [0.5.2] - 21/06/2020
### Added 
- `path()` function in `mains` module. For older Python version uses
`importlib_resources` module. For newer version built in `importlib.resources`.
- `load_env()` function in `mains` module. Added kwargs forwarding. if dotenv_path or stream is present it will be used.
if ENV_PCK is present, dotenv_path will be constructed from ENV_PCK and ENV_NAME.
Otherwise, kwargs will be forwarded as is to load_dotenv.
- `fix_env()` function in `mains` module. For each key in ENV_KEYS, this method prepends full_prefix to os.environ[key].
full_prefix is calculated as absolute path of `__init__.py` of ENV_PCK. 
   

### Changed
``processinvokes`` function ```run_sub_process``` - documentation typo fixed.
Lower Python version to 3.6.  

## [0.5.1] - 06-05-2020
### Added 

- `mains` module explanation article https://medium.com/@alex_ber/making-relative-path-to-file-to-work-d5d0f1da67bf is published.

- `fabs` module. It adds cp method to fabric.Connection.

This method is Linux-like cp command. It copies single file to remote (Posix) machine. 

- Spited dependency list for setup.py req.txt (inexact versions, direct dependency only) and for 
reproducible installation requirements.txt (exact versions, all, including transitive dependencies).

- Added req-fabric.txt, requirements-fabric.txt - Fabric, used in `fabs` module.

- Added req-yml.txt, requirements-yml.txt - Yml-related dependencies, used in ymlparsers.py 
and in init_app_conf.py, deploys.py; optionally used in ymlparsers_extra.py, emails.py.

Main dependency is HiYaPyCo. I'm using feature that is availlable in the minimal version.

HiYaPyCo depends upon PyYAML and Jinja2. Limitations for Jinja2 is from HiYaPyCo project.

- Added req-env.txt, requirements-env.txt - pydotenv, optionally used in deploys.py.

- Added `inspects.has_method`(cls, methodName). Check if class cls has method with name methodName directly, 
or in one of it's super-classes.

- Added `pareser.parse_sys_args` function parses command line arguments.

- Added `ymlparsers` module - `load`/`safe_dump` a Hierarchical Yml files. This is essentially wrapper arround HiYaPyCo project with streamlined 
and extended API and couple of work-arrounds. 

Note: this module doesn't use any package-level variables in hiYaPyCo module, including hiYaPyCo.jinja2env.
This module do use Jinja2's `Environment`.  

It also has another defaults for `load`/`safe_dump` methods.
They can be overridden in `initConfig()` function.

`safe_dump()` method supports simple Python objects like primitive types (str, integer, etc), list, dict, **OrderedDict**.

`as_str()`- convenient method for getting str representation of the data,
for example of dict.

`DisableVarSubst` - use of this context manager disables variable substation in the `load()` function.

`initConfig` - this method reset some defaults. If running from the MainThread, this method is idempotent.
 
- Added `init_app_conf` **major** module. 

The main function is `parse_config`.  This function parses command line arguments first.
Than it parse yml files. Command line arguments overrides yml files arguments. 
Parameters of yml files we always try to convert on best-effort basses.
Parameters of system args we try convert according to `implicit_convert` param.

If you supply `implicit_convert=True`, than `mask_value()` will be applied to the flat map (first parameter).
Otherwise, `implicit_convert` wiil have the value that was set in `intiConfig()`. By default it is `True`.

Command line key --general.profiles or appropriate key default yml file is used to find 'profiles'.
Let suppose, that --config_file is resolved to config.yml.
If 'profiles' is not empty, than it will be used to calculate filenames
that will be used to override default yml file.
Let suppose, 'profiles' resolved to ['dev', 'local']. Than first config.yml
will be loaded, than it will be overridden with config-dev.yml, than
it will be overridden with config-local.yml.
At last, it will be overridden with system args.
This entry can be always be overridden with system args.

`ymlparsers` and `parser` modules serves as Low-Level API for this module.

`mask_value()` implemented as a wrapper to `parsers.safe_eval()` method with support for boolean
variables. This implementation is used to get type for arguments that we get from system args.
This mechanism can be easily replaced with your own one.

`to_convex_map()` This method receives dictionary with 'flat keys', it has simple key:value structure
where value can't be another dictionary.
It will return dictionary of dictionaries with natural key mapping,
optionally, entries will be filtered out according to white_list_flat_keys and,
optionally, value will be implicitly converted to appropriate type.

In order to simulate dictionary of dictionaries 'flat keys' compose key from outer dict with key from inner dict
separated with dot.
For example, 'general.profiles' 'flat key' corresponds to convex map with 'general' key with dictionary as value
that have one of the keys 'profiles' with corresponding value.

If you supply `implicit_convert=True`, than `mask_value()` will be applied to the values of the received flat dictionary.
Otherwise, `implicit_convert` wiil have the value that was set in `intiConfig()`. By default it is True.

`merge_list_value_in_dicts` - merges value of 2 dicts. This value represents list of values.
Value from flat_d is roughly obtained by flat_d[main_key+'.'+sub_key].
Value from d is roughly obtained by d[main_key][sub_key].

If you supply `implicit_convert=True`, than `mask_value()` will be applied to the flat map (first parameter).
Otherwise, `implicit_convert` wiil have the value that was set in `intiConfig()`. By default it is `True`.

`initConfig` - you can set default value of `implicit_convert`. By default it is `True`.
This parameters is used if `implicit_convert` wasn't explicitly supplied. This method is idempotent.

- Added `deploys` module.
This module is usable in your deployment script. See also `fabs` module. 

This method use `parsers`, ymlparsers`, `init_app_conf` as it's low-level API. `init_app_conf` usage is limited.

The main function is `load_config()`. It is simplified method for parsing yml configuration file with optionally 
overrided profiles only. See `init_app_conf.parse_config()` for another variant.

`split_path` - Split filename in 2 part parts by split_dirname. first_part will ends with split_dirname.
second_part will start immediately after split_dirname.

`add_to_zip_copy_function` - Factory method that returns closure that can be used as copy_function param in 
`shutil.copytree()`.

- Added `emails` module.
This module contains extensions of the logging handlers.
This module optionally depends on `ymlparseser` module.
It is better to use `EmailStatus` context manager with configured `emailLogger`.
It is intended to configure first your `emailLogger` with `OneMemoryHandler` (together with `SMTPHandler`).
Than the code block that you want to aggregate log messages from is better to be enclosed with `EmailStatus`
context manager.

`alexber.utils.emails.SMTPHandler` is customization of `logging.handlers.SMTPHandler`. It's purpose is to connect to
SMTP server and actually send the e-mail. Unlike `logging.handlers.SMTPHandler` this class expects for record.msg to be built EmailMessage.
You can also change use of underline SMTP class to SMTP_SSL, LMTP, etc. 
This implementation is *thread-safe*.

`alexber.utils.emails.OneMemoryHandler` is variant of `logging.handlers.MemoryHandler`. This handler aggregates 
log messages until `FINISHED` log-level is received or application is going to terminate abruptly (see docstring
of `calc_abrupt_vars()` method for the details) and we have some log messages in the buffer. On such event 
all messages (in the current Thread) are aggregated to the single `EmailMessage`. The subject of the `EmailMessage` 
is determined by `get_subject()` method. 
If you want to change delimeters used to indicate variable declaration inside template, see docstring of the 
`get_subject()` method.
It is better to use `EmailStatus` context manager with configured emailLogger. See docstring of `EmailStatus`.  
This implementation is *thread-safe*.

`alexber.utils.emails.EmailStatus` -  if contextmanager exits with exception (it fails), than e-mail with 
subject formatted with faildargs and faildkwargs will be send.
Otherwise, e-mail with subject formatted with successargs and successkwargs will be send.
All messages (in the current Thread) will be aggregated to one long e-mail with the subject described in 
`OneMemoryHandler.get_subject()` method. 
	
`alexber.utils.emails.initConfig` - this method reset some defaults. This method is idempotent.
By default, `SMTP` class from `smtplib` is used to send actual e-mail. You can change it to `SMTP_SSL`, `LMTP`,
or another class by specifying default_smpt_cls_name.
You can also specified default port for sending e-mails.

`processInvokes` module has one primary function - `run_sub_process()` This method run subprocess and logs it's out 
to the logger. This method is sophisticated decorator to `subprocess.run()`. It is useful, when your subprocess  
run's a lot of time and you're interesting to receive it's `stdout` and `stderr`. By default, it's streamed to log.
You can easily customize this behavior, see `initConig()` method.  

`initConig()` This method can be optionally called prior any call to another function in this module. You can use your 
custom class for the logging. For example, FilePipe. 

 
### Changed
- Spited dependency list for setup.py req.txt (inexact versions, direct dependency only) and for 
reproducible installation requirements.txt (exact versions, all, including transitive dependencies).
 
- README.md changed, added section 'Alternatively you install install from requirements file:'. 
Some other misc changed done.

- CHANGELOG.md version 0.4.1 misc changes.

- Misc improvement in unit tests.

- Fixed `parser.safe_eval` - safe_eval('%(message)s') was blow up, now it returns value as is. 
See https://github.com/alex-ber/AlexBerUtils/issues/2  

- Enhanced `importer.importer` - added support for PEP 420 (implicit Namespace Packages).  
Namespace packages are a mechanism for splitting a single Python package across multiple directories on disk.
When interpreted encounter with non-empty __path__ attribute it adds modules found in those locations
to the current package.
See https://github.com/alex-ber/AlexBerUtils/issues/3

- In all documentation refference to `pip3` was changed to `python3 -m pip`

## [0.4.1] - 2020-04-02
**BREAKING CHANGE** I highly recommend not to use 0.3.X versions.
### Removed 
- module `warns` is droped

### Changed
- *Limitation:*:

`mains` module wasn't tested with frozen python script (frozen using py2exe). 

- module `mains` is rewritten. Function `initConf` is dropped entirely.
- module `mains` now works with logger and with warnings (it was wrong decision to work with warnings).


## [0.3.4] - 2020-04-02
### Changed
- CHANGELOG.md fixed
- `warns` module bug fixed, now warnings.warn() works.
- FixabscwdWarning is added to simplify warnings disabling.
- Changing how `mains` module use `warns`.


## [0.3.3] - 2020-04-02
### Changed
- CHANGELOG.md fixed


## [0.3.2] - 2020-04-01
### Changed
- To REAMDE.md add `Installing new version` section
- Fix typo in REAMDE.md (tests, not test). 
- Fixing bug: now, you're able to import package in the Python interpreter (`setups.py` fixed)
- Fixing bug: `warns` module now doesn't change log_level in the preconfigured logger in any cases.
- **BREAKING CHANGE**: In`mains` module method `warnsInitConfig()` was renamed to `mainInitConfig()` 
Also singature was changed.  
- `mains` module minor refactored.

 
### Added
- Unit tests are added for `warns` module 
- Unit tests are added for `mains` module

## [0.3.1] - 2020-04-01
### Changed
- Tests minor improvements.
- Excluded tests, data from setup.py (from being installed from the sdist.)
- Created MANIFEST.in
 

### Added
- `warns `module is added:
 
It provides better integration between warnings and logger. 
Unlike `logging._showwarning()` this variant will always go through logger. 

`warns.initConfig()` has optional file parameter (it's file-like object) to redirect warnings. 
Default value is `sys.stderr`.
 
If logger for `log_name` (default is `py.warnings`) will be configured before call to `showwarning()` method, 
than warning will go to the logger's handler with `log_level` (default is `logging.WARNING`).

If logger for `log_name` (default is `py.warnings`) willn't be configured before call to showwarning() method, 
than warning will be done to `file` (default is `sys.stderr`) with `log_level` (default is `logging.WARNING`).
 
- `main` module is added:

`main.fixabscwd()` changes `os.getcwd()` to be the directory of the `__main__` module.

`main.warnsInitConfig()` reexports `warns.initConfig()` for convenience.   



### Added
- Tests for alexber.utils.thread_locals added.

## [0.2.5] - 2019-05-22
### Changed
- Fixed bug in UploadCommand, git push should be before git tag.


## [0.2.4] - 2019-05-22
### Changed
- Fixed bug in setup.py, incorrect order between VERSION and UploadCommand (no tag was created on upload)

## [0.2.1] - 2019-05-22
### Changed
- setup url fixed.
- Added import of Enum to alexber.utils package.

## [0.2.0] - 2019-05-22
### Changed
- setup.py - keywords added.

## [0.1.1] - 2019-05-22
### Changed
- README.md fixed typo.

## [0.1.0] - 2019-05-22
### Changed
- alexber.utils.UploadCommand - bug fixed, failed on git tag, because VERSION was undefined.


## [0.0.1] - 2019-05-22
### Added
- alexber.utils.StrAsReprMixinEnum - Enum Mixin that has __str__() equal to __repr__().
- alexber.utils.AutoNameMixinEnum-  Enum Mixin that generate value equal to the name.
- alexber.utils.MissingNoneMixinEnum - Enum Mixin will return None if value will not be found.
- alexber.utils.LookUpMixinEnum - Enim Mixin that is designed to be used for lookup by value. 

  If lookup fail, None will be return. Also, __str__() will return the same value as __repr__().
- alexber.utils.threadlocal_var, get_threadlocal_var, del_threadlocal_var. 

  Inspired by https://stackoverflow.com/questions/1408171/thread-local-storage-in-python

- alexber.utils.UploadCommand -  Support setup.py upload.

    UploadCommand is intented to be used only from setup.py

    It's builds Source and Wheel distribution.

    It's uploads the package to PyPI via Twine.

    It's pushes the git tags.

- alexber.utils.uuid1mc is is a hybrid between version 1 & version 4. This is v1 with random MAC ("v1mc").

    uuid1mc() is deliberately generating v1 UUIDs with a random broadcast MAC address.

    The resulting v1 UUID is time dependant (like regular v1), but lacks all host-specific information (like v4).
    
    Note: somebody reported that ran into trouble using UUID1 in Amazon EC2 instances.
    

- alexber.utils.importer.importer - Convert str to Python construct that target is represented.
- alexber.utils.importer.new_instance - Convert str to Python construct that target is represented. 
args and kwargs will be passed in to appropriate __new__() / __init__() / __init_subclass__() methods.
- alexber.utils.inspects.issetdescriptor - Return true if the object is a method descriptor with setters.

  But not if ismethod() or isclass() or isfunction() are true.
- alexber.utils.inspects.ismethod - Return false if object is not a class and not a function. 
Otherwise, return true iff signature has 2 params.
- alexber.utils.parsers.safe_eval - The purpose of this function is convert numbers from str to correct type.
  
  This function support convertion of built-in Python number to correct type (int, float)
  
  This function doesn't support decimal.Decimal or datetime.datetime or numpy types.  
- alexber.utils.parsers.is_empty - if value is None returns True.
   
   if value is empty iterable (for example, empty str or emptry list),returns true otherwise false.

   Note: For not iterable values, behaivour is undefined.
- alexber.utils.parsers.parse_boolean - if value is None returns None.

    if value is boolean, it is returned as it is.
    if value is str and value is equals ignoring case to "True", True is returned.
    if value is str and value is equals ignoring case to "False", False is returned.

    For every other value, the answer is undefined. 



- alexber.utils.props.Properties - A Python replacement for java.util.Properties class
   
   This is modelled as closely as possible to the Java original.
   
   Created - Anand B Pillai <abpillai@gmail.com>.
   
   Update to Python 3 by Alex.
   
   Also there are some tweeks that was done by Alex.

<!--
### Changed
### Removed
-->
