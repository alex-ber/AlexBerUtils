import logging
import time
import threading
import pytest
import copy

logger = logging.getLogger(__name__)

from importlib.resources import path

import collections
from collections import OrderedDict
import io
import yaml
from yaml import FullLoader
from alexber.utils.inspects import has_method
from alexber.utils._ymlparsers_extra import format_template


try:
    import alexber.utils.ymlparsers as ymlparsers
    from alexber.utils.ymlparsers import HiYaPyCo
    from alexber.utils.parsers import is_empty
    from jinja2 import DebugUndefined, StrictUndefined, Environment
    from hiyapyco import METHOD_SUBSTITUTE, METHOD_SIMPLE
except ImportError:
    pass

def _reset_ymlparsers():
    ymlparsers.HiYaPyCo.jinja2Lock = None
    ymlparsers.HiYaPyCo.jinja2ctx = None
    ymlparsers._load_d = None
    ymlparsers._safe_dump_d = None

@pytest.fixture
@pytest.mark.yml
def ymlparsersSetup(mocker):
    _reset_ymlparsers()

    ymlparsers.initConfig()

@pytest.fixture(scope='session')
@pytest.mark.yml
def exp_config_d():
    pck = '.'.join(['tests_data', __package__, 'ymlparsers'])

    with path(pck, 'config.yml') as full_path:
        with open(full_path, 'r') as f:
            exp_d = yaml.load(f, FullLoader)
    return exp_d



@pytest.fixture
@pytest.mark.yml
def ymlparsersCleanup(mocker):
    yield None
    _reset_ymlparsers()

class DymmyLock(object):
    def acquire(self, blocking=True):
        pass

    def release(self):
        pass

def create_mock_lock(mocker):
    mock_lock = DymmyLock()

    def __enter__():
        mock_lock.acquire()
        return mock_lock

    def __exit__(t, v, tb):
        mock_lock.release()

    mocker.patch.object(mock_lock, 'acquire', autospec=True, spec_set=True)
    mocker.patch.object(mock_lock, 'release', autospec=True, spec_set=True)
    mocker.patch.object(type(mock_lock), '__enter__', side_effect=__enter__, create=True)
    mocker.patch.object(type(mock_lock), '__exit__', side_effect=__exit__, create=True)
    return mock_lock


