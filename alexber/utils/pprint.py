"""
This module effectively changes default values of standard pprint-related functions.
It does it by monkey-patching, so you should import this module BEFORE
you're importing pprint or any function from theire.

"""


import logging
logger = logging.getLogger(__name__)

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

        # Map positional arguments to their corresponding keyword arguments
        arg_names = list(default_values.keys())
        arg_dict = dict(zip(arg_names, args))

        # Check for conflicts between args and kwargs
        for key, value in arg_dict.items():
            if key in kwargs:
                raise ValueError(f"Parameter '{key}' is provided both as positional argument and keyword argument.")

        # Merge args and kwargs, giving priority to kwargs
        combined_args = {**default_values, **arg_dict, **kwargs}

        super().__init__(**combined_args)

pprint.PrettyPrinter = CustomPrettyPrinter

