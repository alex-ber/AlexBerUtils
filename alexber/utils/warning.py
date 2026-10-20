from collections.abc import Callable
import functools
import inspect
from types import NoneType
from typing import Any, TypeVar, overload
import warnings

from string import punctuation as _p
TERMINAL_PUNCTUATION = tuple(c for c in _p if c not in ('(', ')', '{', '}', '[', ']'))


T = TypeVar("T", bound=Callable[..., Any])


# Define a custom warning for optional NumPy support
class OptionalNumpyWarning(Warning):
    """Custom warning to indicate that NumPy is not available and a fallback to standard Python is used."""


def _build_deprecated_message(
    target: Any,
    version: str | None,
    reason: str | None,
    for_removal: bool,
) -> str:
    # Fallback chain: __qualname__ -> __name__ -> repr()
    name = getattr(target, "__qualname__", None) \
           or getattr(target, "__name__", None) \
           or repr(target)

    parts = [f"{name} is deprecated"]
    if version and (clean_version := version.strip()):
        parts.append(f"since version {clean_version}")
    if for_removal:
        parts.append("and is marked for removal")

    message = " ".join(parts)
    if reason and (clean_reason := reason.strip()):
        message += f": {clean_reason}"
    if not message.endswith(TERMINAL_PUNCTUATION):
        message += "."
    return message


# Case 1: Bare decorator @deprecated or direct call deprecated(fn, version="1.0")
@overload
def deprecated(
    obj: T,
    *,
    version: str | None = None,
    reason: str | None = None,
    for_removal: bool = False,
    warning_class: type[Warning] | None = None,
    stacklevel: int = 1,
) -> T: ...


# Case 2: Decorator factory @deprecated(version="1.0", ...)
@overload
def deprecated(
    obj: None = None,
    *,
    version: str | None = None,
    reason: str | None = None,
    for_removal: bool = False,
    warning_class: type[Warning] | None = None,
    stacklevel: int = 1,
) -> Callable[[T], T]: ...


