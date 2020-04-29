import logging
import os as _os
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=__name__)

#inspired by https://codereview.stackexchange.com/questions/6567/redirecting-subprocesses-output-stdout-and-stderr-to-the-logging-module/175382
#for alternatives see https://gist.github.com/jaketame/3ed43d1c52e9abccd742b1792c449079
# that is itself adoptation of https://gist.github.com/bgreenlee/1402841


class LogPipe(object):
    def __init__(self, *args, **kwargs):
        """Setup the object with a logger and a loglevel
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

default_log_name  = __name__
default_log_level = logging.INFO
default_logpipe_cls = LogPipe


class LoggigSubProcessCall(object):
    def __init__(self, *args, **kwargs):

        self.logpipe = kwargs.pop('pipe')
        self.logger = kwargs.pop('logger')

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
    logPipe_p = kwargs.pop('logPipe', {})
    logPipeCls = logPipe_p.pop('cls', default_logpipe_cls)
    logPipeKwargs = logPipe_p.pop('kwargs', {})
    callKwargs = kwargs.pop('kwargs', {})

    with logPipeCls(**logPipeKwargs) as logPipe:
        call = LoggigSubProcessCall(pipe=logPipe, logger=logPipe.logger,
                                    **{'popen':
                                           {'args':args,
                                           'kwargs':callKwargs}}
                                    )
        call.run_sub_process()



def initConfig(**kwargs):
    default_log_name_p = kwargs.get('default_log_name', None)
    if default_log_name_p is not None:
        global default_log_name
        #default_log_name = __name__
        default_log_name = default_log_name_p

    default_log_level_p = kwargs.get('default_log_level', None)
    if default_log_level_p is not None:
        global default_log_level
        #default_log_level = logging.INFO
        default_log_level = default_log_level_p

    default_logpipe_cls_p = kwargs.get('default_logpipe_cls', None)
    if default_logpipe_cls_p is not None:
        global default_logpipe_cls
        # default_logpipe_cls = LogPipe
        default_logpipe_cls = default_logpipe_cls_p

    executor_d = kwargs.get('executor', None)
    if executor_d is not None:
        global executor
        executor = ThreadPoolExecutor(**{'max_workers':1,
                                         'thread_name_prefix':__name__,
                                         **executor_d})


