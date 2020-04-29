import warnings

try:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=r'.*?collections\.abc.*?', module=r'.*?jinja2.*?')
        from jinja2 import Environment as _Environment, \
                        DebugUndefined as _DebugUndefined
except ImportError:
    import warnings

    warning = (
        "You appear to be missing some optional dependencies (jinja2);"
        "please 'pip3 install alex-ber-utils[yaml]'."
    )
    warnings.warn(warning, ImportWarning)
    raise

try:
    import hiyapyco as _hiyapyco
except ImportError:
    import warnings

    warning = (
        "You appear to be missing some optional dependencies (hiyapyco);"
        "please 'pip3 install alex-ber-utils[yaml]'."
    )
    warnings.warn(warning, ImportWarning)
    raise

try:
    _hiyapyco.METHOD_SUBSTITUTE
except AttributeError:
    import warnings

    warning = (
        "You appear to be missing some optional yaml parsing dependencies (hiyapyco should be at least 0.4.16);"
        "please 'pip3 install alex-ber-utils[yaml]'."
    )
    warnings.warn(warning, ImportWarning)
    raise


import io as _io
import os as _os
from threading import RLock as _Lock


from hiyapyco import logger, HiYaPyCoImplementationException, HiYaPyCoInvocationException, TemplateError, \
    re, strtobool, HiYaPyCo as _HiYaPyCo
from hiyapyco.odyldo import safe_dump as _safe_dump

_safe_dump_d = None
_load_d = None

from platform import uname as _uname



class HiYaPyCo(_HiYaPyCo):
    jinja2ctx = None
    jinja2Lock = None


    #this adopted version
    #1. In order to change reference of jinja2env
    #2. In order to use reentrant lock
    def _interpolatestr(self, s):
        try:
            with self.jinja2Lock:
                si = HiYaPyCo.jinja2ctx.from_string(s).render(self._data)
        except TemplateError as e:
            # FIXME: this seems to be broken for unicode str?
            raise HiYaPyCoImplementationException('error interpolating string "%s" : %s' % (s, e,))
        if not s == si:
            if self.castinterpolated:
                if not re.match( r'^\d+\.*\d*$', si):
                    try:
                        si = bool(strtobool(si))
                    except ValueError:
                        pass
                else:
                    try:
                        if '.' in si:
                            si = float(si)
                        else:
                            si = int(si)
                    except ValueError:
                        pass
            logger.debug('interpolated "%s" to "%s" (type: %s)' % (s, si, type(si),))
        return si


def safe_dump(data, stream=None, **kwds):
    """
    Dumping data to stream.

    Simple Python objects like primitive types (str, integer, etc), list, dict, OrderedDict are supported.

    Note: that collections.OrderedDict is also supported.

    :param data: data-structure to dump.
    :param stream: where to write the representation.
    :param kwds: See initConfig() for default values. See yaml.dump_all()
    :return: str representation of data
    """
    kwargs = {**_safe_dump_d, **kwds}
    _safe_dump(data, stream, **kwargs)


def load(*args, **kwds):
    """
    Load a Hierarchical Yaml files
    --------------------------------------

    See initConfig() for default values.
    If you want to disable variable substitution, use DisableVarSubst context manager like this:

    with ymlparsers.DisableVarSubst():
        d = ymlparsers.load([str(full_path)])

    :param args: YAMLfile(s)
    :param kwargs:
      * method: one of hiyapyco.METHOD_SIMPLE | hiyapyco.METHOD_MERGE | hiyapyco.METHOD_SUBSTITUTE
      * mergelists: boolean (default: True) try to merge lists (only makes sense if hiyapyco.METHOD_MERGE or hiyapyco.METHOD_SUBSTITUTE)
      * interpolate: boolean (default: False)
      * castinterpolated: boolean (default: False) try to cast values after interpolating
      * encoding: (default: 'utf-8') encoding used to read yaml files
      * loglevel: one of  the valid levels from the logging module
      * failonmissingfiles: boolean (default: True)
      * loglevelmissingfiles

    :returns a representation of the merged and (if requested) interpolated config using OrderedDict.
    """
    kwargs = {**_load_d, **kwds}
    #return _hiyapyco.load(*args, **kwargs)
    hiyapyco = HiYaPyCo(*args, **kwargs)
    return hiyapyco.data()


def as_str(data, **kwds):
    with _io.StringIO() as buf:
        buf.write(_os.linesep)
        safe_dump(data, stream=buf, **kwds)
        return buf.getvalue()



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



def convert_template_to_string_format(template, jinja2ctx=None, jinja2Lock=None):
    """
    This is utility method that make template usable with string format

    :param template: str, typically with {{my_variable}}
    :param jinja2ctx:  Jinja2 Environment that is consult what is delimter for variable's names.
                       if is not provided, HiYaPyCo.jinja2ctx is used.
    :param jinja2Lock: Lock to be used to atomically get variable_start_string and variable_end_string from jinja2ctx.
                       if is not provided, HiYaPyCo.jinja2Lock is used.
    :return: template: str with {my_variable}
    """
    if template is None:
        return None
    if jinja2ctx is None:
        jinja2ctx  = HiYaPyCo.jinja2ctx

    if jinja2Lock is None:
        jinja2Lock = HiYaPyCo.jinja2Lock

    with jinja2Lock:
        default_start = jinja2ctx.variable_start_string
        default_end = jinja2ctx.variable_end_string

    template = _normalize_var_name(template, default_start, default_end)

    ret = template.replace(f'{default_start} ', f'{default_start}') \
        .replace(f'{default_start}', '{') \
        .replace(f' {default_end}', f'{default_end}') \
        .replace(f'{default_end}', '}')
    return ret


