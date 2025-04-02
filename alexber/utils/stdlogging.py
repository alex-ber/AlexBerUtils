import logging
import sys
from .importer import importer
from .thread_locals import validate_param


# This modules is based upon https://github.com/fx-kirin/py-stdlogging/blob/master/stdlogging.py
# See also https://github.com/fx-kirin/py-stdlogging/pull/1.
# I have encountered on this module here
# https://stackoverflow.com/questions/47325506/making-python-loggers-log-all-stdout-and-stderr-messages 
# Quote: "But be careful to capture stdout because it's very fragile"

def _coerse_log_level(log_level):
    if log_level is None:
        raise ValueError("logger_level can't be None")

    ret = log_level
    if isinstance(log_level, str):
        level_name = log_level.upper()
        ret = logging.getLevelName(level_name)
        if not isinstance(ret, int):
            raise ValueError(f"Invalid logging level string provided: '{log_level}'")
    elif not isinstance(log_level, int):
        raise TypeError(f"log_level must be an integer or a string, not {type(log_level).__name__}")

    return ret


class StreamToLogger:
    """
    This is adapter class from any stream-like object to logging.Logger.
    """

    def __init__(self, **kwargs):
        """
        It is recommended to use package-level initStream() function and not this method directly.
        :param logger: Required. Standard Python's Logger or any Logger-like object.
        :param stream: Required. sys.stderr, sys.stdout or any other stream-like object.
        :param log_level: Optional. If not supplied, logging.DEBUG will be used.
        """

        self.logger = kwargs.pop('logger')
        validate_param(self.logger, "logger")
        self.log_level = _coerse_log_level(kwargs.pop('log_level', kwargs.pop('logger_level', logging.DEBUG)))
        self.stream = kwargs.pop('stream')
        validate_param(self.stream, "stream")

    def write(self, lines):
        if lines:
            lines = lines + '\n'
            for line in lines.split('\n'):
                if line:
                    self.logger.log(self.log_level, line.rstrip())

    def flush(self):
        self.stream.flush()


def initStream(logger=None, logger_level=logging.ERROR, stream_getter=None, stream_setter=None, adapter_cls=None):
    """
    Preffered API.
    stream_getter() is supplier/factory method that returns stream-like object (i.e. sys.stderr) that we're adapting upon.
                   It's intended usage is to supply stream-like object that we want to apapt upon.
    stream_setter() is consumer method that receives wrapped object as parameter.
                   It's intended usage is to overwrite source stream-like, i.e. sys.stderr = s.
    :param logger: Optional. If not supplied logging.getLogger('stderr') will be used.
    :param logger_level: Optional. If not supplied logging.ERROR will be used.
    :param stream_getter: Optional. if not supplied method that returns sys.stderr will be used.
    :param stream_setter: Optional. if not supplied method that get's strema-like object and set's sys.stderr will be used.
    :param adapter_cls: Optional. Can be str or class. if not supplied than StreamToLogger is used.
    :return:
    """
    if logger is None:
        logger = logging.getLogger('stderr')

    if stream_getter is None:
        def stream_getter():
            return sys.stderr

    if stream_setter is None:
        def stream_setter(s):
            sys.stderr = s

    stream = stream_getter()

    if adapter_cls is None:
        adapter_cls = StreamToLogger
    elif isinstance(adapter_cls, str):
        adapter_cls = importer(adapter_cls)

    logger_level = _coerse_log_level(logger_level)
    sl = adapter_cls(logger=logger, stream=stream, logger_level=logger_level)
    stream_setter(sl)