class TestYmlparsersInit(object):
    @pytest.mark.yml
    def test_initConfig_default_params(self, request, mocker, ymlparsersCleanup):
        logger.info(f'{request._pyfuncitem.name}()')
        ymlparsers.initConfig()
        lock = HiYaPyCo.jinja2Lock
        pytest.assume(lock is not None)
        lock_cls = type(lock)
        b = has_method(lock_cls, 'acquire')
        pytest.assume(b)
        b = has_method(lock_cls, 'release')
        pytest.assume(b)

        jinja2Env = HiYaPyCo.jinja2ctx
        pytest.assume(jinja2Env is not None)

        jinja2EnvUndefined = jinja2Env.undefined
        b = issubclass(jinja2EnvUndefined,DebugUndefined)
        pytest.assume(b)

        jinja2EnvGloblas = jinja2Env.globals
        b = 'uname' in jinja2EnvGloblas
        pytest.assume(b)

        _load_d = ymlparsers._load_d
        assert _load_d is not None
        b = isinstance(_load_d, collections.abc.Mapping)
        pytest.assume(b)

        for k, exp_v in {'method':METHOD_SUBSTITUTE,
                     'mergelists':False,
                     'interpolate':True,
                     'castinterpolated':True}.items():
            v = _load_d[k]
            pytest.assume(exp_v==v)


        _safe_dump_d = ymlparsers._safe_dump_d
        assert _safe_dump_d is not None
        b= isinstance(_safe_dump_d, collections.abc.Mapping)
        pytest.assume(b)

        for k, exp_v in {'default_flow_style':False,
                         'sort_keys':False}.items():
            v = _safe_dump_d[k]
            pytest.assume(exp_v==v)

        pytest.assume("TODO: HiYaPyCo._substmerge() bug workarround, see https://github.com/zerwes/hiyapyco/pull/38",
                      HiYaPyCo._deepmerge==HiYaPyCo._substmerge)

    @pytest.mark.yml
    def test_initConfig_other_params(self, request, mocker, ymlparsersCleanup):
        logger.info(f'{request._pyfuncitem.name}()')

        mock_lock = create_mock_lock(mocker)

        p_load = {'method':METHOD_SIMPLE,
               'mergelists':True,
               'interpolate':False,
               'castinterpolated':False}

        p_safe_dump = {'default_flow_style':True,
                       'sort_keys':True}

        p_undefined = StrictUndefined

        dumb = lambda:None

        p_globals = {"foo":dumb,
                     "uname":dumb}

        ymlparsers.initConfig(jinja2Lock=mock_lock,
                              jinja2ctx={'undefined':p_undefined,
                                         'globals':p_globals
                                         },
                              load=p_load,
                              safe_dump=p_safe_dump
                              )
        lock = HiYaPyCo.jinja2Lock
        pytest.assume(lock is not None)
        pytest.assume(lock==mock_lock)

        pytest.assume(mock_lock.acquire.call_count > 0)
        pytest.assume(mock_lock.release.call_count == mock_lock.acquire.call_count)

        jinja2Env = HiYaPyCo.jinja2ctx
        pytest.assume(jinja2Env is not None)

        jinja2EnvUndefined = jinja2Env.undefined
        b = issubclass(jinja2EnvUndefined, p_undefined)
        pytest.assume(b)

        jinja2EnvGloblas = jinja2Env.globals
        f= jinja2EnvGloblas['uname']
        pytest.assume(f==dumb)
        f = jinja2EnvGloblas['foo']
        pytest.assume(f == dumb)

        _load_d = ymlparsers._load_d
        assert _load_d is not None
        b = isinstance(_load_d, collections.abc.Mapping)
        pytest.assume(b)

        for k, exp_v in p_load.items():
            v = _load_d[k]
            pytest.assume(exp_v ==v)

        _safe_dump_d = ymlparsers._safe_dump_d
        assert _safe_dump_d is not None
        b = isinstance(_safe_dump_d, collections.abc.Mapping)
        pytest.assume(b)

        for k, exp_v in p_safe_dump.items():
            v = _safe_dump_d[k]
            pytest.assume(exp_v == v)

