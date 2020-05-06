"""
This module adopts its behavior dependent on availability of Python packages.

This module optionally depends on ymlparseser module.
Method format_template() is used in emails module.

Note: This module will work if you have only standard Python package. You just can't change delimiters values.
Note: API and implementation of this module is unstable and can change without prior notice.
"""

import warnings

def format_template(template, **kwargs):
    """
    This is main method of this module.
    Note: API of this method is unstable and can change without prior notice.

    Template is expected to be compatible with Jinja2 one.

    Current implementation make delimiters compatible with str.format() and use it.


    :param template: str, typically with {{my_variable}}
    :param jinja2ctx:  Jinja2 Environment that is consulted what is delimiter for variable's names.
                       if is not provided, HiYaPyCo.jinja2ctx is used. See ymlparsers.initConfig().
                       if is not provided, than defaults are used (see jinja2.defaults).
    :param jinja2Lock: Lock to be used to atomically get variable_start_string and variable_end_string from jinja2ctx.
                       if is not provided, HiYaPyCo.jinja2Lock is used.. See ymlparsers.initConfig().
    :return: fromated str
    """
    if template is None:
        return None
    s = _convert_template_to_string_format(template, **kwargs)
    ret = s.format(template, **kwargs)
    return ret


try:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=r'.*?yaml*?', module=r'.*?ymlparsers.*?')
    from . ymlparsers import HiYaPyCo
    _isHiYaPyCoAvailable = True
except ImportError:
    _isHiYaPyCoAvailable = False

_a1 = None
_a2 = None
try:
    try:
        from jinja2.defaults import VARIABLE_START_STRING as _a1, VARIABLE_END_STRING as _a2
        _isJinja2DefaultAvailable = True
    except ImportError:
        try:
            from jinja2.environment import VARIABLE_START_STRING as _a1, VARIABLE_END_STRING as _a2
            _isJinja2DefaultAvailable = True
        except ImportError:
            _isJinja2DefaultAvailable = False
finally:
    del _a1
    del _a2

_VARIABLE_START_STRING = None
_VARIABLE_END_STRING = None


def _init_globals():
    """
    This method is called during module import.
    This method is idempotent.
    """
    global _VARIABLE_START_STRING, _VARIABLE_END_STRING

    if _isJinja2DefaultAvailable:
        p1 = None
        p2 = None
        try:
            from jinja2.defaults import VARIABLE_START_STRING as p1, VARIABLE_END_STRING as p2
        except ImportError:
            from jinja2.environment import VARIABLE_START_STRING as p1, VARIABLE_END_STRING as p2

        if p1 is None or p2 is None:
            raise ImportError('VARIABLE_START_STRING or VARIABLE_END_STRING are not defined')

        _VARIABLE_START_STRING = p1
        _VARIABLE_END_STRING = p2
    else:
        _VARIABLE_START_STRING = '{{'
        _VARIABLE_END_STRING = '}}'


_init_globals()

def _normalize_var_name(text, start_del, end_del):
    """
    Search&replace all pairs of (start_del, end_del) with pairs of ({, }).

    :param text: str to normalize
    :param start_del: delimiter that indicates start of variable name, typically {{
    :param end_del: delimiter that indicates end of variable name, typically }}
    :return:
    """

    if start_del is None or start_del not in text or end_del not in text:
        return text

    first_ind = 0
    len_end_del = len(end_del)

    while True:
        first_ind = text.find(start_del, first_ind)
        if first_ind < 0:
            break
        last_ind =  text.find(end_del, first_ind)
        var = text[first_ind:last_ind+len_end_del]
        var = var.replace('.', '_')
        #text[first_ind:last_ind] = var
        text = text[:first_ind]+var+text[last_ind+len_end_del:]
        first_ind = last_ind+len_end_del
    return text


