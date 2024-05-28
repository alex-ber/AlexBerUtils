"""
This module effectively changes default values of standard pprint-related functions.
It does it by monkey-patching, so you should import this module BEFORE
you're importing pprint or any function from theire.

"""


import logging
logger = logging.getLogger(__name__)

import inspect
import pprint
from pprint import PrettyPrinter

class CustomPrettyPrinter(PrettyPrinter):
    def __init__(self, *args, **kwargs):
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
        init_signature = inspect.signature(PrettyPrinter.__init__)
        valid_params_d = init_signature.parameters #collections.OrderedDict

        # Remove unsupported values from default_values
        default_values = {k: v for k, v in default_values.items() if k in valid_params_d}

        # Map positional arguments to their corresponding keyword arguments
        args_names_l = list(default_values.keys())
        args_d = dict(zip(args_names_l, args))

        # Check for conflicts between args and kwargs
        for key, value in args_d.items():
            if key in kwargs:
                raise ValueError(f"Parameter '{key}' is provided both as positional argument and keyword argument.")

        # Merge args and kwargs, giving priority to kwargs
        combined_args = {**default_values, **args_d, **kwargs}
        super().__init__(**combined_args)

pprint.PrettyPrinter = CustomPrettyPrinter

