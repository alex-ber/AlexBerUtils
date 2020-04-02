import os as _os
import sys
import logging
logger = logging.getLogger(__name__)


def fixabscwd():
    logger.info(f"cwd is {_os.getcwd()}")

    main_module = sys.modules['__main__']

    #inspider by https://github.com/theskumar/python-dotenv/blob/12439aac2d7c98b5acaf51ae3044b1659dc086ae/src/dotenv/main.py#L250
    def _is_interactive():
        """ Decide whether this is running in a REPL or IPython notebook """
        return not hasattr(main_module, '__file__')

    if _is_interactive() or getattr(sys, 'frozen', False):
        # Should work without __file__, e.g. in REPL or IPython notebook.
        pass
    else:
        main_dir = _os.path.dirname(_os.path.realpath(main_module.__file__))

        logger.info(f"Going to change os.chdir('{main_dir}')")

        _os.chdir(main_dir)

