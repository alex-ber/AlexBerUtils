import logging
from collections import OrderedDict
from collections.abc import Mapping
import pytest
import copy

logger = logging.getLogger(__name__)
from alexber.utils.init_app_conf import mask_value, merge_list_value_in_dicts, to_convex_map, \
    parse_config
import alexber.utils.init_app_conf as init_app_conf
from alexber.utils.init_app_conf import _create_default_parser, AppConfParser
from alexber.utils.parsers import is_empty
from tests.utils.ymlparsers_test import ymlparsersSetup, ymlparsersCleanup, exp_config_d
from importlib.resources import path

def create_default_parser(implicit_convert=None):
    parser=_create_default_parser(**{'implicit_convert': implicit_convert})
    return parser

def _reset_initappconf():
    init_app_conf.default_parser_cls  = None
    init_app_conf.default_parser_kwargs = None



@pytest.fixture
def initappconfFixture(mocker):
    _reset_initappconf()

    init_app_conf.initConfig()
    yield None
    _reset_initappconf()

@pytest.fixture
def initappconfFalseFixture(mocker):
    _reset_initappconf()

    init_app_conf.initConfig(**{'default_parser_kwargs': {'implicit_convert': False}})
    yield None
    _reset_initappconf()



class MyAppConfParser(AppConfParser):
    pass

def test_mask_value_default_as_none(request, initappconfFalseFixture):
    logger.info(f'{request._pyfuncitem.name}()')

    with pytest.raises(ValueError, match='None'):
        init_app_conf.initConfig(**{'default_parser_kwargs': {'implicit_convert': None}})
        mask_value('0.1')

def test_initConfig_default_parser_cls_str(request, initappconfFalseFixture):
    logger.info(f'{request._pyfuncitem.name}()')

    class_name = '.'.join([__name__, MyAppConfParser.__name__])
    init_app_conf.initConfig(**{'default_parser_cls': class_name})

    pytest.assume(init_app_conf.default_parser_cls == MyAppConfParser)



@pytest.mark.parametrize(
    'value, exp_value, exp_type',

    [
        ('John', 'John', str),
        ('1000', '1000', str),
        ('0.1', '0.1', str),
        ('None', 'None', str),
        ('True', 'True', str),
        ('False', 'False', str),


    ]
)
def test_mask_value_without_implicit_convert(request, initappconfFixture, value, exp_value, exp_type):
    logger.info(f'{request._pyfuncitem.name}()')


    result = mask_value(value, implicit_convert=False)
    type_result = type(result)
    pytest.assume(exp_value == result)
    pytest.assume(exp_type == type_result)


@pytest.mark.parametrize(
     'value, exp_value, exp_type',

    [
        ('John', 'John', str),
        ('alexber.utils.players.ConstantPlayer', 'alexber.utils.players.ConstantPlayer', str),
        ('1000', 1000, int),
        ('0.1', 0.1, float),
        ('0.0', 0.0, float),
        ('-0.0', 0.0, float),
        ('-5', -5, int),
        ('None', None, type(None)),
        ('True', True, bool),
        ('False', False, bool),



    ]
)
def test_mask_value(request, initappconfFixture, value, exp_value, exp_type):
    logger.info(f'{request._pyfuncitem.name}()')


    result = mask_value(value)
    type_result = type(result)
    pytest.assume(exp_value == result)
    pytest.assume(exp_type == type_result)

def test_mask_value_default_as_true(request, initappconfFixture):
    logger.info(f'{request._pyfuncitem.name}()')

    value = '0.1'
    exp_value = 0.1
    exp_type = float

    result = mask_value(value)  #implicit_convert=None as True
    type_result = type(result)
    pytest.assume(exp_value == result)
    pytest.assume(exp_type == type_result)

def test_mask_value_default_as_false(request, initappconfFalseFixture):
    logger.info(f'{request._pyfuncitem.name}()')

    value = '0.1'
    exp_value = '0.1'
    exp_type = str

    result = mask_value(value)  #implicit_convert=None as False
    type_result = type(result)
    pytest.assume(exp_value == result)
    pytest.assume(exp_type == type_result)




def _calc_exp_ports(ports):
    if ports is None:
        return None
    arr = str(ports).split(',')
    ret=[mask_value(port) for port in arr]
    return ret


