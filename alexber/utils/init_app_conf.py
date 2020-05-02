"""
`ymlparsers` and `parser` modules serves as Low-Level API for this module.

You may need to install some 3-rd party dependencies, in order to use it, you should have installed first. To do it
run `pip3 install alex-ber-utils[yml]` in order to use it.

Note: **It is mandatory to call `alexber.utils.ymlparsers.initConfig()` function before any method in `init_app_conf`
module**.

Note: **It is mandatory to call `initConfig()` function before any method in `ymlparsers` module**.
"""
import logging
logger = logging.getLogger(__name__)

from collections import OrderedDict, deque
from pathlib import Path
import io as _io
from alexber.utils.parsers import is_empty, safe_eval as _convert, parse_boolean, ArgumentParser, \
    parse_sys_args as uparse_sys_args
try:
    import alexber.utils.ymlparsers as ymlparsers
except ImportError:
    pass



class conf(object):
    """
    See parse_config() function for details.
    """
    GENERAL_KEY = 'general'
    PROFILES_KEY = 'profiles'
    #WHITE_LIST_IMPLICIT_KEY = 'whiteListImplicitely'    #default True
    WHITE_LIST_KEY = 'whiteListSysOverride'
    LIST_ENSURE_KEY ='listEnsure'

    CONFIG_KEY = 'config'
    FILE_LEY = 'file'


