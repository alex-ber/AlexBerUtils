import warnings

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


def _convert_template_to_string_format(template, **kwargs):
    """
    This is utility method that make template usable with string format


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

def convert_template_to_string_format(template, **kwargs):
    if template is None:
        return None

    jinja2ctx = kwargs.pop('jinja2ctx', None)
    jinja2Lock = kwargs.pop('jinja2Lock', None)
    is_not_passed_jinja2Lock = 'jinja2Lock' in kwargs


    if _isHiYaPyCoAvailable and jinja2ctx is None:
        jinja2ctx  = HiYaPyCo.jinja2ctx

    if jinja2ctx is None:
        default_start = _VARIABLE_START_STRING
        default_end = _VARIABLE_END_STRING
    else:
        if _isHiYaPyCoAvailable and is_not_passed_jinja2Lock:
            jinja2Lock = HiYaPyCo.jinja2Lock

        if jinja2Lock is None:
            default_start = jinja2ctx.variable_start_string
            default_end = jinja2ctx.variable_end_string
        else:
            with jinja2Lock:
                default_start = jinja2ctx.variable_start_string
                default_end = jinja2ctx.variable_end_string

    ret = _convert_template_to_string_format(template, default_start=default_start, default_end=default_end)
    return ret