@pytest.mark.parametrize(
     'value, exp_value',

    [
         (10000, [10000]),
        ('10000', [10000]),
        ('10000,', [10000, None]),
        ('10000,10001',  [10000,10001]),
        ('10000,10001,', [10000,10001, None]),
        ('10000,,10003', [10000,None, 10003]),

        (True, [True]),
        (False, [False]),
        ('True', [True]),
        ('False', [False]),
        ('False,True,False', [False,True,False]),

        ([False], [False]), #Not_Supported
        ([None], [None]), #Not_Supported
        (['False'], [False]), #Not_Supported
        (['None'], ['None']), #Not_Supported

        ([None], ["innervalue"]),
        ([''], ["innervalue"]),
    ]
)
def test_merge_list_value_in_dicts(request, initappconfFixture, value, exp_value):
    logger.info(f'{request._pyfuncitem.name}()')
    if type(value) is list:
        logger.debug(f"Complex types (such as list) are not supported.")
        return

    flat_d = OrderedDict()
    flat_d['app.ports'] = value
    d = OrderedDict()
    inner_value = ["innervalue"]
    d.setdefault('app', OrderedDict()).setdefault('ports', inner_value)

    ret = merge_list_value_in_dicts(flat_d, d, 'app', 'ports', implicit_convert=True)
    f_value = flat_d['app.ports']
    i_value = d['app']['ports']

    pytest.assume(value==f_value)
    pytest.assume(inner_value==i_value)
    pytest.assume(exp_value==ret)

def test_merge_list_value_in_dicts_absent(request, initappconfFixture):
    logger.info(f'{request._pyfuncitem.name}()')
    flat_d = OrderedDict()
    d = OrderedDict()
    ret = merge_list_value_in_dicts(flat_d, d, 'general', 'profiles')
    b = is_empty(ret)
    pytest.assume(b)

def test_merge_list_value_in_dicts_default_as_true(request, initappconfFixture):
    logger.info(f'{request._pyfuncitem.name}()')

    flat_d = {'app.ports': 10000}
    d = {'app': {'ports': ["innervalue"]}}
    inner_value = ["innervalue"]

    ret = merge_list_value_in_dicts(flat_d, d, 'app', 'ports')
    f_value = flat_d['app.ports']
    i_value = d['app']['ports']

    pytest.assume(10000==f_value)
    pytest.assume(inner_value==i_value)
    pytest.assume([10000]==ret)


def test_merge_list_value_in_dicts_default_as_false(request, initappconfFalseFixture):
    logger.info(f'{request._pyfuncitem.name}()')

    flat_d = {'app.ports': 10000}
    d = {'app': {'ports': ["innervalue"]}}
    inner_value = ["innervalue"]

    ret = merge_list_value_in_dicts(flat_d, d, 'app', 'ports')
    f_value = flat_d['app.ports']
    i_value = d['app']['ports']

    pytest.assume(10000==f_value)
    pytest.assume(inner_value==i_value)
    pytest.assume(['10000']==ret)

def test_merge_list_value_in_dicts_false(request, initappconfFixture):
    logger.info(f'{request._pyfuncitem.name}()')

    flat_d = {'app.ports': 10000}
    d = {'app': {'ports': ["innervalue"]}}
    inner_value = ["innervalue"]

    ret = merge_list_value_in_dicts(flat_d, d, 'app', 'ports', implicit_convert=False)
    f_value = flat_d['app.ports']
    i_value = d['app']['ports']

    pytest.assume(10000==f_value)
    pytest.assume(inner_value==i_value)
    pytest.assume(['10000']==ret)





def check_exp_sys(exp_d, default_d):
    general_d = default_d.get('general', None)
    assert general_d is not None
    app_d = default_d.get('app', None)
    assert app_d is not None
    app_str_d = app_d.get('as_str', None)
    assert app_str_d is not None

    exp_val = exp_d['general.profiles']
    val = general_d.get('profiles', None)
    pytest.assume(exp_val==val)

    for flat_key, exp_val in exp_d.items():
        if flat_key.startswith("general"):
            continue
        arr = flat_key.split('.')
        key = arr[-1]
        dd = app_str_d if 'as_str' in flat_key else app_d
        val = dd.get(key, None)
        pytest.assume(exp_val == val)