class AppConfParser(object):
    def __init__(self, *args, **kwargs):
        self.implicit_convert = kwargs.pop('implicit_convert')
        if self.implicit_convert is None:
            raise ValueError("implicit_convert can't be None")

    basic_parse_sys_args = staticmethod(uparse_sys_args)

    def _parse_yml(self, sys_d, profiles, config_file='config.yml'):
        if ymlparsers.HiYaPyCo.jinja2ctx is None:
            raise ValueError("You should call alexber.utils.ymlparsers.initConfig() first")

        base_full_path = Path(config_file).resolve()  # relative to cwd

        base_suffix = base_full_path.suffix
        base_name = base_full_path.with_suffix("").name

        with _io.StringIO() as sys_buf:
            ymlparsers.safe_dump(sys_d, sys_buf)

            buffersize = len(profiles) + 1  # default_profile
            yml_files = deque(maxlen=buffersize)

            yml_files.append(str(base_full_path))
            full_path = base_full_path

            for profile in profiles:
                name = base_name + '-' + profile + base_suffix
                full_path = full_path.with_name(name)
                yml_files.append(str(full_path))

            dd = ymlparsers.load([*yml_files, sys_buf.getvalue()])

        return dd

    def _parse_white_list_implicitely(self, default_d):
        subvalue = default_d.get(conf.GENERAL_KEY, {})
        value = subvalue.get(conf.WHITE_LIST_KEY, {})

        ret = is_empty(value)
        if ret is None:
            ret = True
        return ret

    def _parse_white_list(self, default_d):
        calc_implicitely = self._parse_white_list_implicitely(default_d)

        if calc_implicitely:
            white_list = [key for key in default_d.keys() if key not in conf.WHITE_LIST_KEY]
            return white_list

        # default_d[conf.GENERAL_KEY][conf.WHITE_LIST_KEY] is not empty
        subvalue = default_d.get(conf.GENERAL_KEY, {})
        white_list = subvalue.get(conf.WHITE_LIST_KEY, {})

        return white_list

    def _is_white_listed(self, white_list_flat_keys, flat_key):
        b = is_empty(white_list_flat_keys)
        if b:
            return True

        for white_list_flat_key in white_list_flat_keys:
            if flat_key.startswith(white_list_flat_key):
                return True
        return False

    def to_convex_map(self, d, white_list_flat_keys=None):
        dd = OrderedDict()

        for flat_key, value in d.items():
            if not ('.' in flat_key and self._is_white_listed(white_list_flat_keys, flat_key)):
                logger.info(f"Skipping key {flat_key}. It doesn't contain dot.")
                continue

            keys = flat_key.split(".")
            length = len(keys)

            inner_d = dd
            for i, part_key in enumerate(keys):
                if i + 1 == length:  # last element
                    inner_d = inner_d.setdefault(part_key, self.mask_value(value))
                else:
                    inner_d = inner_d.setdefault(part_key, OrderedDict())
        return dd

    def merge_list_value_in_dicts(self, flat_d, d, main_key, sub_key):
        if flat_d is None:
            raise TypeError("flat_d can't be None")

        if d is None:
            raise TypeError("d can't be None")

        flat_key = '.'.join([main_key, sub_key])
        flat_value = self._ensure_list(flat_d, flat_key)

        length_flat_value = len(flat_value)

        subvalue = d.get(main_key, {})
        value = subvalue.get(sub_key, {})

        merged_value = value if length_flat_value == 0 else flat_value
        return merged_value

    def _parse_profiles(self, sys_d, default_d):
        profiles = self.merge_list_value_in_dicts(sys_d, default_d, conf.GENERAL_KEY, conf.PROFILES_KEY)
        b = is_empty(profiles)
        if b:
            profiles = []
        return profiles

    def _parse_list_ensure(self, sys_d, default_d):
        list_ensure = self.merge_list_value_in_dicts(sys_d, default_d, conf.GENERAL_KEY, conf.LIST_ENSURE_KEY)

        b = is_empty(list_ensure)
        if not b:
            # we already proceesed profiles, white_list
            # we should process list_ensure
            profiles_flat_key = '.'.join([conf.GENERAL_KEY, conf.PROFILES_KEY])
            list_ensure_flat_key = '.'.join([conf.GENERAL_KEY, conf.LIST_ENSURE_KEY])
            white_list_flat_key = '.'.join([conf.GENERAL_KEY, conf.WHITE_LIST_KEY])

            list_ensure = [flat_key for flat_key in list_ensure \
                           if flat_key not in {profiles_flat_key, list_ensure_flat_key, white_list_flat_key}]
        else:
            list_ensure = []
        return list_ensure

    def _get_white_listed(self, d, white_list_flat_keys):
        b = is_empty(d)
        if b:
            return d
        dd = OrderedDict()

        for flat_key, value in d.items():
            if not ('.' in flat_key and self._is_white_listed(white_list_flat_keys, flat_key)):
                logger.info(f"Skipping key {flat_key}. It doesn't white listed.")
                continue

            dd[flat_key] = value
        return dd

    def _do_ensure_list(self, flat_d, list_ensure):
        b = is_empty(list)
        if b:
            return

        for flat_key in list_ensure:
            flat_value = self._ensure_list(flat_d, flat_key)
            flat_d[flat_key] = flat_value

    def _bool_is_empty(self, value):
        try:
            ret = parse_boolean(value)
            return ret is None
        except ValueError:
            ret = is_empty(value)
        return ret

    def _bool_convert(self, value):
        try:
            ret = parse_boolean(value)
            return ret
        except ValueError:
            ret = _convert(value)
        return ret

    def mask_value(self, value):
        ret = self._bool_convert(value) \
            if self.implicit_convert \
            else value
        return ret

    def _ensure_list(self, flat_d, key):
        def _ensure_list(v):
            value = str(v)
            elements = value.split(",")

            # empty string will become null
            elements = [None if is_empty(value) else value for value in elements]
            ret = [self.mask_value(value) for value in elements]

            return ret

        if flat_d is None:
            flat_d = {}
        val = flat_d.get(key, None)
        b = self._bool_is_empty(val)
        if b:
            if key in flat_d.keys():
                # we have key:None?
                return [val]
            return []
        return _ensure_list(val)

    def _parse_sys_args(self, argumentParser=None, args=None):
        if ymlparsers.HiYaPyCo.jinja2ctx is None:
            raise ValueError("You should call alexber.utils.ymlparsers.initConfig() first")

        params, sys_d0 = self.basic_parse_sys_args(argumentParser, args)
        config_file = params.config_file

        full_path = Path(config_file).resolve()  # relative to cwd

        with ymlparsers.DisableVarSubst():
            default_d = ymlparsers.load([str(full_path)])

        white_list = self._parse_white_list(default_d)
        sys_d = self._get_white_listed(sys_d0, white_list)

        profiles = self._parse_profiles(sys_d, default_d)

        list_ensure = self._parse_list_ensure(sys_d, default_d)

        self._do_ensure_list(sys_d, list_ensure)

        dd = self.to_convex_map(sys_d)
        return dd, profiles, white_list, list_ensure, full_path

    def parse_config(self, argumentParser=None, args=None):

        sys_d, profiles, white_list, list_ensure, config_file = self._parse_sys_args(argumentParser=argumentParser,
                                                                                     args=args)
        dd = self._parse_yml(sys_d, profiles, config_file)

        # merge all to dd
        general_d = dd.setdefault(conf.GENERAL_KEY, OrderedDict())
        config_d = general_d.setdefault(conf.CONFIG_KEY, OrderedDict())
        config_d[conf.FILE_LEY] = str(config_file)

        general_d[conf.PROFILES_KEY] = profiles
        general_d[conf.WHITE_LIST_KEY] = white_list
        general_d[conf.LIST_ENSURE_KEY] = list_ensure

        general_d = dd.setdefault(conf.GENERAL_KEY, OrderedDict())
        config_d = general_d.setdefault(conf.CONFIG_KEY, OrderedDict())
        config_d[conf.FILE_LEY] = str(config_file)

        general_d[conf.PROFILES_KEY] = profiles
        general_d[conf.WHITE_LIST_KEY] = white_list
        general_d[conf.LIST_ENSURE_KEY] = list_ensure
        return dd