class TestDisableVarSubst(object):

    @pytest.mark.yml
    def test_intented_usage(self, request, mocker, ymlparsersSetup, ymlparsersCleanup, exp_config_d):
        logger.info(f'{request._pyfuncitem.name}()')

        mock_lock = create_mock_lock(mocker)

        orig_jinja2ctx = HiYaPyCo.jinja2ctx

        mocker.patch.object(HiYaPyCo, 'jinja2Lock', new=mock_lock, spec_set=True)
        jinja2ctx_mock = mocker.patch.object(HiYaPyCo, 'jinja2ctx', spec_set=True)

        mock_variable_start_string = mocker.PropertyMock(return_value=orig_jinja2ctx.variable_start_string)
        type(jinja2ctx_mock).variable_start_string = mock_variable_start_string
        mock_variable_end_string = mocker.PropertyMock(return_value=orig_jinja2ctx.variable_end_string)
        type(jinja2ctx_mock).variable_end_string = mock_variable_end_string
        mock_block_start_string = mocker.PropertyMock(return_value=orig_jinja2ctx.block_start_string)
        type(jinja2ctx_mock).block_start_string = mock_block_start_string
        mock_block_end_string = mocker.PropertyMock(return_value=orig_jinja2ctx.block_end_string)
        type(jinja2ctx_mock).block_end_string = mock_block_end_string

        mocks = [mock_variable_start_string, mock_variable_end_string, mock_block_start_string, mock_block_end_string]

        # orig_exit = ymlparsers.DisableVarSubst.__exit__
        # mock_exit = mocker.patch.object(ymlparsers.DisableVarSubst, '__exit__', side_effect=orig_exit,
        #                                 autospec=True, spec_set=True)



        with ymlparsers.DisableVarSubst():
            logger.debug("dff")
            pass

        # pytest.assume(mock_exit.call_count == 1)
        pytest.assume(mock_lock.acquire.call_count > 0)
        pytest.assume(mock_lock.release.call_count == mock_lock.acquire.call_count)

        setter_called = None
        for mock in mocks:
            setter_called = None
            pytest.assume(mock.call_count > 0)
            for kall in mock.call_args_list:
                #(param,), _ = kall
                args, _ = kall
                if not is_empty(args) and '|' in args[0]:
                    setter_called = True
                    break
            pytest.assume(setter_called)

        pytest.assume(jinja2ctx_mock.variable_start_string == orig_jinja2ctx.variable_start_string)
        pytest.assume(jinja2ctx_mock.variable_end_string == orig_jinja2ctx.variable_end_string)
        pytest.assume(jinja2ctx_mock.block_start_string == orig_jinja2ctx.block_start_string)
        pytest.assume(jinja2ctx_mock.block_end_string == orig_jinja2ctx.block_end_string)

    class DummyEnvironment(object):
        def __init__(self, *args, **kwargs):
            self.delegate = kwargs['delegate']
            self._variable_start_string = self.delegate.variable_start_string
            self._variable_end_string = self.delegate.variable_end_string
            self._block_start_string =  self.delegate.block_start_string
            self._block_end_string = self.delegate.block_end_string
            self.raiseAlways = kwargs.get('raiseAlways', False)

        @property
        def variable_start_string(self):
            return self._variable_start_string

        @variable_start_string.setter
        def variable_start_string(self, new_name):
            self._variable_start_string = new_name

        @property
        def variable_end_string(self):
            return self._variable_end_string

        @variable_end_string.setter
        def variable_end_string(self, new_name):
            self._variable_end_string = new_name

        @property
        def block_start_string(self):
            return self._block_start_string

        @block_start_string.setter
        def block_start_string(self, new_name):
            self._block_start_string = new_name

        @property
        def block_end_string(self):
            return self._block_end_string

        @block_end_string.setter
        def block_end_string(self, new_name):
            if self.raiseAlways or ('|' not in new_name):
                raise ValueError
            self._block_end_string = new_name

    @pytest.mark.yml
    def test_exception_in_exit(self, request, mocker, ymlparsersSetup, ymlparsersCleanup, exp_config_d):
        logger.info(f'{request._pyfuncitem.name}()')
        #I check 2 things
        #1. Explicately passing params
        #2. Releasing lock even if exception occures in DisableVarSubst. __exit__

        mock_lock = create_mock_lock(mocker)

        orig_jinja2ctx = HiYaPyCo.jinja2ctx
        duumy_jinja2ctx = TestDisableVarSubst.DummyEnvironment(delegate=orig_jinja2ctx)

        #orig_exit = ymlparsers.DisableVarSubst.__exit__
        # mock_exit = mocker.patch.object(ymlparsers.DisableVarSubst, '__exit__', side_effect=orig_exit,
        #                                 autospec=True, spec_set=True)

        with pytest.raises(ValueError):
            with ymlparsers.DisableVarSubst(jinja2ctx=duumy_jinja2ctx, jinja2Lock=mock_lock):
                pass

        # pytest.assume(mock_exit.call_count == 1)
        pytest.assume(mock_lock.acquire.call_count > 0)
        pytest.assume(mock_lock.release.call_count == mock_lock.acquire.call_count)

        pytest.assume(duumy_jinja2ctx != orig_jinja2ctx)
        pytest.assume(mock_lock != orig_jinja2ctx)

        pytest.assume(duumy_jinja2ctx.variable_start_string == orig_jinja2ctx.variable_start_string)
        pytest.assume(duumy_jinja2ctx.variable_end_string == orig_jinja2ctx.variable_end_string)
        pytest.assume(duumy_jinja2ctx.block_start_string == orig_jinja2ctx.block_start_string)
        pytest.assume(duumy_jinja2ctx.block_end_string !=  orig_jinja2ctx.block_end_string )

    @pytest.mark.yml
    def test_exception_in_enter(self, request, mocker, ymlparsersSetup, ymlparsersCleanup, exp_config_d):
        logger.info(f'{request._pyfuncitem.name}()')
        #I check 2 things
        #1. Explicately passing params
        #2. Releasing lock even if exception occures in DisableVarSubst.__enter__

        mock_lock = create_mock_lock(mocker)

        orig_jinja2ctx = HiYaPyCo.jinja2ctx
        duumy_jinja2ctx = TestDisableVarSubst.DummyEnvironment(delegate=orig_jinja2ctx, raiseAlways=True)

        # orig_exit = ymlparsers.DisableVarSubst.__exit__
        # mock_exit = mocker.patch.object(ymlparsers.DisableVarSubst, '__exit__', side_effect=orig_exit,
        #                     autospec=True, spec_set=True)


        with pytest.raises(ValueError):
            with ymlparsers.DisableVarSubst(jinja2ctx=duumy_jinja2ctx, jinja2Lock=mock_lock):
                pass

        # pytest.assume(mock_exit.call_count == 0)
        pytest.assume(mock_lock.acquire.call_count > 0)
        pytest.assume(mock_lock.release.call_count == mock_lock.acquire.call_count)

        pytest.assume(duumy_jinja2ctx != orig_jinja2ctx)
        pytest.assume(mock_lock != orig_jinja2ctx)

        pytest.assume(duumy_jinja2ctx.variable_start_string != orig_jinja2ctx.variable_start_string)
        pytest.assume(duumy_jinja2ctx.variable_end_string != orig_jinja2ctx.variable_end_string)
        pytest.assume(duumy_jinja2ctx.block_start_string != orig_jinja2ctx.block_start_string)
        pytest.assume(duumy_jinja2ctx.block_end_string == orig_jinja2ctx.block_end_string)

    @pytest.mark.yml
    def test_exception_in_code(self, request, mocker, ymlparsersSetup, ymlparsersCleanup, exp_config_d):
        logger.info(f'{request._pyfuncitem.name}()')
        #I check 2 things
        #1. Explicately passing params
        #2. Releasing lock even if exception occures in the with

        mock_lock = create_mock_lock(mocker)

        orig_jinja2ctx = HiYaPyCo.jinja2ctx

        mocker.patch.object(HiYaPyCo, 'jinja2Lock', new=mock_lock, spec_set=True)
        jinja2ctx_mock = mocker.patch.object(HiYaPyCo, 'jinja2ctx', spec_set=True)

        mock_variable_start_string = mocker.PropertyMock(return_value=orig_jinja2ctx.variable_start_string)
        type(jinja2ctx_mock).variable_start_string = mock_variable_start_string
        mock_variable_end_string = mocker.PropertyMock(return_value=orig_jinja2ctx.variable_end_string)
        type(jinja2ctx_mock).variable_end_string = mock_variable_end_string
        mock_block_start_string = mocker.PropertyMock(return_value=orig_jinja2ctx.block_start_string)
        type(jinja2ctx_mock).block_start_string = mock_block_start_string
        mock_block_end_string = mocker.PropertyMock(return_value=orig_jinja2ctx.block_end_string)
        type(jinja2ctx_mock).block_end_string = mock_block_end_string

        mocks = [mock_variable_start_string, mock_variable_end_string, mock_block_start_string, mock_block_end_string]
        # orig_exit = ymlparsers.DisableVarSubst.__exit__
        # mock_exit = mocker.patch.object(ymlparsers.DisableVarSubst, '__exit__', side_effect=orig_exit,
        #                                 autospec=True, spec_set=True)

        with pytest.raises(ValueError):
            with ymlparsers.DisableVarSubst():
                raise ValueError

        # pytest.assume(mock_exit.call_count == 1)
        pytest.assume(mock_lock.acquire.call_count > 0)
        pytest.assume(mock_lock.release.call_count == mock_lock.acquire.call_count)

        setter_called = None
        for mock in mocks:
            setter_called = None
            pytest.assume(mock.call_count > 0)
            for kall in mock.call_args_list:
                # (param,), _ = kall
                args, _ = kall
                if not is_empty(args) and '|' in args[0]:
                    setter_called = True
                    break
            pytest.assume(setter_called)

        pytest.assume(jinja2ctx_mock.variable_start_string == orig_jinja2ctx.variable_start_string)
        pytest.assume(jinja2ctx_mock.variable_end_string == orig_jinja2ctx.variable_end_string)
        pytest.assume(jinja2ctx_mock.block_start_string == orig_jinja2ctx.block_start_string)
        pytest.assume(jinja2ctx_mock.block_end_string == orig_jinja2ctx.block_end_string)