def test_to_convex_map_intented(request, mocker, initappconfFixture):
    logger.info(f'{request._pyfuncitem.name}()')
    exp_d = {'general.profiles': ["dev"],
             'app.white_list': ['one', 'two', 'three'],
             'app.as_str.alt_white_list': [10],
             'app.num_scalar': 5,
             'app.none_scalar': None,
             'app.str_scalar': 'Hello',
             'app.as_str.bool1_scalar': True,
             'app.as_str.bool2_scalar': False,

             'app.as_str.list_bool': [True, False],
             'app.as_str.list_bool_true': [True],
             'app.as_str.list_bool_false': [False],
             'app.as_str.list_none': [None],
             'app.as_str.list_empty_str': [''],
             }

    sys_d = {'general.profiles': "dev",
             'app.white_list': 'one,two,three',
             'app.as_str.alt_white_list': '10',
             'app.num_scalar': 5,
             'app.none_scalar': None,
             'app.str_scalar': 'Hello',
             'app.as_str.bool1_scalar': 'True',
             'app.as_str.bool2_scalar': 'False',

             'app.as_str.list_bool': 'True,False',
             'app.as_str.list_bool_true': True,
             'app.as_str.list_bool_false': False,
             'app.as_str.list_none': None,
             'app.as_str.list_empty_str': '',
             }
    list_ensure = [key for key in sys_d.keys() if 'scalar' not in key]
    create_default_parser()._do_ensure_list(sys_d, list_ensure)
    default_d = to_convex_map(sys_d)

    check_exp_sys(exp_d, default_d)



def test_to_convex_map_whitelist(request, mocker, initappconfFixture):
    logger.info(f'{request._pyfuncitem.name}()')
    exp_d = {'general.profiles': ["dev"],
             'app.as_str.alt_white_list': [10],
             'app.as_str.bool1_scalar': True,
             }

    sys_d = {'general.profiles': "dev",
             'app.white_list': 'one,two,three',
             'app.as_str.alt_white_list': '10',
             'app.as_str.bool1_scalar': 'True',
             'db.unused': 'localhost',
             }
    list_ensure = [key for key in sys_d.keys() if 'scalar' not in key]
    create_default_parser()._do_ensure_list(sys_d, list_ensure)
    default_d = to_convex_map(sys_d, white_list_flat_keys=['general', 'app.as_str'], implicit_convert=True)

    check_exp_sys(exp_d, default_d)

def test_to_convex_map_whitelist_implicit_convert_false(request, mocker, initappconfFalseFixture):
    logger.info(f'{request._pyfuncitem.name}()')
    exp_d = {'general.profiles': ["dev"],
             'app.as_str.alt_white_list': ['10'],
             'app.as_str.bool1_scalar': 'True',
             }

    sys_d = {'general.profiles': "dev",
             'app.white_list': 'one,two,three',
             'app.as_str.alt_white_list': '10',
             'app.as_str.bool1_scalar': 'True',
             'db.unused': 'localhost',
             }
    list_ensure = [key for key in sys_d.keys() if 'scalar' not in key]
    create_default_parser()._do_ensure_list(sys_d, list_ensure)
    default_d = to_convex_map(sys_d, white_list_flat_keys=['general', 'app.as_str'], implicit_convert=False)

    check_exp_sys(exp_d, default_d)

def test_to_convex_map_whitelist_implicit_convert_false_default_as_false(request, mocker, initappconfFalseFixture):
    logger.info(f'{request._pyfuncitem.name}()')
    exp_d = {'general.profiles': ["dev"],
             'app.as_str.alt_white_list': ['10'],
             'app.as_str.bool1_scalar': 'True',
             }

    sys_d = {'general.profiles': "dev",
             'app.white_list': 'one,two,three',
             'app.as_str.alt_white_list': '10',
             'app.as_str.bool1_scalar': 'True',
             'db.unused': 'localhost',
             }
    list_ensure = [key for key in sys_d.keys() if 'scalar' not in key]
    create_default_parser()._do_ensure_list(sys_d, list_ensure)
    default_d = to_convex_map(sys_d, white_list_flat_keys=['general', 'app.as_str'], implicit_convert=False)

    check_exp_sys(exp_d, default_d)