def _create_default_parser(**kwargs):
    if default_parser_cls is None:
        raise ValueError("You should call initConfig() first")

    implicit_convert = kwargs['implicit_convert']
    if implicit_convert is None:
        implicit_convert=default_parser_kwargs['implicit_convert']

    kwargs = {
        **default_parser_kwargs,
        'implicit_convert': implicit_convert,

    }
    parser = default_parser_cls(**kwargs)
    return parser

def mask_value(value, implicit_convert=None):
    """
    If implicit_convert is True,  or it is None, but implicit_convert=True was supplied to initConfig() method,
    then we assume Python built-in types, including bool, and we're converting it to appropriate type.
    If implicit_convert is False, or it is None, but False=True was supplied to initConfig() method,
    then use value as is.

    Bool values are case-insensitive.

    Note: Before calling this method, please ensure that you've called initConfig() method first.

    :param value: str to ccnvert
    :param implicit_convert: if none, than value that was passed to initConfig() is used (default).
                             if True value attempt to convert value to appropriate type will be done,
                             if False value will be used as is. See mask_value() function.
    :return:
    """
    if default_parser_cls is None:
        raise ValueError("You should call initConfig() first")

    parser = _create_default_parser(**{'implicit_convert': implicit_convert})
    ret = parser.mask_value(value)
    return ret


def to_convex_map(d, white_list_flat_keys=None, implicit_convert=None):
    """
    This method receives dictionary with 'flat keys', it has simple key:value structure
    where value can't another dictionary.
    It will return dictionary of dictionaries with natural key mapping (see bellow),
    optionally entries will be filtered out according to white_list_flat_keys and
    optionally value will be implicitly converted to appropriate type.

    Note: Before calling this method, please ensure that you've called initConfig() method first.

    In order to simulate dictionary of dictionaries 'flat keys' compose key from outer dict with key from inner dict
    separated with dot.
    For example, 'general.profiles' 'flat key' corresponds to convex map with 'general' key with dictionary as value
    that have one of the keys 'profiles' with corresponding value.

    if white_list_flat_keys is not None, it will be used to filter out entries from d.
    If implicit_convert is True,  or it is None, but implicit_convert=True was supplied to initConfig() method,
    it will be used to convert value to appropriate type. See mask_value() function.
    If implicit_convert is False, or it is None, but False=True was supplied to initConfig() method,
    the value will be used as is.

    :param d: dict with flat keys
    :param white_list_flat_keys: Optional. if present, only keys that start with one of the elements listed here
                                            will be considered.
    :param implicit_convert: if none, than value that was passed to initConfig() is used (default).
                             if True value attempt to convert value to appropriate type will be done,
                             if False value will be used as is. See mask_value() function.
    :return: convex map with optionally filtered entrys
    """
    if default_parser_cls is None:
        raise ValueError("You should call initConfig() first")

    parser = _create_default_parser(**{'implicit_convert': implicit_convert})
    dd = parser.to_convex_map(d, white_list_flat_keys)
    return dd



def merge_list_value_in_dicts(flat_d, d, main_key, sub_key, implicit_convert=None):
    """
    This method merge value of 2 dicts. This value represents list of values.

    Note: Before calling this method, please ensure that you've called initConfig() method first.

    Value from flat_d is roughly obtained by flat_d[main_key+'.'+sub_key].
    Value from d is roughly obtained by d[main_key][sub_key].

    If value (or intermediate value) is not found empty dict is used.

    This method assumes that flat_d value contain str that represent list (comma-delimited).
    This method assumes that d[main_key] contains dict.
    implicit_convert is applied only for flat_d.


    If implicit_convert is True,  or it is None, but implicit_convert=True was supplied to initConfig() method,
    then this method implicitly converts every element inside list to Python built-in type. See mask_value() function.
    If implicit_convert is False, or it is None, but False=True was supplied to initConfig() method,
    then use value as is.


    :param flat_d: flat dictionoray, usually one that was created from parsing system args.
    :param d: dictionary of dictionaries,  usually one that was created from parsing YAML file.
    :param main_key: d[main_key] is absent or dict.
    :param sub_key: d[main_key][sub_key] is absent or list.
    :param implicit_convert: if none, than value that was passed to initConfig() is used (default).
                             if True value attempt to convert value to appropriate type will be done,
                             if False value will be used as is. See mask_value() function.
    :return: merged convreted value, typically one from flat_d, if empty than from d
    """
    if default_parser_cls is None:
        raise ValueError("You should call initConfig() first")

    parser = _create_default_parser(**{'implicit_convert': implicit_convert})
    merged_value = parser.merge_list_value_in_dicts(flat_d, d, main_key, sub_key)
    return merged_value

