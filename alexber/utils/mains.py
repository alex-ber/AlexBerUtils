import logging

import os as _os
import sys as _sys


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


def load_dotenv(dotenv_path, **kwargs):
    """
    Convinient wrapper for dotenv.load_dotenv().

    :param dotenv_path: path for .env file
    :param kwargs: forwarded to dotenv.load_dotenv. Optional. Can override dotenv_path
    :return:
    """
    try:
        from dotenv import load_dotenv as _load_dotenv
    except ImportError:
        import warnings

        warning = (
            "You appear to be missing some optional dependencies (python-dotenv);"
        )
        warnings.warn(warning, ImportWarning)
        raise

    d = {'dotenv_path':dotenv_path,
         **kwargs
         }

    _load_dotenv(**d)