@pytest.mark.yml
def test_ymlparsers_load_single_no_substition(request, mocker, ymlparsersSetup, ymlparsersCleanup, exp_config_d):
    logger.info(f'{request._pyfuncitem.name}()')

    pck = '.'.join(['tests_data', __package__, 'ymlparsers'])

    mock_lock = create_mock_lock(mocker)
    mocker.patch.object(HiYaPyCo, 'jinja2Lock', new=mock_lock, spec_set=True)

    with path(pck, 'config.yml') as full_path:
        with ymlparsers.DisableVarSubst():
            default_d = ymlparsers.load([str(full_path)])

    # ymlparsers.load() when uses HiYaPyCo.jinja2ctx uses HiYaPyCo.jinja2Lock
    # note, that ymlparsers.DisableVarSubst also use 1 time HiYaPyCo.jinja2Lock
    pytest.assume(mock_lock.acquire.call_count > 1)
    pytest.assume(mock_lock.release.call_count == mock_lock.acquire.call_count)


    app_d = default_d.get('app', None)
    exp_d = copy.deepcopy(exp_config_d)
    exp_app_d = exp_d.get('app', None)

    inner_host_name = app_d.get('inner_host_name', None)
    exp_host_name = exp_app_d.get('inner_host_name', None)
    pytest.assume(exp_host_name==inner_host_name)
    cli_template = app_d.get('cli_template')
    pytest.assume('inner_host_name' in cli_template)
    pytest.assume(exp_config_d==default_d)


