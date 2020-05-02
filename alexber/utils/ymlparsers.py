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
        "please 'pip3 install alex-ber-utils[yml]'."
    )
    warnings.warn(warning, ImportWarning)
    raise

try:
    import hiyapyco as _hiyapyco
except ImportError:
    import warnings

    warning = (
        "You appear to be missing some optional dependencies (hiyapyco);"
        "please 'pip3 install alex-ber-utils[yml]'."
    )
    warnings.warn(warning, ImportWarning)
    raise

try:
    _hiyapyco.METHOD_SUBSTITUTE
except AttributeError as e:
    import warnings

    warning = (
        "You appear to be missing some optional yml parsing dependencies (hiyapyco should be at least 0.4.16);"
        "please 'pip3 install alex-ber-utils[yml]'."
    )
    warnings.warn(warning, ImportWarning)
    raise ImportError(str(e)) from e

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

    Note: Before calling this method, please ensure that you've called initConfig() method first.
    Note: that collections.OrderedDict is also supported.

    :param data: data-structure to dump.
    :param stream: where to write the representation.
    :param kwds: See initConfig() for default values. See yaml.dump_all()
    :return: str representation of data
    """
    if _safe_dump_d is None:
        raise ValueError("You should call initConfig() first")

    kwargs = {**_safe_dump_d, **kwds}
    _safe_dump(data, stream, **kwargs)


def load(*args, **kwds):
    """
    Load a Hierarchical yml files
    --------------------------------------

    Note: Before calling this method, please ensure that you've called initConfig() method first.

    See initConfig() for default values.
    If you want to disable variable substitution, use DisableVarSubst context manager like this:

    with ymlparsers.DisableVarSubst():
        d = ymlparsers.load([str(full_path)])

    :param args: YMLfile(s)
    :param kwargs:
      * method: one of hiyapyco.METHOD_SIMPLE | hiyapyco.METHOD_MERGE | hiyapyco.METHOD_SUBSTITUTE
      * mergelists: boolean (default: True) try to merge lists (only makes sense if hiyapyco.METHOD_MERGE or hiyapyco.METHOD_SUBSTITUTE)
      * interpolate: boolean (default: False)
      * castinterpolated: boolean (default: False) try to cast values after interpolating
      * encoding: (default: 'utf-8') encoding used to read yml files
      * loglevel: one of  the valid levels from the logging module
      * failonmissingfiles: boolean (default: True)
      * loglevelmissingfiles

    :returns a representation of the merged and (if requested) interpolated config using OrderedDict.
    """
    if _load_d is None:
        raise ValueError("You should call initConfig() first")

    kwargs = {**_load_d, **kwds}
    #return _hiyapyco.load(*args, **kwargs)
    hiyapyco = HiYaPyCo(*args, **kwargs)
    return hiyapyco.data()


def as_str(data, **kwds):
    """
    Return str representation of the data.

    Simple Python objects like primitive types (str, integer, etc), list, dict, OrderedDict are supported.

    Note: Before calling this method, please ensure that you've called initConfig() method first.
    Note: that collections.OrderedDict is also supported.

    :param data: data-structure to dump.
    :param kwds: See initConfig() for default values. See yaml.dump_all()
    :return: str representation of data
    """
    with _io.StringIO() as buf:
        buf.write(_os.linesep)
        safe_dump(data, stream=buf, **kwds)
        return buf.getvalue()

class DisableVarSubst(object):
    """
    Use of this context manager disables variable substation in the load() function.

    Note: Before calling this method, please ensure that you're explicitly passing jinja2ctx and jinja2Lock
    or you've called initConfig() method first.


    :param jinja2ctx - Jinja2 Environment. If not provided HiYaPyCo.jinja2ctx is used.
    :param jinja2Lock - lock to use for synchronization. Should be the same here and in load() function.
                        If not provided HiYaPyCo.jinja2ctx is used.
    """
    def __init__(self, *args, **kwargs):
        jinja2ctx = kwargs.pop('jinja2ctx', HiYaPyCo.jinja2ctx)
        jinja2Lock = kwargs.pop('jinja2Lock', HiYaPyCo.jinja2Lock)

        if jinja2ctx is None or jinja2Lock is None:
            raise ValueError("You should pass jinja2ctx and jinja2Lock or call initConfig() first")

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