def test_to_convex_map_whitelist_default_as_true(request, mocker, initappconfFixture):
    logger.info(f'{request._pyfuncitem.name}()')
    exp_d = {'general.profiles': ["dev"],
             'app.as_str.alt_white_list': [10],
             'app.as_str.bool1_scalar': True,
             }

    sys_d = {'general.profiles': "dev",
             'app.white_list': 'one,two,three',
             'app.as_str.alt_white_list': '10',
             'app.as_str.bool1_scalar': 'True',
             'db.unused': 'localhost',
             }
    list_ensure = [key for key in sys_d.keys() if 'scalar' not in key]
    create_default_parser()._do_ensure_list(sys_d, list_ensure)
    default_d = to_convex_map(sys_d, white_list_flat_keys=['general', 'app.as_str'])

    check_exp_sys(exp_d, default_d)

@pytest.mark.parametrize(
     'exp_profiles, sys_d, default_d',
    [
        (['dev', 'local'], {'general.profiles': "dev,local"}, {'general': {'profiles': ["dev"]}}),
        (['prod'], {'general.profiles': "prod"}, {'general': {'profiles': ["dev"]}}),
        (['dev'], {}, {'general': {'profiles': ["dev"]}}),
        (['prod'], {'general.profiles': "prod"}, {}),
        (['prod'], {'general.profiles': "prod"}, {'general': {'profiles': None}}),
        (['prod'], {'general.profiles': "prod"}, {'general': {'profiles': [""]}}),
        ([None], {'general.profiles': None}, {'general': {'profiles': ["dev"]}}),
        ([""], {'general.profiles': ""}, {'general': {'profiles': ["dev"]}}),
        ([], {'general.log': "something"}, {'general': {'log': {'root': 'INFO'}}}), #it should be list, not dict
    ]
)
def test_parse_profiles(request, mocker, initappconfFixture, exp_profiles, sys_d, default_d):
    logger.info(f'{request._pyfuncitem.name}()')

    profiles = create_default_parser()._parse_profiles(sys_d, default_d)
    pytest.assume(exp_profiles == profiles)


@pytest.mark.parametrize(
     'exp_value, default_d',

    [
        (False, {'general': {'whiteListSysOverride': ["general,app"]}}),
        (False, {'general': {'whiteListSysOverride': ["general"]}}),
        (True, {'general': {'whiteListSysOverride': []}}),
        (False, {'general': {'whiteListSysOverride': ['']}}),
        (False, {'general': {'whiteListSysOverride': [None]}}),
        (True, {'general': {'whiteListSysOverride': None}}),
    ]

)

def test_parse_white_list_implicitely(request, mocker, initappconfFixture, exp_value, default_d):
    logger.info(f'{request._pyfuncitem.name}()')
    result = create_default_parser()._parse_white_list_implicitely(default_d)
    pytest.assume(exp_value==result)




@pytest.mark.parametrize(
     'default_d',

    [
        {'general': {'profiles': ["dev"]}, 'some_unique_key': 'value'},
        {'general': {'profiles': ["dev"], 'whiteListSysOverride':None}, 'some_unique_key': 'value'},
        {'general': {'profiles': ["dev"], 'whiteListSysOverride':[]}, 'some_unique_key': 'value'},
    ]

)

def test_parse_white_list_implicit(request, mocker, initappconfFixture, default_d):
    logger.info(f'{request._pyfuncitem.name}()')
    #whiteListSysOverride

    white_list = create_default_parser()._parse_white_list(default_d)
    length = 0 if white_list is None else len(white_list)
    pytest.assume(length==2)
    pytest.assume('general' in white_list)
    pytest.assume('some_unique_key' in white_list)

def test_parse_white_list_explicit(request, mocker, initappconfFixture):
    logger.info(f'{request._pyfuncitem.name}()')
    #whiteListSysOverride
    default_d={'general': {'profiles': ["dev"], 'whiteListSysOverride': ['general']},
               'app': {
                   'ignoredKey': 1,
               }}

    white_list = create_default_parser()._parse_white_list(default_d)
    length = 0 if white_list is None else len(white_list)
    pytest.assume(length==1)
    pytest.assume('general' in white_list)
    pytest.assume('app' not in white_list)

