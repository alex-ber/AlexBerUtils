"""
This module contains extensions of the logging handlers.
See https://docs.python.org/3/library/logging.handlers.html#module-logging.handlers for more details.

See here https://medium.com/analytics-vidhya/my-emails-module-3ad36a4861c5 for documentation.
All handlers are thread safe.

It is better to use EmailStatus context manager with configured emailLogger.
See docstring of EmailStatus.

This module optionally depends on ymlparseser module.

If you want to change delimeters used to indicate variable declaration inside template, see docstring of the
OneMemoryHandler.get_subject() method.

"""

import io as _io
import warnings
import logging
from logging.handlers import SMTPHandler as _logging_SMTPHandler
from logging.handlers import MemoryHandler as _logging_MemoryHandler
from smtplib import SMTP as _SMTP
import contextlib
from collections.abc import Mapping
from email.message import EmailMessage as _EmailMessage
from email.policy import SMTPUTF8 as _SMTPUTF8
from ..utils import threadlocal_var
from . importer import importer
from .parsers import is_empty
from . _ymlparsers_extra import format_template as _format_template

FINISHED = logging.FATAL+10
logging.addLevelName(FINISHED, 'FINISHED')

default_smtp_cls = None
default_smtp_port = None

import threading
_thread_locals = threading.local()



class SMTPHandler(_logging_SMTPHandler):
    """
    It's purpose is to connect to SMTP server and actually send the e-mail.
    This class expects for record.msg to be built EmailMessage.
    You can also change use of underline smtplib.SMTP class to smtplib.SMTP_SSL, smtplib.LMTP, or any another class.

    This implementation is Thread safe.
    """
    def __init__(self, *args, **kwargs):
        smtp_cls_name = kwargs.pop('smtpclsname', None)
        if isinstance(smtp_cls_name, str):
            smtp_cls = importer(smtp_cls_name)
        else:
            smtp_cls = smtp_cls_name
        if smtp_cls is None:
            smtp_cls = default_smtp_cls
        self.smtp_cls = smtp_cls

        super().__init__(*args, **kwargs)


    def emit(self, record):
        """
        Emit a record.

        Format the record and send it to the specified addressees.
        """
        try:
            msg = record.msg

            if msg is not None:
                port = self.mailport
                if not port:
                    port = getattr(self.smtp_cls, 'default_port', None)

                if port is None:
                    port = default_smtp_port

                if port is None:
                    raise ValueError("{self.smtp_cls} class that will be used doesn't contain default_port field."
                                     "You should explicitly specify default_smtp_port.")


                smtp = self.smtp_cls(self.mailhost, port, timeout=self.timeout)

                if self.username:
                    if self.secure is not None:
                        smtp.ehlo()
                        smtp.starttls(*self.secure)
                        smtp.ehlo()
                    smtp.login(self.username, self.password)
                smtp.send_message(msg, self.fromaddr, self.toaddrs)
                smtp.quit()
        except Exception:
            self.handleError(record)

class BaseOneMemoryHandler(_logging_MemoryHandler):
    """
    This implementation is Thread safe. Each Thread aggregates it's own buffer of the log messages.
    """

    def __init__(self, *args, **kwargs):
        subject = kwargs.pop('subject')
        self.subject = subject

        self.createLock()
        lock = self.lock

        self.acquire()
        try:
            super().__init__(*args, **kwargs)
            #restore lock
            self.lock=lock
            del self.buffer
            threadlocal_var(_thread_locals, 'buffer', lambda: [])
        finally:
            self.release()

    def shouldFlush(self, record):
        """
        Check for buffer full or a record at the flushLevel or higher.
        """
        return record.levelno >= self.flushLevel

    def calc_msg_params(self, *args, **kwargs):
        """
        Hook to be overridden in the sub-class.
        """
        pass

    def get_subject(self, *args, **kwargs):
        """
        You may override this method.
        """
        ret = self.subject
        return ret

    def create_one_record(self, records):
        length = len(records)
        last_record = records[-1] if length > 0 else None
        is_finished = False if last_record is None else self.shouldFlush(last_record)

        self.calc_msg_params(records=records,
                             is_finished=is_finished,
                             last_record=last_record
                             )

        with _io.StringIO() as body:
            for record in records:
                message = self.format(record)
                message = message.replace('\n', '<br />'+'\n')
                body.write(message)
                body.write("<br />")
                body.write('\n')


            msg = _EmailMessage(policy=_SMTPUTF8)

            msg['Subject'] = self.get_subject()
            msg.set_content(body.getvalue(), subtype='html', cte='8bit')

        last_record.msg = msg
        return last_record

    def emit(self, record):
        """
        Emit a record.

        Append the record. If shouldFlush() tells us to, call flush() to process
        the buffer.
        """
        buffer = threadlocal_var(_thread_locals, 'buffer', lambda: [])


        buffer.append(record)
        if self.shouldFlush(record):
            self.flush()


    def flush(self):
        """
        For a MemoryHandler, flushing means just sending the buffered
        records to the target, if there is one. Override if you want
        different behaviour.

        The record buffer is also cleared by this operation.
        """
        self.acquire()


        try:
            buffer = threadlocal_var(_thread_locals, 'buffer', lambda: [])

            if self.target and buffer:
                # for record in self.buffer:
                #     self.target.handle(record)

                record = self.create_one_record(buffer)
                self.target.handle(record)

                #self.buffer = []

                setattr(_thread_locals, 'buffer', [])
        finally:
            self.release()



