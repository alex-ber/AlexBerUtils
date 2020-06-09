import logging

import os as _os
import sys as _sys
from collections import deque
from .parsers import is_empty
from .importer import importer

logger = logging.getLogger(__name__)


def fixabscwd():
    logger.info(f"cwd is {_os.getcwd()}")

    main_module = _sys.modules['__main__']

    #inspider by https://github.com/theskumar/python-dotenv/blob/12439aac2d7c98b5acaf51ae3044b1659dc086ae/src/dotenv/main.py#L250
    def _is_interactive():
        """ Decide whether this is running in a REPL or IPython notebook """
        return not hasattr(main_module, '__file__')

    if _is_interactive() or getattr(_sys, 'frozen', False):
        # Should work without __file__, e.g. in REPL or IPython notebook.
        pass
    else:
        main_dir = _os.path.dirname(_os.path.realpath(main_module.__file__))

        logger.info(f"Going to change os.chdir('{main_dir}')")

        _os.chdir(main_dir)

def path():
    """
    For older Python version uses`importlib_resources` module.
    For newer version built in `importlib.resources`.
    :return:
    """
    if _sys.version_info >= (3, 7):
        from importlib.resources import path as _path
    else:
        try:
            from importlib_resources import path as _path
        except ImportError:
            import warnings

            warning = (
                "You appear to be missing some optional dependencies (importlib_resources);"
            )
            warnings.warn(warning, ImportWarning)
            raise
    return _path


def load_env(**kwargs):
    """
    Convenient method from loading environment variables
    inside packed format (eggs, etc).

    if dotenv_path or stream is present it will be used.
    Otherwise, dotenv_path will be constructed from ENV_PCK and ENV_NAME.


    Implementaion note:
    If available it uses importlib.resources API,
    if not it assumes existence of backport of importlib_resources.

    :param ENV_PCK: package where to find .env file Optional.
    :param ENV_NAME: Name of .env file. Optional.
    :param dotenv_path:  absolute or relative path to .env file. Optional.
    :param stream: `StringIO` object with .env content. Optional.
    :return:
    """

    # os.environ['AWS_DEFAULT_REGION'] = 'eu-central-1'
    try:
        from dotenv import load_dotenv
    except ImportError:
        import warnings


        warning = (
            "You appear to be missing some optional dependencies (python-dotenv);"
            "please 'python3 -m pip install alex-ber-utils[python-dotenv]'."
        )

        warnings.warn(warning, ImportWarning)
        raise

    l_path = path()

    dotenv_path = kwargs.get('dotenv_path', None)
    stream = kwargs.get('stream', None)
    if is_empty(dotenv_path) and is_empty(stream):
        ENV_PCK = kwargs.pop('ENV_PCK', None)
        if is_empty(ENV_PCK):
            raise ValueError("ENV_PCK can't be empty")

        ENV_NAME = kwargs.pop('ENV_NAME', '.env')
        with l_path(ENV_PCK, ENV_NAME) as full_path:
            d = {**kwargs, 'dotenv_path': full_path}

            load_dotenv(**d)
    else:
        load_dotenv(**kwargs)



class OsEnvrionPathExpender(object):
    DEFAULT_DELIMSEP = _os.pathsep   #';'
    DEFAULT_ENVSEP = _os.path.sep   #/
    DEFAULT_KEYSEP = ','


    def __init__(self, **kwargs):
        delimsep = kwargs.get('ENV_DELIM_SEP', None)
        if is_empty(delimsep):
            delimsep = OsEnvrionPathExpender.DEFAULT_DELIMSEP
        self.delimsep = delimsep

        envsep = kwargs.get('ENV_SEP', None)
        if is_empty(envsep):
            envsep = OsEnvrionPathExpender.DEFAULT_ENVSEP
        self.envsep = envsep


        keysep = kwargs.get('ENV_KEY_SEP', None)
        if is_empty(keysep):
            keysep = OsEnvrionPathExpender.DEFAULT_KEYSEP
        self.keysep = keysep

        env_keys = kwargs.get('ENV_KEYS', None) # 'NLTK_DATA'
        if is_empty(env_keys):
            raise ValueError('ENV_KEYS is not found in kwargs')
        self.env_keys =  self._str_to_list(self.keysep, env_keys)

        pck = kwargs.get('ENV_MAIN_PCK', None)
        if is_empty(pck):
            raise ValueError('ENV_MAIN_PCK is not found in kwargs')

        self.pck = pck

    def _str_to_list(self, sep, value):
        ret = [w.strip() for w in value.split(sep)]
        return ret

    def _list_to_str(self, sep, *args):
        ret = sep.join([*args])
        return ret

    def fix_abs_path(self):
        l_path = path()

        with l_path(self.pck, '__init__.py') as init_file:
            full_prefix = str(init_file.parent.parent)

            for env_key in self.env_keys:
                rel_paths = self._str_to_list(self.delimsep, _os.environ[env_key])

                buffersize = 0 if rel_paths is None else len(rel_paths)
                env_values = deque(maxlen=buffersize)

                for rel_path in rel_paths:
                    abs_path = self._list_to_str(self.envsep, *[full_prefix, rel_path])
                    env_values.append(abs_path)

                values = self._list_to_str(self.delimsep, *env_values)
                _os.environ[env_key] = values


def fix_env(**kwargs):
    """
    This method "fixes" os.environ relatively to the given ENV_MAIN_PCK package.
    This method ignores current working directory or __main__ module's __file__ atrribute.
    For each key in ENV_KEYS, this method prepends full_prefix to os.environ[key].
    full_prefix is calculated as absolute path of __init__.py of ENV_MAIN_PCK.



    :param ENV_KEYS keys of os.environ which will be fixed.
    :param ENV_MAIN_PCK: package to calcualte full_prefix.
    :param ENV_KEY_SEP: seperator used in ENV_PCK. Optional. Default is ','
    :param ENV_SEP: seperator that is used inside path. Optional. Default is os.path.sep.
    :param ENV_DELIM_SEP: seperator that is used inside os.environ. Optional. Default is os.pathsep.
    :param cls: class or str with implementation logic. Optional. Default is OsEnvrionPathExpender.
    """

    cls = kwargs.pop('cls', OsEnvrionPathExpender)
    if isinstance(cls, str):
        cls = importer(cls)
    expender = cls(**kwargs)
    expender.fix_abs_path()
