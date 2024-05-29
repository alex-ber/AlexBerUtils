"""
This module has the e

effectively changes default values of standard pprint-related functions.
It does it by monkey-patching, so you should import this module BEFORE
you're importing pprint or any function from theire.

"""


import logging
logger = logging.getLogger(__name__)

import inspect
import pprint as _pprint
from .inspects import update_function_defaults
import importlib

def _calc_pprint_new_params():
    # Define the default values
    default_values = {
        'indent': 4,
        'width': 120,
        'depth': None,
        'stream': None,
        'compact': False,
        'sort_dicts': False,
        'underscore_numbers': False
    }

    # Get the parameters of PrettyPrinter.__init__
    init_signature = inspect.signature(_pprint.PrettyPrinter.__init__)
    valid_params_d = init_signature.parameters #dict-like

    # Remove unsupported values from default_values
    default_values = {k: v for k, v in default_values.items() if k in valid_params_d}
    return default_values


_pprint_new_params = _calc_pprint_new_params()


# Dynamically define __all__ based on _pprint's __all__
__all__ = _pprint.__all__.copy()

# Dynamically update defaults for each item in pprint
this_module = importlib.import_module(__name__)
for name in __all__:
    _obj = getattr(_pprint, name)
    if inspect.isfunction(_obj):
        updated_func = update_function_defaults(_obj, new_defaults=_pprint_new_params)
        setattr(this_module, name, updated_func)
    elif inspect.isclass(_obj):
        # Create a new class dynamically
        class _cloned_obj(_obj):
            pass

        updated_init = update_function_defaults(_cloned_obj.__init__, new_defaults=_pprint_new_params)
        setattr(_cloned_obj, '__init__', updated_init)
        setattr(this_module, name, _cloned_obj)