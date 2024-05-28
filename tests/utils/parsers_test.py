import logging
import enum
from enum import Enum
import pytest


from alexber.utils.parsers import ConfigParser, ArgumentParser, safe_eval, is_empty, parse_boolean, parse_sys_args

logger = logging.getLogger(__name__)
from decimal import Decimal
from datetime import datetime
from importlib.resources import path

def test_parse_config(request):
    logger.info(f'{request._pyfuncitem.name}()')

    parser = ConfigParser()

    pck = '.'.join(['tests_data', __package__, 'parser'])

    with path(pck, 'config.ini') as f:
        parser.read(f)

    dd = parser.as_dict()
    da = dd['playera']
    clsa = da['cls']
    namea = da['name']

    db = dd['playerb']
    clsb = db['cls']
    nameb = db['name']

    assert clsa==clsb
    assert namea == nameb


@pytest.fixture(params=[
    #'args,exp_d',
    ('--key=value --single',
     dict([('key', 'value'), ('single', None)])),

    ('wrong=pair',
         dict([('wrong=pair', None)])),

    ('--conf --prop1=value1 --prop2=value --prop1=value9',
         dict([('conf', None), ('prop1', 'value9'), ('prop2', 'value')])),

])
def arg_parse_param(request):
    return request.param

def test_args_parse(request, mocker, arg_parse_param):
    logger.info(f'{request._pyfuncitem.name}()')
    args, exp_d = arg_parse_param

    parser = ArgumentParser()

    mock_args = mocker.patch('alexber.utils.parsers.sys.argv', new_callable=list)
    mock_args.append(__file__)
    mock_args[1:] = args.split()

    d = parser.as_dict()
    assert exp_d==d


def test_args_parse_explicit_args(request, arg_parse_param):
    logger.info(f'{request._pyfuncitem.name}()')
    args, exp_d = arg_parse_param

    parser = ArgumentParser()

    sys_args = args.split()

    d = parser.as_dict(args=sys_args)
    assert exp_d==d


@pytest.mark.parametrize(
     'value, exp_value, exp_type',

    [
        ('John', 'John', str),
        ('alexber.utils.players.ConstantPlayer', 'alexber.utils.players.ConstantPlayer', str),
        ('1000', 1000, int),
        ('0.1', 0.1, float),
        ('0.0', 0.0, float),
        ('-0.0', -0.0, float),
        ('-5', -5, int),
        ('0.1', None, Decimal),  #Not Supprted
        ('2019-04-01 16:31:51.513383', None, datetime),  #Not Supprted
        ('%(message)s','%(message)s', str),#https://github.com/alex-ber/AlexBerUtils/issues/2
        ('(message)s','(message)s', str),
        ('(message)','(message)', str),

    ]
)
def test_convert(request, value, exp_value, exp_type):
    logger.info(f'{request._pyfuncitem.name}()')
    if exp_value is None:
        logger.debug(f"Type {exp_type} is not supported.")
        return


    result = safe_eval(value)
    type_result = type(result)
    pytest.assume(exp_value == result)
    pytest.assume(exp_type == type_result)


@enum.unique
class Color(Enum):
    RED = 'r'
    BLUE = 'b'
    GREEN = 'g'


@pytest.mark.parametrize(
    'value, exp_result',
    [
     (True, False),
     (False, True),
     (None, True),

     ("something", False),
     ("", True),
     #
     (1, False),
     (0, True),
     (0.0, True),

     ("1", False),
     ("0", False),

     (Color.RED, False),
     ([], True),
     ([None], False),
     (['something'], False),
     ]
)
def test_is_empty(request, value, exp_result):
    logger.info(f'{request._pyfuncitem.name}()')

    result = is_empty(value)
    assert exp_result == result


@pytest.mark.parametrize(
    'value, exp_result',
    [
     (True, True),
     (False, False),
     (None, None),

     ("True", True),
     ("False", False),

     ("TRUE", True),
     ("FALSE", False),

     ("tRuE", True),
     ("fALsE", False),

     ("true", True),
     ("false", False),

     (1, True),
     (0, False),
     (0.0, False),
     ]
)
def test_parse_boolean(request, value, exp_result):
    logger.info(f'{request._pyfuncitem.name}()')

    result = parse_boolean(value)
    assert exp_result == result

@pytest.mark.parametrize(
    'value',
    [
     ("gibrish123"),
     ("T"),
     ("F"),

     ("t"),
     ("f"),

     ("1"),
     ("0"),

     (3.5),
     ([]),
     (5),
     (2.01),

    ]
)


def test_parse_boolean_invalid(request, value):
    logger.info(f'{request._pyfuncitem.name}()')

    with pytest.raises(ValueError, match='nknown'):
        parse_boolean(value)



def test_parse_sys_args(request):
    logger.info(f'{request._pyfuncitem.name}()')
    expdd = {
        'general.profiles': "dev",
        'general.log.formatters.detail.format': '%(message)s',
        'general.log.root.level': '20', #logging.INFO
        'app.inner_host_name': 'yahoo.com',
        'app.white_list': 'gamma,alpha,betha',
        'app.alt_white_list': '100,10.0'
    }

    argsv = '--general.profiles=dev ' \
            '--general.log.formatters.detail.format=%(message)s ' \
            '--general.log.root.level=20 ' \
            '--app.inner_host_name=yahoo.com ' \
            '--app.white_list=gamma,alpha,betha ' \
            '--app.alt_white_list=100,10.0 ' \
        .split()


    _, dd = parse_sys_args(args=argsv)
    assert expdd == dd


if __name__ == "__main__":
    pytest.main([__file__])
