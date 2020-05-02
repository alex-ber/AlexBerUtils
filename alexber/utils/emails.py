"""
This module contains extensions of the logging handlers.
See https://docs.python.org/3/library/logging.handlers.html#module-logging.handlers for more details.

All handlers are thread safe.
This module optionally depends on ymlparseser module.

it is better to use email_status context manager with configured emailLogger.
See docstring of email_status.
"""

import io as _io
import logging
from logging.handlers import SMTPHandler as _logging_SMTPHandler
from logging.handlers import MemoryHandler as _logging_MemoryHandler
import smtplib
import contextlib
from collections.abc import Mapping
from email.message import EmailMessage as _EmailMessage
from email.policy import SMTPUTF8 as _SMTPUTF8
from ..utils import threadlocal_var
from .parsers import is_empty
from . _ymlparsers_extra import format_template

FINISHED = logging.FATAL+10
logging.addLevelName(FINISHED, 'FINISHED')

default_smpt_cls_name = 'SMTP'
default_smpt_port = None

import threading
_thread_locals = threading.local()

class SMTPHandler(_logging_SMTPHandler):
    """
    This implementation is Thread safe. Each Thread aggregates it's own buffer of the log messages.
    """
    def __init__(self, *args, **kwargs):
        smpt_cls_name = kwargs.pop('smptclsname', default_smpt_cls_name)
        self.smpt_cls = getattr(smtplib, smpt_cls_name)

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
                    port = self.smpt_cls.default_port if hasattr(self.smpt_cls, 'default_port') else default_smpt_port

                smtp = self.smpt_cls(self.mailhost, port, timeout=self.timeout)

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
            msg.set_content(body.getvalue(), subtype='html')

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

        buffer = threadlocal_var(_thread_locals, 'buffer', lambda: [])

        try:
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
    This implementation is Thread safe.
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

    def get_subject(self, *args, **kwargs):
        """
        You can override this method.
        """
        subject = self.subject
        ret = format_template(subject, **self.variables)
        return ret

    def calc_abrupt_vars(self, *args, **kwargs):
        """
        You can override this method.
        However, it is better to use email_status context manager and don't rely on this mechanism.
        """
        abruptvars = kwargs.pop('abruptvars', None)
        if abruptvars is None:
            self.abruptvars = OneMemoryHandler.DEFAULT_ABRUPT_VARS
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
def email_status(emailLogger, logger=None, faildargs={}, successargs={}, successkwargs={}, faildkwargs={}):
    """
    if contextmanager exits with exception (it fails), than e-mail with subject formatted with faildargs and faildkwargs
    will be send.
    Otherwise, e-mail with subject formatted with successargs and successkwargs will be send.

    Exactly 1 e-mail will be send. All message will be aggregated to one long e-mail with the subject described above.

    You can have subject of the e-mails without place holders, for example, 'Aggregates log from the Demo application'.

    Below, is example of customizable e-mails message.

    Indented usage example:

    with email_status(emailLogger=emailLogger, logger=logger, faildargs={'status': 'Failed'},
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