# Inspired by Java's 1.5 @Deprecated annotation (written in 2024 before Python 3.13's warnings.deprecated (PEP 702)).
# Currently this project supports Python 3.10+, so warnings.deprecated is not available for all versions.
# Note that this API differs from warnings.deprecated.
# See https://docs.python.org/3.13/library/warnings.html#warnings.deprecated
def deprecated(
    obj: T | None = None,
    *,
    version: str | None = None,
    reason: str | None = None,
    for_removal: bool = False,
    warning_class: type[Warning] | None = None,
    stacklevel: int = 1,
) -> T | Callable[[T], T]:
    """
    A decorator to mark functions, coroutines, generators, or methods as deprecated.

    Can be used as `@deprecated`, `@deprecated(version="1.0", reason="...")`,
    or called directly as `deprecated(func, version="1.0")`.

    Note:
        - Decorating classes, callable class instances, or `functools.partial`
          objects directly is not supported and raises `TypeError`. Decorate the
          underlying function, `__init__`, `__call__`, or specific methods instead.
        - Sets `__deprecated__` on the returned wrapper for runtime introspection.
          Static type checkers (mypy, Pyright) only recognize PEP 702's
          `warnings.deprecated` / `typing_extensions.deprecated` for static diagnostics.

    Semantics & Contract:
        - Regular functions and methods emit a warning immediately when called.
        - Coroutine functions (`async def`), generator functions (`yield`), and
          async generator functions (`async def ... yield`) preserve their
          respective `inspect.is*` introspection flags across Python 3.10+ and
          emit the warning when execution begins (i.e., when awaited or iterated).

    Args:
        obj (Callable, optional): The function or method to decorate when used
            without parentheses or called directly. Defaults to None.
        version (str, optional): The version since which the function is deprecated.
        reason (str, optional): The reason why the function is deprecated.
        for_removal (bool, optional): If True, indicates that the function is scheduled
            for removal and defaults `warning_class` to `FutureWarning`. Defaults to False.
        warning_class (type[Warning], optional): The warning category to emit.
            Defaults to `FutureWarning` if `for_removal=True`, else `DeprecationWarning`.
        stacklevel (int, optional): Additional stack levels to walk up when emitting
            the warning. Must be an integer >= 1. Defaults to 1.

    Returns:
        Callable: The decorated function/method, or a decorator factory if `obj` is None.
    """
    if version is not None and not isinstance(version, str):
        raise TypeError(
            f"version must be a str or None, got {type(version).__name__}."
        )

    if reason is not None and not isinstance(reason, str):
        raise TypeError(
            f"reason must be a str or None, got {type(reason).__name__}."
        )

    if not isinstance(for_removal, bool):
        raise TypeError(
            f"for_removal must be a bool, got {type(for_removal).__name__}."
        )

    if warning_class is not None and (
        not isinstance(warning_class, type) or not issubclass(warning_class, Warning)
    ):
        raise TypeError(
            f"warning_class must be a subclass of Warning, got {warning_class!r}."
        )

    if isinstance(stacklevel, bool) or not isinstance(stacklevel, int):
        raise TypeError(
            f"stacklevel must be an int, got {type(stacklevel).__name__}."
        )

    if stacklevel < 1:
        raise ValueError(f"stacklevel must be >= 1, got {stacklevel}.")

    # Default to FutureWarning when `for_removal=True`, because Python silently
    # filters out standard DeprecationWarning in user code by default.
    actual_warning_class = warning_class or (
        FutureWarning if for_removal else DeprecationWarning
    )
    # Add 1 to stacklevel to account for the wrapper frame itself
    internal_stacklevel = stacklevel + 1

    def decorator(target: T) -> T:
        # Descriptor objects must be handled before the callable check.
        # staticmethod is callable in Python 3.10+, but directly
        # wrapping descriptors would break their binding semantics.
        if isinstance(target, (classmethod, staticmethod, property)):
            raise TypeError(
                f"@deprecated cannot be applied on top of @{type(target).__name__}. "
                f"Place @deprecated underneath it."
            )

        if isinstance(target, type):
            raise TypeError(
                "@deprecated cannot be applied to classes; "
                "decorate __init__ or specific methods instead."
            )

        if not callable(target):
            raise TypeError(
                f"@deprecated can only be applied to callables, got {type(target).__name__}."
            )

        if not inspect.isroutine(target):
            raise TypeError(
                f"@deprecated can only be applied to functions or methods, "
                f"got {type(target).__name__} (for callable instances or partial "
                f"objects, decorate the underlying function or __call__ method instead)."
            )

        message = _build_deprecated_message(target, version, reason, for_removal)

        # Handle coroutine functions, generator functions, async generator functions,
        # and regular functions/methods while preserving inspect.is* introspection.
        wrapper: Callable[..., Any] = NoneType
        if inspect.iscoroutinefunction(target):

            @functools.wraps(target)
            async def coro_wrapper(*args: Any, **kwargs: Any) -> Any:
                warnings.warn(
                    message, actual_warning_class, stacklevel=internal_stacklevel
                )
                return await target(*args, **kwargs)

            wrapper = coro_wrapper
        elif inspect.isgeneratorfunction(target):

            @functools.wraps(target)
            def gen_wrapper(*args: Any, **kwargs: Any) -> Any:
                warnings.warn(
                    message, actual_warning_class, stacklevel=internal_stacklevel
                )
                return (yield from target(*args, **kwargs))

            wrapper = gen_wrapper
        elif inspect.isasyncgenfunction(target):

            @functools.wraps(target)
            async def asyncgen_wrapper(*args: Any, **kwargs: Any) -> Any:
                warnings.warn(
                    message, actual_warning_class, stacklevel=internal_stacklevel
                )
                agen = target(*args, **kwargs)
                try:
                    val = await agen.asend(None)
                    while True:
                        try:
                            sent = yield val
                        except BaseException as exc:
                            val = await agen.athrow(exc)
                        else:
                            val = await agen.asend(sent)
                except StopAsyncIteration:
                    return

            wrapper = asyncgen_wrapper
        else:

            @functools.wraps(target)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                warnings.warn(
                    message, actual_warning_class, stacklevel=internal_stacklevel
                )
                return target(*args, **kwargs)

            wrapper = sync_wrapper

        wrapper.__deprecated__ = message  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    if obj is not None:
        return decorator(obj)

    return decorator