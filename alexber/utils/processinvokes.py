import logging
import os as _os
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor

executor = None
default_log_name  = None
default_log_level = None
default_logpipe_cls = None

#inspired by https://codereview.stackexchange.com/questions/6567/redirecting-subprocesses-output-stdout-and-stderr-to-the-logging-module/175382
#for alternatives see https://gist.github.com/jaketame/3ed43d1c52e9abccd742b1792c449079
# that is itself adoptation of https://gist.github.com/bgreenlee/1402841


class LogPipe(object):
    def __init__(self, *args, **kwargs):
        """
        Setup the logger with logName and loglevel
        Create read and write file descriptor of the pipe
        """
        logName = kwargs.pop('logName', default_log_name)
        logLevel = kwargs.pop('logLevel', default_log_level)

        super().__init__(**kwargs)

        self.logger = logging.getLogger(logName)

        self.level = logLevel
        self.fdRead, self.fdWrite = _os.pipe()
        self.fdWriteLock = threading.RLock()

        with self.fdWriteLock:
            self.is_closed = False

    def fileno(self):
        """Return the write file descriptor of the pipe
        """
        return self.fdWrite

    def run(self):
        """Run the thread, logging everything.
        """
        with _os.fdopen(self.fdRead) as pipeReader:
            for line in iter(pipeReader.readline, ''):
                self.logger.log(self.level, line.rstrip('\r\n'))

    def breakPipe(self):
        self.close()

    def close(self):
        """Close the write end of the pipe.
        """
        with self.fdWriteLock:
            if not self.is_closed:
                _os.close(self.fdWrite)
            self.is_closed = True

    def __enter__(self):
        if self.is_closed:
            raise ValueError("I/O operation on closed pipe")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()




class LoggigSubProcessCall(object):
    def __init__(self, *args, **kwargs):

        self.logpipe = kwargs.pop('pipe')
        d = kwargs.pop('popen', {})

        self.popenargs = d.pop('args', [])
        self.popenkwargs = d.pop('kwargs', {})
        super().__init__(**kwargs)

    def run_sub_process(self):
        f = executor.submit(self.logpipe.run)
        try:
            process = subprocess.run(self.popenargs, **{'stdout':self.logpipe, 'stderr':subprocess.STDOUT,
                                                        'text':True, 'bufsize':1, 'check':True,
                                                        **self.popenkwargs})
        finally:
            self.logpipe.breakPipe()
            f.result()




def run_sub_process(*args, **kwargs):
    """
    This method run subprocess and logs it's out to the logger.

    Note: Before calling this method, please ensure that you've called initConfig() method first.

    This method is sophisticated decorator to subprocess.run(). See it's docstring for more information. Note, that
    some parameters (cwd, for example) that can be used in popenkwargs are listed in Popen constructor.

    logPipe is customizable object that essentially forwards output from subprocess to the logger using
    logName and logLevel (see below).

    default_logpipe_cls by default is LogPipe.
    logName by default is processinvokes.
    logLevel by default is logger.INFO.
    See initConfig() for more details.

    Default parameters for subprocess.run() are (it can be overridden in popenkwargs):
        'stdout':logPipe,
        'stderr':STDOUT,
        'text':True,
        'bufsize': 1,
        'check': True

    This means:
        logPipe is used as subprocess's standard output and standard error.
        Do decode stdin, stdout and stderr using the given encoding
          or the system default otherwise.
        1 is supplied as the buffering argument to the open() function when
          creating the stdin/stdout/stderr pipe file objects.
          Essentially, no OS-level buffering between process, provided that call to write contains a newline character.
        If the exit code of subprocess is non-zero, it raises a CalledProcessError.




    It is generally not advice to override them, but you can if you know, what you're doing.




    :param args: will be passed as popenargs to subprocess.run() method
    :param roughly kwargs['kwargs'] will be passed as popenkwargs to subprocess.run() method
    :param roughly kwargs['logPipe']['cls'] or default_logpipe_cls (if first one is empty)
                                             will be passed as logPipeCls to create logPipe.
    :param roughly kwargs['logPipe']['kwargs'] will be passed as kwargs to logPipeCls to create logPipe.


    :return:
    """
    if default_logpipe_cls is None:
        raise ValueError("You should call initConfig() first")

    logPipe_p = kwargs.pop('logPipe', {})
    logPipeCls = logPipe_p.pop('cls', default_logpipe_cls)
    logPipeKwargs = logPipe_p.pop('kwargs', {})
    callKwargs = kwargs.pop('kwargs', {})

    with logPipeCls(**logPipeKwargs) as logPipe:
        call = LoggigSubProcessCall(pipe=logPipe,
                                    **{'popen':
                                           {'args':args,
                                           'kwargs':callKwargs}}
                                    )
        call.run_sub_process()



def initConfig(**kwargs):
    """
    This method should be called prior any call to another function in this module.
    It is indented to be called in the MainThread.
    This method can be call with empty params.

    :param default_log_name: Optional.
                Default values is: processinvokes
    :param default_log_level: Optional.
                Default values is: logging.INFO
    :param default_logpipe_cls: Optional.
                Default values is: LogPipe
    :param executor: internally used to run sub-process
                Default values are
                      'max_workers':1,
                      'thread_name_prefix': processinvokes
                This means, by default:
                    We're using up to 1 worker.
                    In log message generated from the worker processinvokes-xxx will be used as thread_name.
    :return:
    """
    default_log_name_p = kwargs.get('default_log_name', None)
    if default_log_name_p is None:
        default_log_name_p = __name__
    global default_log_name
    default_log_name = default_log_name_p

    default_log_level_p = kwargs.get('default_log_level', None)
    if default_log_level_p is None:
        default_log_level_p = logging.INFO
    global default_log_level
    default_log_level = default_log_level_p

    default_logpipe_cls_p = kwargs.get('default_logpipe_cls', None)
    if default_logpipe_cls_p is None:
        default_logpipe_cls_p = LogPipe
    global default_logpipe_cls
    default_logpipe_cls = default_logpipe_cls_p

    executor_d = kwargs.get('executor', {})
    executor_d = {'max_workers': 1,
                  'thread_name_prefix': __name__,
                  **executor_d}
    global executor
    if executor is not None:
        executor.shutdown(wait=False)
    executor = ThreadPoolExecutor(**executor_d)

