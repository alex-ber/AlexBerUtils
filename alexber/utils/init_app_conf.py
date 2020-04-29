import logging
logger = logging.getLogger(__name__)

from collections import OrderedDict, deque
from pathlib import Path
import io as _io
from alexber.utils.parsers import is_empty, safe_eval as _convert, parse_boolean, ArgumentParser
import alexber.utils.ymlparsers as ymlparsers

class conf(object):
    GENERAL_KEY = 'general'
    PROFILES_KEY = 'profiles'
    #WHITE_LIST_IMPLICIT_KEY = 'whiteListImplicitely'    #default True
    WHITE_LIST_KEY = 'whiteListSysOverride'
    LIST_ENSURE_KEY ='listEnsure'

    CONFIG_KEY = 'config'
    FILE_LEY = 'file'

def _bool_convert(value):
    try:
        ret = parse_boolean(value)
        return ret
    except ValueError:
        ret = _convert(value)
    return ret

def _bool_is_empty(value):
    try:
        ret = parse_boolean(value)
        return ret is None
    except ValueError:
        ret = is_empty(value)
    return ret


def mask_value(value, implicit_convert=True):
    """
    If bool(implicit_convert) is False then, return value as is.
    Otherwise, we assume Python built-in types, including bool, and we're converting it to appropriate type.

    Bool values are case-insensitive.

    :param value: str to ccnvert
    :param implicit_convert: detault True. Whether to convert value using alexber.utils.parsers.safe_eval() function.
    :return:
    """


    ret = _bool_convert(value) \
        if implicit_convert \
        else value
    return ret

def _do_ensure_list(flat_d, list_ensure, implicit_convert=True):
    b = is_empty(list)
    if b:
        return

    for flat_key in list_ensure:
        flat_value = _ensure_list(flat_d, flat_key, implicit_convert)
        flat_d[flat_key] = flat_value


def _ensure_list(flat_d, key, implicit_convert=True):
    def _ensure_list(v):
        value = str(v)
        elements = value.split(",")

        # empty string will become null
        elements = [None if is_empty(value) else value for value in elements]
        ret = [mask_value(value, implicit_convert=implicit_convert) for value in elements]

        return ret

    if flat_d is None:
        flat_d = {}
    val = flat_d.get(key, None)
    b= _bool_is_empty(val)
    if b:
        if key in flat_d.keys():
            #we have key:None?
            return [val]
        return []
    return _ensure_list(val)


def merge_list_value_in_dicts(flat_d, d, main_key, sub_key):
    """
    This method merge value of 2 dicts. This value represents list of values.

    Value from flat_d is roughly obtained by flat_d[main_key+'.'+sub_key].
    Value from d is roughly obtained by d[main_key][sub_key].

    If value (or intermediate value) is not found empty dict is used.

    This method assumes that flat_d value contain str that represent list (comma-delimited).
    This method assumes that d[main_key] contains dict.

    This method implicitly converts every element inside list to Python built-in type.

    :param flat_d: flat dictionoray, usually one that was created from parsing system args.
    :param d: dictionary of dictionaries,  usually one that was created from parsing YAML file.
    :param main_key: d[main_key] is absent or dict.
    :param sub_key: d[main_key][sub_key] is absent or list.
    :return: merged convreted value, typically one from flat_d, if empty than from d
    """

    if flat_d is None:
        raise TypeError("flat_d can't be None")

    if d is None:
        raise TypeError("d can't be None")

    flat_key = '.'.join([main_key, sub_key])
    flat_value = _ensure_list(flat_d, flat_key)

    length_flat_value = len(flat_value)

    subvalue = d.get(main_key, {})
    value = subvalue.get(sub_key, {})

    merged_value = value if length_flat_value == 0 else flat_value
    return merged_value

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
    return params.config_file, sys_d

def _is_white_listed(white_list_flat_keys, flat_key):
    b = is_empty(white_list_flat_keys)
    if b:
        return True

    for white_list_flat_key in white_list_flat_keys:
        if flat_key.startswith(white_list_flat_key):
            return True
    return False

def flat_keys(d, white_list_flat_keys=None, implicit_convert=True):
    dd = OrderedDict()

    for flat_key, value in d.items():
        if not ('.' in flat_key and _is_white_listed(white_list_flat_keys, flat_key)):
            logger.info(f"Skipping key {flat_key}. It doesn't contain dot.")
            continue

        keys = flat_key.split(".")
        length = len(keys)

        inner_d = dd
        for i, part_key in enumerate(keys):
            if i + 1 == length:  # last element
                inner_d = inner_d.setdefault(part_key, mask_value(value, implicit_convert))
            else:
                inner_d = inner_d.setdefault(part_key, OrderedDict())
    return dd

def _parse_profiles(sys_d, default_d):
    profiles = merge_list_value_in_dicts(sys_d, default_d, conf.GENERAL_KEY, conf.PROFILES_KEY)
    b = is_empty(profiles)
    if b:
        profiles = []
    return profiles


def _parse_white_list_implicitely(default_d):
    subvalue = default_d.get(conf.GENERAL_KEY, {})
    value = subvalue.get(conf.WHITE_LIST_KEY, {})

    ret= is_empty(value)
    if ret is None:
        ret = True
    return ret


