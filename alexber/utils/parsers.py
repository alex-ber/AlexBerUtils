"""
See https://medium.com/analytics-vidhya/my-parser-module-429ed1457718 for documentation.
"""
import logging
logger = logging.getLogger(__name__)
from collections import OrderedDict

from configparser import ConfigParser
from argparse import ArgumentParser
import sys
import ast


def _as_dict(parser):
    """
    Go over all sections in the parser,
    convert's there's key/value as dictionary that
    for every section in the parser has dictionary
    with key/value pairs (both str).

    :param parser: (self)
    :return: dict with key/value as str
    """
    d = OrderedDict()
    for section in parser.sections():
        d[section] = OrderedDict()
        for key in parser.options(section):
            d[section][key] = parser.get(section, key)
    return d

ConfigParser.as_dict = _as_dict

#inspired by
#https://stackoverflow.com/questions/21920989/parse-non-pre-defined-argument
#https://stackoverflow.com/questions/51267814/argparse-for-unknown-number-of-arguments-and-unknown-names
def _args_as_dict(parser, args=None):
    """
    Go over source for arguments, takes argument of the form --key=value.
    Create dictionary.
    Strip out '--' prefix from the key and put key/value (as str) to dict.

    If args is None, sys.argv[1:] will be used as source for arguments.
    Note: sys.argv[0] is ignored as it contain the name of main .py file to run.

    :param parser: ArgumentParser (self)
    :param args: if is not None, will be used as source for arguments.
    :return:
    """

    #see #argumentParser.parse_known_args()
    if args is None:
        # args default to the system args
        args = sys.argv[1:]
    else:
        # make sure that args are mutable
        args = list(args)

    d = OrderedDict()

    key = None
    value = None
    for arg in args:
        if arg.startswith('--') and '=' in arg:
            key, value = arg.rsplit("=", 1)
        else:
            key = arg
            value = None
        if key.startswith('--'):
            key = key[2:]

        d[key] = value

    return d


ArgumentParser.as_dict = _args_as_dict


#insipred by https://stackoverflow.com/a/14258151/1137529
#
def safe_eval(value):
    '''
    The purpose of this function is convert numbers from str to correct type.
    This function support convertion of built-in Python number to correct type (int, float)
    This function doesn't support decimal.Decimal or datetime.datetime or numpy types.
    '''
    try:
        ret = ast.literal_eval(value)
    except (SyntaxError, ValueError):
        ret = value
    return ret

def is_empty(value):
    '''
    if value is None returns True.

    if value is empty iterable (for example, empty str or emptry list),
    returns true
    otherwise false

    Note: For not iterable values, behaivour is undefined.

    :param value:
    :return:
    '''
    if value is None:
        return True
    if value:
        ret = False
    else:
        ret = True
    return ret


def parse_boolean(value):
    '''
    if value is None returns None.

    if value is boolean, it is returned as it is.
    if value is str and value is equals ignoring case to "True", True is returned.
    if value is str and value is equals ignoring case to "False", False is returned.

    For every other value, the answer is undefined.

    :param value:
    :return:
    '''
    if value is None:
        return None

    if value in (True, False):
        return value
    try:
        return {"true": True, "false": False}[value.casefold()]
    except (AttributeError, KeyError):
        raise ValueError(f"unknown string for bool: {value!r}")

def parse_sys_args(argumentParser=None, args=None):
    """
    This function parses command line arguments.

    :param argumentParser:
    :param args: if not None, suppresses sys.args
    :return:
    """
    if argumentParser is None:
        argumentParser = ArgumentParser()
    argumentParser.add_argument("--general.config.file", nargs='?', dest='config_file', default='config.yml',
                                const='config.yml')
    params, unknown_arg = argumentParser.parse_known_args(args=args)

    sys_d = argumentParser.as_dict(args=unknown_arg)
    return params, sys_d