@pytest.mark.yml
def test_ymlparsers_load_single_with_substition(request, mocker, ymlparsersSetup, ymlparsersCleanup, exp_config_d):
    logger.info(f'{request._pyfuncitem.name}()')

    pck = '.'.join(['tests_data', __package__, 'ymlparsers'])


    mock_lock = create_mock_lock(mocker)
    mocker.patch.object(HiYaPyCo, 'jinja2Lock', new=mock_lock, spec_set=True)

    with path(pck, 'config.yml') as full_path:
        default_d = ymlparsers.load([str(full_path)])

    pytest.assume(mock_lock.acquire.call_count > 1)
    pytest.assume(mock_lock.release.call_count == mock_lock.acquire.call_count)

    app_d = default_d['app']
    exp_d = copy.deepcopy(exp_config_d)
    exp_app_d = exp_d.get('app', None)

    inner_host_name = app_d.get('inner_host_name', None)
    exp_host_name = exp_app_d.get('inner_host_name', None)
    pytest.assume(exp_host_name==inner_host_name)

    exp_cli_template = exp_app_d.get('cli_template', None)
    exp_cli_template = format_template(exp_cli_template, app_inner_host_name=exp_host_name)
    exp_app_d['cli_template']=exp_cli_template


    cli_template = app_d.get('cli_template')
    pytest.assume('inner_host_name' not in cli_template)

    cli_template = app_d['cli_template']
    pytest.assume('inner_host_name' not in cli_template)
    pytest.assume(exp_d==default_d)

    white_list = app_d.get('white_list', None)
    exp_white_list = exp_app_d.get('white_list', None)
    pytest.assume(exp_white_list==white_list)


#order is non-alephabetic intentionally
_data_list = {'profiles': ['local', 'dev']}
_data_dict = {'general':
                 { 'whiteListSysOverrideKeys': ['app'],
                   'profiles': ['local', 'dev']},
              'app':
                  {'host_name': 'google.com'},
             }

@pytest.mark.parametrize(
     'data, kwds',

    [
        (_data_list, {}),

        #sort_key is ignored
        (_data_list, {'default_flow_style': None,  'sort_keys': True}),
        (_data_list, {'default_flow_style': False, 'sort_keys': True}),
        (_data_list, {'default_flow_style': True,  'sort_keys': True}),

        (_data_dict, {'default_flow_style': None,  'sort_keys': True}),
        (_data_dict, {'default_flow_style': False, 'sort_keys': True}),
        (_data_dict, {'default_flow_style': True,  'sort_keys': True}),

    ]
)
@pytest.mark.yml
def test_safe_dump_composite(request, mocker, ymlparsersSetup, ymlparsersCleanup, data, kwds):
    logger.info(f'{request._pyfuncitem.name}()')

    default_flow_style = kwds.get('default_flow_style', False)

    with io.StringIO() as buf:
        ymlparsers.safe_dump(data, stream=buf, **kwds)
        value = buf.getvalue()
        logger.debug(value)
        if default_flow_style is not None and not default_flow_style:
            pytest.assume('-' in value)
        else:
            pytest.assume('[' in value)
            pytest.assume(']' in value)

        with ymlparsers.DisableVarSubst():
            restored_d = ymlparsers.load(value)

    pytest.assume(data == restored_d)