class OneMemoryHandler(BaseOneMemoryHandler):
    """
    This is variant of logging.handlers.MemoryHandler.

    This implementation is Thread safe.

    This handler aggregates log messages until FINISHED log-level is received or we've figure out that application is
    going to terminate abruptly and we have some log messages in the buffer (see below).

    On such event all messages (in the current Thread) are aggregated to the single EmailMessage.
    The subject of the EmailMessage is determined by get_subject() method (see it's docstring for the details).

    There are cases on which FINISHED log-level is not received, but we know that application is going to terminate
    abruptly and we did aggregated some messages. See docstring of the calc_abrupt_vars() method for the details.
    On such a cases we will send EmailMessage as if FINISHED log-level was recieved, but using abruptvars field
    that was set in the constructor in calc_abrupt_vars() method.

    If you want to change delimeters used to indicate variable declaration inside template, see docstring of the
    get_subject() method.

    Note: It is better to use EmailStatus context manager with configured emailLogger. See docstring of EmailStatus.

    """
    DEFAULT_ABRUPT_VARS =  {'status': 'Finished Abruptly'}

    def calc_msg_params(self, *args, **kwargs):
        records = kwargs['records']
        is_finished = kwargs['is_finished']
        last_record = kwargs['last_record']

        if is_finished:
            variables = last_record.msg
            b = is_empty(variables)
            if b:
                variables = {}
            else:
                if not isinstance(variables, Mapping):
                    raise ValueError("Only Mapping (dict) is expected as last log message")

            self.variables = variables
        else:
            self.variables = self.abruptvars


        if is_finished:
            records.pop()

    format_template = staticmethod(_format_template)

    def get_subject(self, *args, **kwargs):
        """
        You may override this method.

        If your subject doesn't contains place holders, for example, 'Aggregates log from the Demo application',
        there is no need to override this method. See also docstring of EmailStatus context manager.

        If you want to change delimeters used to indicate variable declaration inside template, you have following
        options:

        1. You can override this method and pass Jinja2 Environment object to format_template() method.
            If your application is mutli-threaded, this object should be non-shareble (maybe locally defined).
            If this object is shared, see another options below.
        2. You can override this method and pass Jinja2 Environment object with threading.RLock (or any other lock)
        object in order to ensure atomic read of all decimetres.
        3. Call alexber.utils.ymplparser.initConfig() method to initialize HiYaPyCo.jinja2ctx (together will
        HiYaPyCo.jinja2Lock). It will be consulted for delimeters in format_template() method. Please, note:
            This object will be used by also by another modules (init_app_conf.py for example), so this change
            may effect also another parts of your applications if you use when.
            You're changing global variable, please make sure, you own code is aware of this change.
            You should ensure that dependencies that are required by ymplparser module are installed.
            See docstring of ymplparser module for mode details.
        4. You can override this method with your custom logic.

        """
        subject = self.subject
        ret = self.format_template(subject, **self.variables)
        return ret

    def calc_abrupt_vars(self, *args, **kwargs):
        """
        You can override this method.

        If your subject doesn't contains place holders, for example, 'Aggregates log from the Demo application',
        there is no need to override this method.

        There are alternatives though to change default behaviour of this method
        (see below).

        This method need to define self.abruptvars field.

        If your application is stopped abruptly (for example, by SIGINT) and your buffer (in the current Thread)
        has some messages,
        logging system at shutdown will flush and close all handlers, so the buffer without message
        with log-level FINISHED (and hence without variable substitution kwargs) will be flushed.
        self.abruptvars will be used instead.

        If you application has execution path that doesn't ends by sending log messages with log-level FINISHED
        (for example, you have uncaught exception that cause your application to terminate abruptly)
        and your buffer (in the current Thread) has some messages,
        logging system at shutdown will flush and close all handlers, so the buffer without without message
        with log-level FINISHED (and hence without variable substitution kwargs) will be flushed.
        self.abruptvars will be used instead.
        It is recommended to use EmailStatus context manager in order to avoid this.

        The default implementation checks if abruptvars kwargs was supplied in constructor. If it did, it will be used
        put as self.abruptvars. If it doesn't DEFAULT_ABRUPT_VARS is used as self.abruptvars.

        :param abruptvars: kwargs to be put as self.abruptvars. Optional.

        """
        abruptvars = kwargs.pop('abruptvars', None)
        if abruptvars is None:
            self.abruptvars = self.DEFAULT_ABRUPT_VARS
        elif is_empty(abruptvars):
            self.abruptvars = {}
        else:
            if not isinstance(abruptvars, Mapping):
                raise ValueError("Only Mapping (dict) is expected.")
            self.abruptvars = abruptvars

    def __init__(self, *args, **kwargs):
        subject = kwargs.pop('subject')
        capacity = kwargs.pop('capacity', None)
        flushLevel = kwargs.pop('flushLevel', FINISHED)
        target = kwargs.pop('target', None)
        flushOnClose = kwargs.pop('flushOnClose', True)

        super().__init__(*args, **{**kwargs,
                                   'subject': subject, 'capacity': capacity, 'flushLevel': flushLevel,
                                   'target': target,
                                   'flushOnClose': flushOnClose})
        self.calc_abrupt_vars(*args, **kwargs)