def _parse_white_list(default_d):
    calc_implicitely = _parse_white_list_implicitely(default_d)

    if calc_implicitely:
        white_list=[key for key in default_d.keys() if key not in conf.WHITE_LIST_KEY]
        return white_list

    #default_d[conf.GENERAL_KEY][conf.WHITE_LIST_KEY] is not empty
    subvalue = default_d.get(conf.GENERAL_KEY, {})
    white_list = subvalue.get(conf.WHITE_LIST_KEY, {})

    return white_list

def _parse_list_ensure(sys_d, default_d):
    list_ensure = merge_list_value_in_dicts(sys_d, default_d, conf.GENERAL_KEY, conf.LIST_ENSURE_KEY)

    b = is_empty(list_ensure)
    if not b:
        # we already proceesed profiles, white_list
        #we should process list_ensure
        profiles_flat_key = '.'.join([conf.GENERAL_KEY, conf.PROFILES_KEY])
        list_ensure_flat_key = '.'.join([conf.GENERAL_KEY, conf.LIST_ENSURE_KEY])
        white_list_flat_key = '.'.join([conf.GENERAL_KEY, conf.WHITE_LIST_KEY])

        list_ensure = [flat_key for flat_key in list_ensure \
                       if flat_key not in {profiles_flat_key, list_ensure_flat_key, white_list_flat_key}]
    else:
        list_ensure = []
    return list_ensure

def _get_white_listed(d, white_list_flat_keys):
    b = is_empty(d)
    if b:
        return d
    dd = OrderedDict()

    for flat_key, value in d.items():
        if not ('.' in flat_key and _is_white_listed(white_list_flat_keys, flat_key)):
            logger.info(f"Skipping key {flat_key}. It doesn't white listed.")
            continue

        dd[flat_key] = value
    return dd


def _parse_sys_args(argumentParser=None, args=None):
    if ymlparsers.HiYaPyCo.jinja2ctx is None:
        raise ValueError("You should call alexber.utils.ymlparsers.initConfig() first")

    config_file, sys_d0  = parse_sys_args(argumentParser, args)
    full_path = Path(config_file).resolve()  # relative to cwd

    with ymlparsers.DisableVarSubst():
        default_d = ymlparsers.load([str(full_path)])

    white_list = _parse_white_list(default_d)
    sys_d = _get_white_listed(sys_d0, white_list)

    profiles = _parse_profiles(sys_d, default_d)

    list_ensure = _parse_list_ensure(sys_d, default_d)

    _do_ensure_list(sys_d, list_ensure)

    dd = flat_keys(sys_d)
    return dd, profiles, white_list, list_ensure, full_path




def _parse_yml(sys_d, profiles, config_file='config.yml'):
    if ymlparsers.HiYaPyCo.jinja2ctx is None:
        raise ValueError("You should call alexber.utils.ymlparsers.initConfig() first")

    base_full_path = Path(config_file).resolve() #relative to cwd

    base_suffix = base_full_path.suffix
    base_name = base_full_path.with_suffix("").name

    with _io.StringIO() as sys_buf:
        ymlparsers.safe_dump(sys_d, sys_buf)

        buffersize = len(profiles) + 1  #default_profile
        yml_files = deque(maxlen=buffersize)

        yml_files.append(str(base_full_path))
        full_path = base_full_path

        for profile in profiles:
            name =  base_name+'-'+profile+base_suffix
            full_path = full_path.with_name(name)
            yml_files.append(str(full_path))


        dd = ymlparsers.load([*yml_files, sys_buf.getvalue()])


    return dd


def parse_config(argumentParser=None, args=None):
    """
    This function can be in external use, but it is not intended for.
    This function parses command line arguments.
    Than it parse ini file.
    Command line arguemnts overrides ini file arguments.

    In more detail, command line arguments of the form --key=value are parsed first.
    If exists --config_file it's value is used to search for ini file.
    if --config_file is absent, 'config.yml' is used for ini file.
    If ini file is not found, only command line arguments are used.
    If ini file is found, both arguments are used, while
    command line arguments overrides ini arguments.

    :param argumentParser:
    :param args: if not None, suppresses sys.args
    :return: dict ready to use
    """
    if ymlparsers.HiYaPyCo.jinja2ctx is None:
        raise ValueError("You should call alexber.utils.ymlparsers.initConfig() first")
    sys_d, profiles, white_list, list_ensure, config_file = _parse_sys_args(argumentParser=argumentParser, args=args)
    dd = _parse_yml(sys_d, profiles, config_file)

    #merge all to dd
    general_d = dd.setdefault(conf.GENERAL_KEY, OrderedDict())
    config_d = general_d.setdefault(conf.CONFIG_KEY, OrderedDict())
    config_d[conf.FILE_LEY] = str(config_file)

    general_d[conf.PROFILES_KEY] = profiles
    general_d[conf.WHITE_LIST_KEY] = white_list
    general_d[conf.LIST_ENSURE_KEY] = list_ensure


    return dd