def __convert_template_to_string_format(template, **kwargs):
    """
    This is utility method that make template usable with string format.


    :param template: str, typically with {{my_variable}}
    :param default_start: Typically {{ but can be any other delimiter that points to start of the token variable.
    :param default_end:   Typically }} but can be any other delimiter that points to end of the token variable.
    :return: template: str with {my_variable}
    """
    if template is None:
        return None

    default_start = kwargs.pop('default_start', None)
    default_end = kwargs.pop('default_end', None)

    template = _normalize_var_name(template, default_start, default_end)

    ret = template.replace(f'{default_start} ', f'{default_start}') \
        .replace(f'{default_start}', '{') \
        .replace(f' {default_end}', f'{default_end}') \
        .replace(f'{default_end}', '}')
    return ret

def _convert_template_to_string_format(template, **kwargs):
    """
    This is utility method that make template usable with string format.

    if both jinja2ctx and jinja2Lock are provided, than they are used to determine various delimiters
    (jinja2Lock is used to read the values from jinja2ctx atomically).

    if both jinja2ctx and jinja2Lock are not provided, than
        If ymlparsers is usable (it's 3rd party dependencies are available, one if each is jinja2)
        than it's jinja2ctx (Jinja2's Environment) will be consulted for the various delimiters.
        Otherwise, if jinja2 is available than we will use it's defaults for constricting Jinja2's Environment
        for the various delimiters.
        Otherwise, some sensible defaults (default values from some version of Jinja2) will be used.

    You can't provide jinja2Lock without providing jinja2ctx (you can't provide your jinja2Lock for HiYaPyCo.jinja2ctx).

    You can provide jinja2ctx without jinja2Lock. Than you will give up atomicity for determining various delimiters.

    :param template: str, typically with {{my_variable}}
    :param jinja2ctx:  Jinja2 Environment that is consulted what is delimiter for variable's names.
                       if is not provided, HiYaPyCo.jinja2ctx is used. See ymlparsers.initConfig().
                       if is not provided, than defaults are used (see jinja2.defaults).
    :param jinja2Lock: Lock to be used to atomically get variable_start_string and variable_end_string from jinja2ctx.
                       if is not provided, HiYaPyCo.jinja2Lock is used.. See ymlparsers.initConfig().
    :return: template: str with {my_variable}
    """

    if template is None:
        return None

    jinja2ctx = kwargs.pop('jinja2ctx', None)
    jinja2Lock = kwargs.pop('jinja2Lock', None)

    if _isHiYaPyCoAvailable and jinja2ctx is None and jinja2Lock is not None:
        raise ValueError("You can't provide your jinja2Lock for HiYaPyCo.jinja2ctx")

    if _isHiYaPyCoAvailable and jinja2ctx is None:
        jinja2ctx  = HiYaPyCo.jinja2ctx
        jinja2Lock = HiYaPyCo.jinja2Lock    #we should use HiYaPyCo.jinja2Lock for HiYaPyCo.jinja2ctx

    #default_start, default_end
    if jinja2ctx is None:
        if jinja2Lock is None:
            default_start = _VARIABLE_START_STRING
            default_end = _VARIABLE_END_STRING
        else:
            with jinja2Lock:
                default_start = _VARIABLE_START_STRING
                default_end = _VARIABLE_END_STRING

    else:
        if _isHiYaPyCoAvailable and HiYaPyCo.jinja2ctx is not None and HiYaPyCo.jinja2Lock is None:
            raise ValueError('HiYaPyCo.jinja2ctx is not None, but HiYaPyCo.jinja2Lock is None')

        if jinja2Lock is None:
            # jinja2ctx was provided, but jinja2Lock wasn't, it is ok
            # (maybe jinja2ctx is local variable?)
            default_start = jinja2ctx.variable_start_string
            default_end = jinja2ctx.variable_end_string
        else:
            with jinja2Lock:
                default_start = jinja2ctx.variable_start_string
                default_end = jinja2ctx.variable_end_string

    ret = __convert_template_to_string_format(template, default_start=default_start, default_end=default_end)
    return ret