def test_parse_white_list_explicit2(request, initappconfFixture, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    #whiteListSysOverride

    default_d={'general': {'profiles': ["dev"],
                           'log': None,
                           'whiteListSysOverride': ['general', 'app']},
               'app': {
                  'ignoredKey': 1,
                }
    }

    white_list = create_default_parser()._parse_white_list(default_d)
    length = 0 if white_list is None else len(white_list)
    pytest.assume(length==2)
    pytest.assume('general' in white_list)
    pytest.assume('app' in white_list)


def test_parse_list_ensure(request, mocker, initappconfFixture):
    logger.info(f'{request._pyfuncitem.name}()')
    sys_d = {}
    default_d={'general': {'listEnsure': ['general.profiles', 'general.listEnsure',
                                          'general.listEnsure', 'general.whiteListSysOverride',
                                          'app.check_list']}}

    list_ensure = create_default_parser()._parse_list_ensure(sys_d, default_d)
    length = 0 if list_ensure is None else len(list_ensure)
    pytest.assume(length==1)
    pytest.assume('app.check_list' in list_ensure)


def test_parse_list_ensure_empty(request, mocker, initappconfFixture):
    logger.info(f'{request._pyfuncitem.name}()')
    sys_d = {}
    default_d={'general': {'listEnsure': []}}

    list_ensure = create_default_parser()._parse_list_ensure(sys_d, default_d)
    length = 0 if list_ensure is None else len(list_ensure)
    pytest.assume(length==0)

def test_parse_list_ensure2(request, mocker, initappconfFixture):
    logger.info(f'{request._pyfuncitem.name}()')
    sys_d = {'general.listEnsure':'general.profiles,app.white_list'}

    default_d={'general': {'listEnsure': ['general.profiles', 'general.listEnsure',
                                          'general.listEnsure', 'general.whiteListSysOverride',
                                          'app.check_list']}}

    list_ensure = create_default_parser()._parse_list_ensure(sys_d, default_d)
    length = 0 if list_ensure is None else len(list_ensure)
    pytest.assume(length==1)
    pytest.assume('app.white_list' in list_ensure)

def test_get_white_listed_empty_src_d(request, mocker, initappconfFixture):
    logger.info(f'{request._pyfuncitem.name}()')
    exp_d = {}
    d = create_default_parser()._get_white_listed({}, {'a':'b'})
    pytest.assume(exp_d==d)

def test_get_white_listed_empty_white_list_flat_keys(request, mocker, initappconfFixture):
    logger.info(f'{request._pyfuncitem.name}()')
    exp_d = {'general.profiles': "dev",
             'app.white_list': 'one,two,three',
             'app.as_str.alt_white_list': '10',
             'app.as_str.bool1_scalar': 'True',
             'db.unused': 'localhost',
             }

    sys_d = {'general.profiles': "dev",
             'app.white_list': 'one,two,three',
             'app.as_str.alt_white_list': '10',
             'app.as_str.bool1_scalar': 'True',
             'db.unused': 'localhost',
             }

    d = create_default_parser()._get_white_listed(sys_d, None)
    pytest.assume(exp_d==d)

def test_get_white_listed(request, mocker, initappconfFixture):
    logger.info(f'{request._pyfuncitem.name}()')
    exp_d = {'general.profiles': "dev",
             'app.white_list': 'one,two,three',
             'app.as_str.alt_white_list': '10',
             'app.as_str.bool1_scalar': 'True',
             }

    sys_d = {'general.profiles': "dev",
             'app.white_list': 'one,two,three',
             'app.as_str.alt_white_list': '10',
             'app.as_str.bool1_scalar': 'True',
             'db.unused': 'localhost',
             }

    white_list_flat_keys = ['app', 'general']

    d = create_default_parser()._get_white_listed(sys_d, white_list_flat_keys)
    pytest.assume(exp_d==d)

@pytest.mark.yml
def test_parse_sys_args(request, mocker, ymlparsersSetup, ymlparsersCleanup, initappconfFixture):
    logger.info(f'{request._pyfuncitem.name}()')

    expdd = {
        'general': {'profiles': ['dev'],  # list
                    'log': {
                        'formatters': {
                            'detail': {
                                'format': '%(message)s'
                            }
                        },
                        'root': {
                            'level': 20  # logging.INFO
                        }
                    },
                    'listEnsure': ['app.white_list','app.alt_white_list']
                    },  # list
        'app': {'host_name': 'yahoo.com',
                'portal': 'reddit.com',     #this will be proceses because of implicit general.whiteListSysOverride
                'white_list': ['alpha', 'betha', 'gamma'],
                'alt_white_list': [],  # not part of sys.args, so value from config.yml will be ignored
                }
    }

    pck = '.'.join(['tests_data', __package__, 'initappconf'])
    with path(pck, 'config.yml') as full_path:
        argsv = f'--general.config.file={full_path} '\
                '--general.profiles=dev ' \
                '--general.log.formatters.detail.format=%(message)s ' \
                '--general.log.root.level=20 ' \
                '--general.listEnsure=app.white_list,app.alt_white_list ' \
                '--app.host_name=yahoo.com ' \
                '--app.portal=reddit.com ' \
                '--app.white_list=alpha,betha,gamma ' \
            .split()


        dd, profiles, _, list_ensure, _ = create_default_parser()._parse_sys_args(None, argsv)
        dd['general']['profiles'] = profiles
        dd['general']['listEnsure'] = list_ensure

        pytest.assume(expdd==dd)

@pytest.mark.yml
def test_parse_yml(request, mocker, ymlparsersSetup, ymlparsersCleanup, initappconfFixture):
    logger.info(f'{request._pyfuncitem.name}()')

    expdd = {
        'general': {'profiles': ['dev'],  # list
                    'log': {
                        'version': 1,
                        'disable_existing_loggers': False,
                        'formatters': {
                            'brief': {
                                'format': '%(message)s'
                            },
                            'detail': {
                                'format': '%(asctime)-15s %(levelname)s [%(name)s.%(funcName)s] %(message)s',
                                'datefmt': '%Y-%m-%d %H:%M:%S'
                            },
                        },
                        'root': {
                            'level': 'INFO'  # logging.INFO
                        }
                    },
                    'listEnsure': ['app.white_list', 'app.alt_white_list']
                    },  # list
        'app': {'host_name': 'yahoo.com',
                'portal': 'reddit.com',  # this will be proceses because of implicit general.whiteListSysOverride
                'news': 'cnn.com',
                'white_list': ['alpha', 'betha', 'gamma'],
                'alt_white_list': [100, 10.0],  #value from config.yml will be parsed
                }
    }



    sys_d = {
        'general': {'profiles': ['dev'],
                    'listEnsure': ['app.white_list','app.alt_white_list']
                    },
        'app': {'host_name': 'yahoo.com',
                'portal': 'reddit.com',     #this will be proceses because of implicit general.whiteListSysOverride
                'white_list': ['alpha', 'betha', 'gamma'],
                }
    }

    pck = '.'.join(['tests_data', __package__, 'initappconf'])
    with path(pck, 'config.yml') as full_path:
        dd = create_default_parser()._parse_yml(sys_d, ['dev'], config_file=full_path)
        del dd['general']['log']['handlers']
        del dd['general']['log']['root']['handlers']
        pytest.assume(expdd==dd)

@pytest.mark.yml
def test_parse_config_true(request, mocker, ymlparsersSetup, ymlparsersCleanup, initappconfFixture):
    logger.info(f'{request._pyfuncitem.name}()')

    expdd = {
        'general': {'profiles': ['dev'],
                    'log': {
                        'version': 1,
                        'disable_existing_loggers': False,
                        'formatters': {
                            'brief': {
                                'format': '%(message)s'
                            },
                            'detail': {
                                'format': '%(asctime)-15s %(levelname)s [%(name)s.%(funcName)s] %(message)s',
                                'datefmt': '%Y-%m-%d %H:%M:%S'
                            },
                        },
                        'root': {
                            'level': 'INFO'  # logging.INFO
                        }
                    },
                    'config':{
                        'file' : None   #will be be populated below
                    },
                    'whiteListSysOverride': ['general', 'app'],   #implictely populated
                    'listEnsure': [],   #profile can be overridden in sysargs, regargless,  \
                                        # we don't override any (other) list value from sysargs
                    },  # list
        'app': {'host_name': 'yahoo.com',
                'news': 'cnn.com',
                'portal': 'reddit.com',     #this will be proceses because of implicit general.whiteListSysOverride
                'white_list': ['gamma', 'alpha', 'betha'],
                'alt_white_list': [100, 10.0],
                }
    }

    pck = '.'.join(['tests_data', __package__, 'initappconf'])

    with path(pck, 'config.yml') as full_path:
        expdd['general']['config']['file'] = str(full_path)

        argsv = f'--general.config.file={full_path} '\
                '--app.portal=reddit.com ' \
                '--general.profiles=dev ' \
            .split()


        dd = parse_config(None, argsv)
        del dd['general']['log']['handlers']
        del dd['general']['log']['root']['handlers']

        pytest.assume(expdd==dd)

@pytest.mark.yml
def test_parse_config_explicit_white_list(request, mocker, ymlparsersSetup, ymlparsersCleanup, initappconfFixture):
    logger.info(f'{request._pyfuncitem.name}()')

    expdd = {
        'general': {'profiles': [],
                    'log': {
                        'version': 1,
                        'disable_existing_loggers': False,
                        'formatters': {
                            'brief': {
                                'format': '%(message)s'
                            },
                            'detail': {
                                'format': '%(asctime)-15s %(levelname)s [%(name)s.%(funcName)s] %(message)s',
                                'datefmt': '%Y-%m-%d %H:%M:%S'
                            },
                        },
                        'root': {
                            'level': 'DEBUG'
                        }
                    },
                    'config':{
                        'file' : None   #will be be populated below
                    },
                    'whiteListSysOverride': ['app.host_name'],   #explicetly populated
                    'listEnsure': [],   #whiteListSysOverride can be overridden in sysargs, regargless,  \
                                        # we don't override any (other) list value from sysargs
                    },  # list
        'app': {'host_name': '10.20.40.60',
                'news': 'cnn.com',
                #'portal': 'reddit.com',     #this will NOT be proceses because of explicit general.whiteListSysOverride
                'white_list': ['gamma', 'alpha', 'betha'],
                'alt_white_list': [100, 10.0],
                }
    }

    pck = '.'.join(['tests_data', __package__, 'initappconf'])

    with path(pck, 'confige.yml') as full_path:
        expdd['general']['config']['file'] = str(full_path)

        #app.host_name is in general.whiteListSysOverridem it will be process
        #app.portal and last line will be ignored
        argsv = f'--general.config.file={full_path} '\
                '--app.portal=reddit.com ' \
                '--app.host_name=10.20.40.60 ' \
                '10.20.40.60:8082 ' \
            .split()


        dd = parse_config(None, argsv)
        del dd['general']['log']['handlers']
        del dd['general']['log']['root']['handlers']

        pytest.assume(expdd==dd)

@pytest.mark.yml
def test_parse_config_false(request, mocker, ymlparsersSetup, ymlparsersCleanup, initappconfFixture):
    logger.info(f'{request._pyfuncitem.name}()')
    pck = '.'.join(['tests_data', __package__, 'initappconf'])
    exp_disable_existing_loggers = 'False'

    with path(pck, 'config.yml') as full_path:
        argsv = f'--general.config.file={full_path} ' \
                '--general.profiles=dev ' \
                f'--general.log.disable_existing_loggers={exp_disable_existing_loggers} ' \
            .split()

        dd = parse_config(None, argsv, implicit_convert=False)
        disable_existing_loggers = dd['general']['log']['disable_existing_loggers']
        pytest.assume(exp_disable_existing_loggers==disable_existing_loggers)

@pytest.mark.yml
def test_parse_config_default_as_false(request, mocker, ymlparsersSetup, ymlparsersCleanup, initappconfFalseFixture):
    logger.info(f'{request._pyfuncitem.name}()')
    pck = '.'.join(['tests_data', __package__, 'initappconf'])
    exp_disable_existing_loggers = 'False'

    with path(pck, 'config.yml') as full_path:
        argsv = f'--general.config.file={full_path} ' \
                '--general.profiles=dev ' \
                f'--general.log.disable_existing_loggers={exp_disable_existing_loggers} ' \
            .split()

        dd = parse_config(None, argsv)
        disable_existing_loggers = dd['general']['log']['disable_existing_loggers']
        pytest.assume(exp_disable_existing_loggers==disable_existing_loggers)

@pytest.mark.yml
def test_parse_config_default_as_true(request, mocker, ymlparsersSetup, ymlparsersCleanup, initappconfFixture):
    logger.info(f'{request._pyfuncitem.name}()')
    pck = '.'.join(['tests_data', __package__, 'initappconf'])
    exp_disable_existing_loggers = False

    with path(pck, 'config.yml') as full_path:
        argsv = f'--general.config.file={full_path} ' \
                '--general.profiles=dev ' \
                f'--general.log.disable_existing_loggers={exp_disable_existing_loggers} ' \
            .split()

        dd = parse_config(None, argsv)
        disable_existing_loggers = dd['general']['log']['disable_existing_loggers']
        pytest.assume(exp_disable_existing_loggers==disable_existing_loggers)



if __name__ == "__main__":
    pytest.main([__file__])


