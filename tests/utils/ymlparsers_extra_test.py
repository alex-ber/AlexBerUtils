import logging
import pytest
import alexber.utils._ymlparsers_extra as ymlparsers_extra
from alexber.utils._ymlparsers_extra import _convert_template_to_string_format, \
    __convert_template_to_string_format as uuconvert_template_to_string_format, \
    format_template



try:
    from .ymlparsers_test import ymlparsersSetup, ymlparsersCleanup, ymlparsers, create_mock_lock
    from alexber.utils._ymlparsers_extra import HiYaPyCo

    from jinja2 import Environment as _Environment, \
                 DebugUndefined as _DebugUndefined
except ImportError:
    pass

logger = logging.getLogger(__name__)


@pytest.fixture
def ymlparsersExtraFixture(request, mocker, ymlparsersSetup, ymlparsersCleanup):
    p_isHiYaPyCoAvailable = ymlparsers_extra._isHiYaPyCoAvailable
    p_isJinja2DefaultAvailable = ymlparsers_extra._isJinja2DefaultAvailable

    if p_isHiYaPyCoAvailable and p_isJinja2DefaultAvailable:
        request_param = (p_isHiYaPyCoAvailable, p_isJinja2DefaultAvailable) if (not hasattr(request, 'param')) else request.param
    else:
        request_param = (False, False)
    isHiYaPyCoAvailable, isJinja2DefaultAvailable = request_param

    ymlparsers_extra._isHiYaPyCoAvailable = isHiYaPyCoAvailable
    ymlparsers_extra._isJinja2DefaultAvailable = isJinja2DefaultAvailable
    ymlparsers_extra._init_globals()

    yield request_param
    ymlparsers_extra._isHiYaPyCoAvailable = p_isHiYaPyCoAvailable
    ymlparsers_extra._isJinja2DefaultAvailable = p_isJinja2DefaultAvailable
    ymlparsers_extra._init_globals()



@pytest.mark.parametrize(
     'template, exp_value',

    [
        ('ping {{app.inner_host_name}}', 'ping {app_inner_host_name}'),
        ('Hi, {{user}}. My name is {{app.first.name}}. Good Luck!', 'Hi, {user}. My name is {app_first_name}. Good Luck!'),
        ('plain text', 'plain text'),
        ('First. Second.', 'First. Second.'),
        ('{{name}}', '{name}'),
        ('{{app,name}}', '{app,name}'),
        ('{{name}}.', '{name}.'),
        ('{{app,name}}.', '{app,name}.'),
        ('', ''),
         (None, None),


    ]
)

def test_uuconvert_template_to_string_format(request, mocker, template, exp_value):
    logger.info(f'{request._pyfuncitem.name}()')

    value = uuconvert_template_to_string_format(template,
                                                default_start='{{',
                                                default_end='}}'
                                                )
    pytest.assume(exp_value==value)



