import inspect
from functools import wraps
from typing import Dict, List, Any, Optional, Callable, Type

import logging
logger = logging.getLogger(__name__)


def issetdescriptor(object: Any) -> bool:
    """Return true if the object is a method descriptor with setters.

    But not if ismethod() or isclass() or isfunction() are true.
    """
    if inspect.isclass(object) or inspect.ismethod(object) or inspect.isfunction(object):
        # mutual exclusion
        return False
    tp = type(object)

    return hasattr(tp, "__set__")


import inspect
from typing import Any


def ismethod(object: Any) -> bool:
    """Check if the given object is a method.

    If the object is a class, return False.
    If the object is not a function or method, return False.

    :param object: The object to check.
    :return: True if the object is a method, False otherwise.
    """
    return inspect.ismethod(object) or (inspect.isfunction(object) and hasattr(object, '__self__'))

def has_method(cls: Type, methodName: str) -> bool:
    """
    Check if class cls has a method with name methodName directly,
    or in one of its super-classes.

    :param cls: The class to check.
    :param methodName: The name of the method to look for.
    :return: True if the method exists, False otherwise.
    """
    return inspect.isroutine(getattr(cls, methodName, None))


def update_function_defaults(func: Callable, new_defaults: Optional[Dict[str, Any]] = None,
                             remove_defaults: Optional[List[str]] = None, is_forced: bool = False):
    """
    Decorator to change and remove default values.

    :param func: function/method to apply on.
    :param new_defaults: Dictionary of new default values to apply.
    :param remove_defaults: List of parameter names to remove default values from.
    :param is_forced: If False (default), only func's params that do have default value will be updated.
                      If True, all func's params will be updated that are mentioned by name in new_defaults and remove_defaults.
    :return: Decorated function with modified default values.
    """
    if new_defaults is None:
        new_defaults = {}
    if remove_defaults is None:
        remove_defaults = []

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get the signature of the original function
        sig = inspect.signature(func)

        # Create a new signature with updated default values
        new_params = []
        for param in sig.parameters.values():
            if is_forced or param.default is not inspect.Parameter.empty:
                if param.name in new_defaults:
                    new_param = param.replace(default=new_defaults[param.name])
                elif param.name in remove_defaults:
                    new_param = param.replace(default=inspect.Parameter.empty)
                else:
                    new_param = param
            else:
                new_param = param
            new_params.append(new_param)

        new_sig = sig.replace(parameters=new_params)

        # Bind the arguments to the new signature
        bound_args = new_sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        # Call the original function with the bound arguments
        _bounded_args = bound_args.args
        _bounded_kwargs = bound_args.kwargs
        return func(*_bounded_args, **_bounded_kwargs)

    return wrapper
