import logging
import sys as _sys
from logging import warnings

_py_warnings_handler = None
_default_file = _sys.stderr
_default_log_name  = 'py.warnings'
_default_log_level = logging.WARNING

log_name = None
log_level = None

# inpsired by https://github.com/python/cpython/blob/c49016e67c3255b37599b354a8d7995d40663991/Lib/logging/__init__.py#L2175
def showwarning(message, *, filename, category=UserWarning, lineno='', line=''):
    """
    Implementation of showwarnings which redirects to logging.
    It will call warnings.formatwarning and will log the resulting string to a logger.
    """
    s = warnings.formatwarning(message, category, filename, lineno, line)
    s = s.rstrip()

    _py_warnings_logger = logging.getLogger(log_name)

    h = _py_warnings_handler
    if not _py_warnings_logger.handlers:
        logging._acquireLock()
        try:
            _py_warnings_logger.addHandler(h)
            _py_warnings_logger.setLevel(log_level)
        finally:
            logging._releaseLock()

    _py_warnings_logger.log(log_level, f"{s}")




def initConfig(**kwargs):
    '''
    This method will override warnings.showwarning with variant of logging._showwarning
    Unlike logging._showwarning this variant will always go through logger.

    If logger for log_name (default is `py.warnings`) will be configured before call to showwarning() method,
    than warning will go to the logger's handler with log_level (default is logging.WARNING).

    If logger for log_name  (default is `py.warnings`) willn't be configured before call to showwarning() method,
    than warning will be done to file with log_level (default is logging.WARNING).


    :param file - file-like object that can be used to redirect loggger. Default is sys.stderr.
    :param log_name - Name of the log. Default is 'py.warnings'.
    :param log_level - Log Level to be used to log. Default is logging.WARNING.
    :return:
    '''

    logging.captureWarnings(True)
    warnings.showwarning = showwarning

    file = kwargs.get('file', _default_file)

    h = logging.NullHandler()
    if file is not None:
        try:
            h = logging.FileHandler(file)
        except:
            h = logging.StreamHandler(stream=file)


    global _py_warnings_handler
    _py_warnings_handler = h

    log_name_p = kwargs.get('log_name', _default_log_name)
    global log_name
    log_name = log_name_p

    log_level_p = kwargs.get('log_level', _default_log_level)
    global log_level
    log_level = log_level_p