@pytest.mark.yml
def test_safe_dump(request, mocker, ymlparsersSetup, ymlparsersCleanup, exp_config_d):
    logger.info(f'{request._pyfuncitem.name}()')

    orig_d = dict(exp_config_d)
    d = OrderedDict(exp_config_d)
    d['general'] = OrderedDict(d['general'])
    d['app'] = OrderedDict(d['app'])

    with io.StringIO() as buf:
        ymlparsers.safe_dump(d, stream=buf)
        value = buf.getvalue()

    with ymlparsers.DisableVarSubst():
        restored_d = ymlparsers.load(value)

    pytest.assume(orig_d==restored_d)

@pytest.mark.yml
def test_as_str(request, mocker, ymlparsersSetup, ymlparsersCleanup, exp_config_d):
    logger.info(f'{request._pyfuncitem.name}()')

    orig_d = dict(exp_config_d)
    d = OrderedDict(exp_config_d)
    d['general'] = OrderedDict(d['general'])
    d['app'] = OrderedDict(d['app'])

    orig_safe_dump = ymlparsers.safe_dump
    mock_safe_dump = mocker.patch.object(ymlparsers, 'safe_dump', side_effect=orig_safe_dump,
                                    autospec=True, spec_set=True)

    value = ymlparsers.as_str(d)
    pytest.assume(mock_safe_dump.call_count > 0)

    with ymlparsers.DisableVarSubst():
        restored_d = ymlparsers.load(value)

    pytest.assume(orig_d==restored_d)

@pytest.mark.yml
def test_ymlparsers_load_multiple_no_substition(request, mocker, ymlparsersSetup, ymlparsersCleanup, exp_config_d):
    logger.info(f'{request._pyfuncitem.name}()')

    exp_d = copy.deepcopy(exp_config_d)
    exp_d['general']['log']['formatters']['detail'] = {'format': \
                                                '%(asctime)-14s %(levelname)s [%(name)s.%(funcName)s] %(message)s',
                                                       'datefmt': \
                                                '%Y-%m-%d %H:%M:%S'}
    exp_d['general']['log']['root']['level'] = 'INFO'
    exp_d['app']['inner_host_name'] = 'yahoo.com'
    exp_d['app']['white_list'] = ['gamma', 'alpha', 'betha']
    exp_d['app']['alt_white_list'] = ['c', 'b', 'a']



    pck = '.'.join(['tests_data', __package__, 'ymlparsers'])

    with path(pck, 'config.yml') as full_path:
        with path(pck, 'config-dev.yml') as full_dev_path:
            with ymlparsers.DisableVarSubst():
                default_d = ymlparsers.load([str(full_path), str(full_dev_path)])


    app_d = default_d.get('app', None)
    exp_app_d = exp_d.get('app', None)

    inner_host_name = app_d.get('inner_host_name', None)
    exp_host_name = exp_app_d.get('inner_host_name', None)
    pytest.assume(exp_host_name==inner_host_name)

    cli_template = app_d.get('cli_template')
    pytest.assume('inner_host_name' in cli_template)

    pytest.assume(exp_d==default_d)