@contextlib.contextmanager
def EmailStatus(emailLogger, logger=None, faildargs={}, successargs={}, successkwargs={}, faildkwargs={}):
    """
    if contextmanager exits with exception (it fails), than e-mail with subject formatted with faildargs and faildkwargs
    will be send.
    Otherwise, e-mail with subject formatted with successargs and successkwargs will be send.

    All messages (in the current Thread) will be aggregated to one long e-mail with the subject described in
    OneMemoryHandler.get_subject() method. (see also below).

    You can have subject of the e-mails without place holders, for example, 'Aggregates log from the Demo application'.

    Below, is example of customizable e-mails message.

    Indented usage example:

    with EmailStatus(emailLogger=emailLogger, logger=logger, faildargs={'status': 'Failed'},
                              successargs={'status': 'Done'}):
        emailLogger.info("Start - Process")
        ...
        emailLogger.info("Step 1")
        ...
        emailLogger.info("Step 2")
        ...
        emailLogger.info("Done Successfully - Process")

    'status' is place holder in the subject of the e-mail. For example, 'My Process Status : {{status}}'.
    In this case the same subject of the e-mail will be used whether the code-block finish successfully or with failure.

    If you want to change delimeters used to indicate variable declaration inside template, see docstring of the
    OneMemoryHandler.get_subject() method.

    :param emailLogger: configured emailLogger. See https://docs.python.org/3/howto/logging-cookbook.html#logging-cookbook
    :param faildargs:   variable resolution for e-mail's subject on failure. Optional.
                            Expected to be dict with variable substitution.
    :param successargs: variable resolution for e-mail's subject on success. Optional.
                            Expected to be dict with variable substitution.
    :param logger:      logger ot used if exception was thrown from the code. It will be used in addition to
                        emailLogger. Optional.
    :param successkwargs: to be send to the emailLogger's kwargs param on success. Optional.
    :param faildkwargs:   to be send to the emailLogger's kwargs param on failure. Optional.
    :return:
    """

    try:
        yield emailLogger
    except Exception:
        if logger is not None:
            logger.error("", exc_info=True)
        emailLogger.error("", exc_info=True)
        emailLogger.log(FINISHED, faildargs, **faildkwargs)
    else:
        emailLogger.log(FINISHED, successargs, **successkwargs)

class NoDefaultSmtpPortWarning(RuntimeWarning):
    pass


def initConfig(**kwargs):
    """
    This method can be optionally called prior any call to another function in this module.
    It is indented to be called in the MainThread.
    This method can be call with empty params.

    By default, SMTP class from smtplib is used to send actual e-mail. You can change it to SMTP_SSL, LMTP,
    or another class by specifying default_smtp_cls_name.

    SMTP and some other classes (but not all) has default_port class-level field. If you use
    class that doesn't have such field you have 2 options:
        1.Specify port with default_smtp_port param.
        2.Explicitly use port in mailhost param to SMTPHandler as list of mailhost and port.

    In any case, the order of the determination of the port is as following:

    1. Port in mailhost param to SMTPHandler.
    2. default_smtp_cls_name if exists
    3. default_smtp_port

    This method is idempotent.

    :param default_smtp_cls: Can be class or str. Optional
            Default values is: 'smtplib.SMTP'

    :param default_smtp_port: Optional
                Default values is: `smtplib.SMTP.default_port` if exists else None.
    :return:
    """

    default_smtp_cls_p = kwargs.get('default_smtp_cls_name', None)
    if default_smtp_cls_p is None:
        default_smtp_cls_p = _SMTP
    elif isinstance(default_smtp_cls_p, str):
        default_smtp_cls_p = importer(default_smtp_cls_p)
    global default_smtp_cls
    default_smtp_cls = default_smtp_cls_p

    default_smtp_port_p = kwargs.get('default_smtp_port', None)
    if default_smtp_port_p is None:
        default_smtp_port_p = getattr(_SMTP, 'default_port', None)
    elif isinstance(default_smtp_port_p, str):
        default_smtp_port_p = importer(default_smtp_port_p)
    global default_smtp_port
    default_smtp_port = default_smtp_port_p




initConfig()