def test_uuconvert_template_to_string_format_undocumented1(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    exp_value = 'ping {{app.inner_host_name}}'
    value = uuconvert_template_to_string_format(exp_value, default_start=None, default_end=None)
    pytest.assume(exp_value == value)

def test_uuconvert_template_to_string_format_undocumented2(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    exp_value = 'ping {{app.inner_host_name}}'
    value = uuconvert_template_to_string_format(exp_value)
    pytest.assume(exp_value == value)


def test_uuconvert_is_used_in_uconvert_template_to_string_format(request, mocker, ymlparsersExtraFixture):
    logger.info(f'{request._pyfuncitem.name}()')

    uconvert_mock=mocker.patch('alexber.utils._ymlparsers_extra.__convert_template_to_string_format',
                               side_effect=uuconvert_template_to_string_format, autospec=True, spec_set=True)

    exp_value = '{name}'
    template = '{{name}}'
    value = _convert_template_to_string_format(template)
    pytest.assume(exp_value == value)
    pytest.assume(uconvert_mock.call_count > 0)


#isHiYaPyCoAvailable,isJinja2DefaultAvailable
@pytest.mark.parametrize('ymlparsersExtraFixture', [(False, False), #minimal, no 3-rd party dependencies
                                                    (True, True),   #maximal 3-rd party dependencies available, \
                                                                    #but not customized
                                                    (False, True),  #only Jinja2 avaialble
                                                    (True, False),  #can't really happen
                                                    ], indirect=True)
def test_uconvert_template_to_string_format_minimal(request, mocker, ymlparsersExtraFixture):
    logger.info(f'{request._pyfuncitem.name}{ymlparsersExtraFixture}')

    exp_value = '{name}'
    template = '{{name}}'
    value = _convert_template_to_string_format(template)
    pytest.assume(exp_value == value)


#isHiYaPyCoAvailable,isJinja2DefaultAvailable
@pytest.mark.parametrize('ymlparsersExtraFixture', [(False, True)  #only Jinja2 avaialble \
                                                    ], indirect = True)
@pytest.mark.yml
def test_uconvert_template_to_string_jinja2DefaultChanged(request, mocker, ymlparsersExtraFixture):
    logger.info(f'{request._pyfuncitem.name}{ymlparsersExtraFixture}')


    mocker.patch('jinja2.defaults.VARIABLE_START_STRING', new='1_', spec_set=True)
    mocker.patch('jinja2.defaults.VARIABLE_END_STRING', new='_1', spec_set=True)

    ymlparsers_extra._init_globals()
    exp_value = '{name}'
    template = '1_name_1'
    value = _convert_template_to_string_format(template)
    pytest.assume(exp_value == value)

#isHiYaPyCoAvailable,isJinja2DefaultAvailable
@pytest.mark.parametrize('ymlparsersExtraFixture', [(True, False)
                                                    ], indirect = True)
@pytest.mark.yml
def test_uconvert_template_to_string_HiYaPyCoDefault(request, mocker, ymlparsersExtraFixture):
    logger.info(f'{request._pyfuncitem.name}{ymlparsersExtraFixture}')

    ymlparsers.initConfig()

    mock_lock = create_mock_lock(mocker)
    init_jinja2ctx = HiYaPyCo.jinja2ctx
    mocker.patch.object(HiYaPyCo, 'jinja2Lock', new=mock_lock, spec_set=True)
    jinja2ctx_mock = mocker.patch.object(HiYaPyCo, 'jinja2ctx', spec_set=True)
    mock_variable_start_string = mocker.PropertyMock(return_value=init_jinja2ctx.variable_start_string)
    type(jinja2ctx_mock).variable_start_string = mock_variable_start_string
    mock_variable_end_string = mocker.PropertyMock(return_value=init_jinja2ctx.variable_end_string)
    type(jinja2ctx_mock).variable_end_string = mock_variable_end_string

    exp_value = '{name}'
    template = '{{name}}'
    value = _convert_template_to_string_format(template)
    pytest.assume(exp_value == value)

    pytest.assume(mock_lock.acquire.call_count > 0)
    pytest.assume(mock_lock.release.call_count == mock_lock.acquire.call_count)

    pytest.assume(mock_variable_start_string.call_count > 0)
    pytest.assume(mock_variable_end_string.call_count > 0)


#isHiYaPyCoAvailable,isJinja2DefaultAvailable
@pytest.mark.parametrize('ymlparsersExtraFixture', [(True, False)
                                                    ], indirect = True)
@pytest.mark.yml
def test_uconvert_template_to_string_HiYaPyCoDefaultChanged(request, mocker, ymlparsersExtraFixture):
    logger.info(f'{request._pyfuncitem.name}{ymlparsersExtraFixture}')


    ymlparsers.initConfig(jinja2ctx={'variable_start_string':'2_', 'variable_end_string':'_2' })
    init_jinja2ctx = HiYaPyCo.jinja2ctx

    mock_lock = create_mock_lock(mocker)
    mocker.patch.object(HiYaPyCo, 'jinja2Lock', new=mock_lock, spec_set=True)
    jinja2ctx_mock = mocker.patch.object(HiYaPyCo, 'jinja2ctx', spec_set=True)
    mock_variable_start_string = mocker.PropertyMock(return_value=init_jinja2ctx.variable_start_string)
    type(jinja2ctx_mock).variable_start_string = mock_variable_start_string
    mock_variable_end_string = mocker.PropertyMock(return_value=init_jinja2ctx.variable_end_string)
    type(jinja2ctx_mock).variable_end_string = mock_variable_end_string

    exp_value = '{name}'
    template = '2_name_2'
    value = _convert_template_to_string_format(template)
    pytest.assume(exp_value == value)

    pytest.assume(mock_lock.acquire.call_count > 0)
    pytest.assume(mock_lock.release.call_count == mock_lock.acquire.call_count)

    pytest.assume(mock_variable_start_string.call_count > 0)
    pytest.assume(mock_variable_end_string.call_count > 0)

@pytest.mark.yml
def test_uconvert_template_to_string_explicit_param1_jinja2ctx(request, mocker, ymlparsersExtraFixture):
    logger.info(f'{request._pyfuncitem.name}{ymlparsersExtraFixture}')

    mock_lock = create_mock_lock(mocker)

    exp_value = '{name}'
    template = '3_name_3'

    jinja2ctx = _Environment(undefined=_DebugUndefined, variable_start_string='3_', variable_end_string='_3')
    value = _convert_template_to_string_format(template, jinja2ctx=jinja2ctx)
    pytest.assume(exp_value == value)

@pytest.mark.yml
def test_uconvert_template_to_string_explicit_param1_jinja2Lock(request, mocker, ymlparsersExtraFixture):
    logger.info(f'{request._pyfuncitem.name}{ymlparsersExtraFixture}')

    mock_lock = create_mock_lock(mocker)
    mocker.patch.object(HiYaPyCo, 'jinja2Lock', new=mock_lock, spec_set=True)

    #exp_value = '{name}'
    template = '{{name}}'   #HiYaPyCo.jinja2ctx is default one

    jinja2Lock_param_lock = create_mock_lock(mocker)
    with pytest.raises(ValueError):
        _convert_template_to_string_format(template, jinja2Lock=jinja2Lock_param_lock)
    #pytest.assume(exp_value == value)
    pytest.assume(mock_lock.acquire.call_count == 0)
    #pytest.assume(jinja2Lock_param_lock.acquire.call_count ==0)



#isHiYaPyCoAvailable,isJinja2DefaultAvailable
@pytest.mark.parametrize('ymlparsersExtraFixture', [(False, True)   #only Jinja2 avaialble \
                                                    ], indirect = True)
@pytest.mark.yml
def test_uconvert_template_to_string_explicit_param1a_jinja2Lock(request, mocker, ymlparsersExtraFixture,
                                                                ):
    logger.info(f'{request._pyfuncitem.name}{ymlparsersExtraFixture}')

    mock_lock = create_mock_lock(mocker)
    mocker.patch.object(HiYaPyCo, 'jinja2Lock', new=mock_lock, spec_set=True)
    jinja2ctx_mock = mocker.patch.object(HiYaPyCo, 'jinja2ctx', spec_set=True)

    exp_value = '{name}'
    template = '{{name}}'   #isHiYaPyCoAvailable is not available, global default are used and external lock
                            # (will be ignored)

    jinja2Lock_param_lock = create_mock_lock(mocker)
    value = _convert_template_to_string_format(template, jinja2Lock=jinja2Lock_param_lock)
    pytest.assume(exp_value == value)
    pytest.assume(mock_lock.acquire.call_count == 0)
    pytest.assume(jinja2ctx_mock.call_count == 0)

@pytest.mark.yml
def test_uconvert_template_to_string_explicit_param1b_jinja2Lock(request, mocker, ymlparsersExtraFixture,
                                                               ):
    logger.info(f'{request._pyfuncitem.name}{ymlparsersExtraFixture}')

    ymlparsers.initConfig(jinja2ctx={'variable_start_string': '22_', 'variable_end_string': '_22'})

    init_jinja2ctx = HiYaPyCo.jinja2ctx
    mock_lock = create_mock_lock(mocker)
    mocker.patch.object(HiYaPyCo, 'jinja2Lock', new=mock_lock, spec_set=True)
    jinja2ctx_mock = mocker.patch.object(HiYaPyCo, 'jinja2ctx', spec_set=True)
    mock_variable_start_string = mocker.PropertyMock(return_value=init_jinja2ctx.variable_start_string)
    type(jinja2ctx_mock).variable_start_string = mock_variable_start_string
    mock_variable_end_string = mocker.PropertyMock(return_value=init_jinja2ctx.variable_end_string)
    type(jinja2ctx_mock).variable_end_string = mock_variable_end_string

    #exp_value = '{name}'
    template = '22_name_22'   #HiYaPyCo.jinja2ctx is non default one and external lock

    jinja2Lock_param_lock = create_mock_lock(mocker)
    with pytest.raises(ValueError):
        _convert_template_to_string_format(template, jinja2Lock=jinja2Lock_param_lock)
    #pytest.assume(exp_value == value)
    pytest.assume(mock_lock.acquire.call_count == 0)
    #pytest.assume(jinja2Lock_param_lock.acquire.call_count ==0)


#isHiYaPyCoAvailable,isJinja2DefaultAvailable
@pytest.mark.parametrize('ymlparsersExtraFixture', [(False, True)
                                                    ], indirect = True)
@pytest.mark.yml
def test_uconvert_template_to_string_explicit_param1a_jinja2ctx(request, mocker, ymlparsersExtraFixture,
                                                               ):
    logger.info(f'{request._pyfuncitem.name}{ymlparsersExtraFixture}')

    mock_lock = create_mock_lock(mocker)
    mocker.patch.object(HiYaPyCo, 'jinja2Lock', new=mock_lock, spec_set=True)

    exp_value = '{name}'
    template = '33_name_33'

    jinja2ctx = _Environment(undefined=_DebugUndefined, variable_start_string='33_', variable_end_string='_33')
    value = _convert_template_to_string_format(template, jinja2ctx=jinja2ctx)

    pytest.assume(exp_value == value)
    pytest.assume(mock_lock.acquire.call_count == 0)


@pytest.mark.yml
def test_uconvert_template_to_string_explicit_param2(request, mocker, ymlparsersExtraFixture):
    logger.info(f'{request._pyfuncitem.name}{ymlparsersExtraFixture}')

    mock_lock = create_mock_lock(mocker)
    mocker.patch.object(HiYaPyCo, 'jinja2Lock', new=mock_lock, spec_set=True)
    mock_lock_inuse = create_mock_lock(mocker)

    exp_value = '{name}'
    template = '4_name_4'

    jinja2ctx = _Environment(undefined=_DebugUndefined, variable_start_string='4_', variable_end_string='_4')
    value = _convert_template_to_string_format(template, jinja2ctx=jinja2ctx, jinja2Lock=mock_lock_inuse)
    pytest.assume(exp_value == value)

    pytest.assume(mock_lock.acquire.call_count == 0)
    pytest.assume(mock_lock_inuse.acquire.call_count >0)
    pytest.assume(mock_lock_inuse.release.call_count == mock_lock_inuse.acquire.call_count)


def test_format_template(request, mocker, ymlparsersExtraFixture):
    logger.info(f'{request._pyfuncitem.name}()')

    uconvert_mock=mocker.patch('alexber.utils._ymlparsers_extra._convert_template_to_string_format',
                               side_effect=_convert_template_to_string_format, autospec=True, spec_set=True)

    exp_value = 'Hello, John!'
    template = 'Hello, {{name}}!'
    value = format_template(template, name='John')
    pytest.assume(exp_value == value)
    pytest.assume(uconvert_mock.call_count > 0)

def test_format_template_without_variables(request, mocker, ymlparsersExtraFixture):
    logger.info(f'{request._pyfuncitem.name}()')

    uconvert_mock=mocker.patch('alexber.utils._ymlparsers_extra._convert_template_to_string_format',
                               side_effect=_convert_template_to_string_format, autospec=True, spec_set=True)

    exp_value = 'Hello, World!'
    template = 'Hello, World!'
    value = format_template(template)
    pytest.assume(exp_value == value)
    pytest.assume(uconvert_mock.call_count > 0)


if __name__ == "__main__":
    pytest.main([__file__])