@pytest.mark.yml
def test_ymlparsers_load_multiple_with_substition(request, mocker, ymlparsersSetup, ymlparsersCleanup, exp_config_d):
    logger.info(f'{request._pyfuncitem.name}()')

    pck = '.'.join(['tests_data', __package__, 'ymlparsers'])

    exp_d = copy.deepcopy(exp_config_d)
    exp_d['general']['log']['formatters']['detail'] = {'format': \
                                                           '%(asctime)-14s %(levelname)s [%(name)s.%(funcName)s] %(message)s',
                                                       'datefmt': \
                                                           '%Y-%m-%d %H:%M:%S'}
    exp_d['general']['log']['root']['level'] = 'INFO'
    exp_d['app']['inner_host_name'] = 'yahoo.com'
    exp_d['app']['white_list'] = ['gamma', 'alpha', 'betha']
    exp_d['app']['alt_white_list'] = ['c', 'b', 'a']

    with path(pck, 'config.yml') as full_path:
        with path(pck, 'config-dev.yml') as full_dev_path:
            default_d = ymlparsers.load([str(full_path), str(full_dev_path)])


    app_d = default_d['app']
    exp_app_d = exp_d.get('app', None)

    inner_host_name = app_d.get('inner_host_name', None)
    exp_host_name = exp_app_d.get('inner_host_name', None)
    pytest.assume(exp_host_name==inner_host_name)

    exp_cli_template = exp_app_d.get('cli_template', None)
    exp_cli_template = format_template(exp_cli_template, app_inner_host_name=exp_host_name)
    exp_app_d['cli_template']=exp_cli_template


    cli_template = app_d.get('cli_template')
    pytest.assume('inner_host_name' not in cli_template)

    cli_template = app_d['cli_template']
    pytest.assume('inner_host_name' not in cli_template)

    pytest.assume(exp_d==default_d)


def _run_without_substition(content, exp_config_d, stop):
    for i in range(stop):
        with ymlparsers.DisableVarSubst():
            default_d = ymlparsers.load([str(content)])

            app_d = default_d.get('app', None)
            exp_app_d = exp_config_d.get('app', None)

            inner_host_name = app_d.get('inner_host_name', None)
            exp_host_name = exp_app_d.get('inner_host_name', None)
            pytest.assume(exp_host_name==inner_host_name)
            cli_template = app_d.get('cli_template')
            pytest.assume('inner_host_name' in cli_template)
            pytest.assume(exp_config_d == default_d)

def _run_with_substition(content, exp_config_d, stop):
    for i in range(stop):
        default_d = ymlparsers.load([str(content)])

        app_d = default_d['app']
        exp_app_d = exp_config_d.get('app', None)

        inner_host_name = app_d.get('inner_host_name', None)
        exp_host_name = exp_app_d.get('inner_host_name', None)
        pytest.assume(exp_host_name==inner_host_name)

        exp_cli_template = exp_app_d.get('cli_template', None)
        exp_cli_template = format_template(exp_cli_template, app_inner_host_name=exp_host_name)

        exp_app_d['cli_template'] = exp_cli_template

        cli_template = app_d.get('cli_template')
        pytest.assume('inner_host_name' not in cli_template)

        cli_template = app_d['cli_template']
        pytest.assume('inner_host_name' not in cli_template)
        pytest.assume(exp_config_d == default_d)

@pytest.mark.yml
def test_ymlparsers_load_it(request, mocker, ymlparsersSetup, ymlparsersCleanup, exp_config_d):
    logger.info(f'{request._pyfuncitem.name}()')
    pck = '.'.join(['tests_data', __package__, 'ymlparsers'])

    with path(pck, 'config.yml') as full_path:
        with open(full_path, 'r') as f:
            content = f.read()

    stop = 10

    exp_d = copy.deepcopy(exp_config_d)
    exp_app_d = dict(exp_d.get('app', None))
    if exp_app_d is not None:
        exp_d['app'] = exp_app_d

    exp_host_name = exp_app_d.get('inner_host_name', None)
    exp_cli_template = exp_app_d.get('cli_template', None)
    exp_cli_template = format_template(exp_cli_template, app_inner_host_name=exp_host_name)
    exp_app_d['cli_template'] = exp_cli_template


    th1 = threading.Thread(name="run_with_substition",
        target=_run_with_substition, args=(content, exp_d, stop))

    th2 = threading.Thread(name="run_without_substition",
                           target=_run_without_substition, args=(str(content), copy.deepcopy(exp_config_d), stop))

    th1.start()
    time.sleep(2)
    th2.start()
    th1.join()
    th2.join()


if __name__ == "__main__":
    pytest.main([__file__])
