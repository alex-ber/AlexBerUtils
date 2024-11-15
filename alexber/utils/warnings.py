import warnings
import functools

# Define a custom warning for optional NumPy support
class OptionalNumpyWarning(Warning):
    """Custom warning to indicate that NumPy is not available and a fallback to standard Python is used."""



def deprecated(version=None, reason=None, for_removal=False, warning_class=DeprecationWarning):
    """
    A decorator to mark functions as deprecated.

    This decorator can be used to indicate that a function is deprecated and may be removed in future versions.
    It issues a warning when the decorated function is called.

    Args:
        version (str, optional): The version since which the function is considered deprecated.
        reason (str, optional): The reason why the function is deprecated.
        for_removal (bool, optional): If True, indicates that the function is marked for removal.
        warning_class (Warning, optional): The class of warning to be issued. Defaults to DeprecationWarning.

    Returns:
        function: The decorated function that issues a deprecation warning when called.
    """
    def decorator(func):
        message = f"{func.__name__} is deprecated"
        if version:
            message += f" since version {version}"
        if reason:
            message += f": {reason}"
        if for_removal:
            message += " and is marked for removal."
        else:
            message += " and will be removed in a future version."

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(message, warning_class, stacklevel=2)
            return func(*args, **kwargs)
        return wrapper
    return decorator
