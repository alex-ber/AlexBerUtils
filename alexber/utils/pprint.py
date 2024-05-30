"""
This module effectively changes default values of the standard pprint.pprint module.
Intended usage:

instead of: from pprint import pprint
use:        from alexber.utils.pprint import pprint

You can utilize any publicly available functions from pprint, including *.

One of the main changes is to set sort_dicts=False.
From Python 3.7 onward, dictionary order of dict is guaranteed to be the insertion order.
This behavior was an implementation detail of CPython from version 3.6.
As a result, the order of keys is now deterministic, eliminating the need to sort keys.

The defaults are:

indent: 4,
width: 120,
depth: None,
stream: None,
compact: False,
sort_dicts: False,
underscore_numbers: False

If a value is absent in your Python version's pprint (for example, underscore_numbers was added only in Python 3.10),
and you are using a lower version (e.g., Python 3.9), this argument will be safely ignored.

See https://alex-ber.medium.com/my-pprint-module-f25a7b695e5f for more details.
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