def parse_config(argumentParser=None, args=None, implicit_convert=None):
    """
    This is the main function of the module.

    Note: Before calling this method, please ensure that you've called initConfig() method first.

    Note: Before calling this method, please ensure that you've called alexber.utils.ymlparsers.initConfig()
    method first.

    This function parses command line arguments first.
    Than it parse yml files.
    Command line arguments overrides yml files arguments.

    Parameters of yml files we always try to convert on best-effort basses.
    Parameters of system args we try convert according to implicit_convert param (see below).

    In more detail, command line arguments of the form --key=value are parsed first.
    If exists --config_file it's value is used to search for yml file.
    if --config_file is absent, 'config.yml' is used for yml file.
    If yml file is not found, only command line arguments are used.
    If yml file is found, both arguments are used, while
    command line arguments overrides yml arguments.

    --general.profiles or appropriate key in default yml file is used to find 'profiles'.
    Let suppose, that --config_file is resolved to config.yml.
    If 'profiles' is not empty, than it will be used to calculate filenames
    that will be used to override default yml file.
    Let suppose, 'profiles' resolved to ['dev', 'local']. Than first config.yml
    will be loaded, than it will be overridden with config-dev.yml, than
    it will be overridden with config-local.yml.
    At last, it will be overridden with system args.
    This entry can be always be overridden with system args.

    general.whiteListSysOverride key in yml file is optional.
    If not provided, than any key that exists in the default yml file can be overridden
    with system args.
    If provided, than only key that start with one of the key provided here can be used
    to override entrys with system args.
    This entry can't be overridden with system args.

    --general.listEnsure or appropriate key in default yml file is used to instruct that
    listed key should be interpreted as comma-delimited list when is used to override
    entrys with system args.
    This entry can be always be overridden with system args.

    general.config.file is key that is used in returned dict that points to default yml file.

    If implicit_convert is True,  or it is None, but implicit_convert=True was supplied to initConfig() method,
    then for system args we assume Python built-in types, including bool, and we're converting it to appropriate type.
    If implicit_convert is False, or it is None, but False=True was supplied to initConfig() method,
    then system args we use value as is.


    :param argumentParser:
    :param args: if not None, suppresses sys.args
    :param implicit_convert: if none, than value that was passed to initConfig() is used (default).
                             if True value attempt to convert value from system args to appropriate type will be done,
                             if False value from system args will be used as is. See mask_value() function.
    :return: dict ready to use
    """
    if default_parser_cls is None:
        raise ValueError("You should call initConfig() first")

    if ymlparsers.HiYaPyCo.jinja2ctx is None:
        raise ValueError("You should call alexber.utils.ymlparsers.initConfig() first")

    parser = _create_default_parser(**{'implicit_convert': implicit_convert})
    dd = parser.parse_config(argumentParser=argumentParser, args=args)
    return dd


default_parser_cls = None
default_parser_kwargs = None

def initConfig(**kwargs):
    """
    This method should be called prior any call to another function in this module.
    It is indented to be called in the MainThread.
    This method can be call with empty params.

    :param default_parser_cls: Optional.
                Default values is: AppConfParser
    :param default_parser_kwargs: this params will be used as default values in default_parser_cls.__init__() function.
                Default values are
                      'implicit_convert':True,
                This means, by default:
                    We're converting values using mask_value() function.
    :return:
    """
    default_parser_cls_p = kwargs.get('default_parser_cls', None)
    if default_parser_cls_p is None:
        default_parser_cls_p = AppConfParser
    global default_parser_cls
    default_parser_cls = default_parser_cls_p

    default_parser_kwargs_p = kwargs.get('default_parser_kwargs', {})
    default_parser_kwargs_p = {
        'implicit_convert':True,
        **default_parser_kwargs_p}
    global default_parser_kwargs
    default_parser_kwargs = default_parser_kwargs_p