class DisableVarSubst(object):
    """
    Use of this context manager disables variable substation in the load() function.

    :param jinja2ctx - Jinja2 Environment. If not provided HiYaPyCo.jinja2ctx is used.
    :param jinja2Lock - lock to use for synchronization. Should be the same here and in load() function.
                        If not provided HiYaPyCo.jinja2ctx is used.
    """
    def __init__(self, *args, **kwargs):
        jinja2ctx = kwargs.pop('jinja2ctx', HiYaPyCo.jinja2ctx)
        jinja2Lock = kwargs.pop('jinja2Lock', HiYaPyCo.jinja2Lock)

        self.variable_start_string = jinja2ctx.variable_start_string
        self.variable_end_string = jinja2ctx.variable_end_string
        self.block_start_string = jinja2ctx.block_start_string
        self.block_end_string = jinja2ctx.block_end_string
        self.jinja2ctx = jinja2ctx
        self.jinja2Lock = jinja2Lock

    def __enter__(self):
        self.jinja2Lock.acquire()
        try:
            self.jinja2ctx.variable_start_string = '@@{@|'
            self.jinja2ctx.variable_end_string = '|@}@@'
            self.jinja2ctx.block_start_string = '%%{%|'
            self.jinja2ctx.block_end_string = '|%}%%'
        except:
            self.jinja2Lock.release()
            raise

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.jinja2ctx.variable_start_string = self.variable_start_string
            self.jinja2ctx.variable_end_string = self.variable_end_string
            self.jinja2ctx.block_start_string = self.block_start_string
            self.jinja2ctx.block_end_string = self.block_end_string
        finally:
            self.jinja2Lock.release()

# # support for tag 'tag:yaml.org,2002:python/object/apply:collections.OrderedDict'
# _represent_dict_order = lambda self, data:  self.represent_mapping('tag:yaml.org,2002:map', data.items())
# yaml.add_representer(OrderedDict, _represent_dict_order)

#
# _hiyapyco.load("\n") #_hiyapyco._usedefaultyamlloader = False



def initConfig(**kwargs):
    """
    This method should be called prior any call to another function in this module.
    It is indented to be called in the MainThread.
    This method can be call with empty params.

    Note: this module doesn't use any package-level variables in hiYaPyCo module.

    :param jinja2Lock: lock to use for synchronization in DisableVarSubst and load().
                      If not supplied, default RLock is used.
                      Will be available as HiYaPyCo.jinja2Lock.
    :param jinja2ctx: context for overriding values in initialization (default is _DebugUndefined) of Jinja2 Environment:
                      gloabls will be override values in Environment.globals.update(**globals)
                      Default is 'uname':platform.uname
                      Will be available as HiYaPyCo.jinja2ctx.
    :param load: this params will be used as default values in load() function. See hiyapyco.load()
                Default values are
                      'method':_hiyapyco.METHOD_SUBSTITUTE,
                      'mergelists':False,
                      'interpolate':True,
                      'castinterpolated':True
                This means, by default:
                      We're replacing list, not merging them.
                      We're interpolating values in the data (to scalar/list/OrderDict).
                      We're also using casting to appropriate type.
    :param safe_dump: this params will be used as default values in safe_dump() and as_str(). See yaml.dump_all()
                Default values are
                      'default_flow_style':False,
                      'sort_keys':False
                This means, by default:
                       we prefer block style always.
                       we preserve the key order (no sorting for key in the dictionary).

    :return:
    """
    jinja2Lock_p = kwargs.get('jinja2Lock', None)
    if jinja2Lock_p is None:
        jinja2Lock_p = _Lock()
    HiYaPyCo.jinja2Lock = jinja2Lock_p

    jinja2ctx_d = kwargs.get('jinja2ctx', {})
    globals_d = jinja2ctx_d.pop('globals', {})
    # jinja2ctx_p = _Environment(undefined=_StrictUndefined)
    jinja2ctx_p = _Environment(**{'undefined':_DebugUndefined, **jinja2ctx_d})
    jinja2ctx_p.globals.update(**{'uname':_uname, **globals_d})


    with HiYaPyCo.jinja2Lock:
        HiYaPyCo.jinja2ctx = jinja2ctx_p


    load_d = kwargs.get('load', {})
    _load_d_p = {'method':_hiyapyco.METHOD_SUBSTITUTE,
               'mergelists':False,
               'interpolate':True,
               'castinterpolated':True,
               **load_d}

    method = _load_d_p['method']
    # TODO: HiYaPyCo._substmerge() bug workarround, see https://github.com/zerwes/hiyapyco/pull/38
    HiYaPyCo._deepmerge = _HiYaPyCo._substmerge
    if method == _hiyapyco.METHOD_MERGE:
        #restore original _deepmerge
        HiYaPyCo._deepmerge = _HiYaPyCo._deepmerge
    global _load_d
    _load_d = _load_d_p


    safe_dump_d = kwargs.get('safe_dump', {})
    global _safe_dump_d
    #See https://github.com/yaml/pyyaml/pull/256
    _safe_dump_d = {'default_flow_style':False,
                        'sort_keys':False,
                        **safe_dump_d}


