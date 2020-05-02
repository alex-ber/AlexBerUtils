import io as _io
import logging
from logging.handlers import SMTPHandler as _logging_SMTPHandler
from logging.handlers import MemoryHandler as _logging_MemoryHandler
import smtplib
import contextlib
from email.message import EmailMessage as _EmailMessage
from email.policy import SMTPUTF8 as _SMTPUTF8

FINISHED = logging.FATAL+10
logging.addLevelName(FINISHED, 'FINISHED')

default_smpt_cls_name = 'SMTP'
default_smpt_port = None

import threading
thread_locals = threading.local()
from ..utils import threadlocal_var


from . ymlparsers_extra import convert_template_to_string_format as _convert_template_to_string_format

class SMTPHandler(_logging_SMTPHandler):
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
            threadlocal_var(thread_locals, 'buffer', lambda: [])
        finally:
            self.release()

    def shouldFlush(self, record):
        """
        Check for buffer full or a record at the flushLevel or higher.
        """
        return record.levelno >= self.flushLevel

    def calc_msg_params(self, *args, **kwargs):
        pass

    def get_subject(self, *args, **kwargs):
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
        buffer = threadlocal_var(thread_locals, 'buffer', lambda: [])


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

        buffer = threadlocal_var(thread_locals, 'buffer', lambda: [])

        try:
            if self.target and buffer:
                # for record in self.buffer:
                #     self.target.handle(record)

                record = self.create_one_record(buffer)
                self.target.handle(record)

                #self.buffer = []
                setattr(thread_locals, 'buffer', [])
        finally:
            self.release()


class OneMemoryHandler(BaseOneMemoryHandler):

        def calc_msg_params(self, *args, **kwargs):
            records = kwargs['records']
            is_finished = kwargs['is_finished']
            last_record = kwargs['last_record']

            status = last_record.msg if is_finished else {'status': 'Finished Abruptly'}
            self.status = status

            if is_finished:
                records.pop()

        def get_subject(self, *args, **kwargs):
            subject = self.subject
            subject = _convert_template_to_string_format(subject)
            ret = subject.format(**self.status)
            return ret

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


@contextlib.contextmanager
def email_status(emailLogger, faildargs, successargs, logger=None, successkwargs={}, faildkwargs={}):
    try:
        yield emailLogger
    except Exception:
        if logger is not None:
            logger.error("", exc_info=True)
        emailLogger.error("", exc_info=True)
        emailLogger.log(FINISHED, faildargs, **faildkwargs)
    else:
        emailLogger.log(FINISHED, successargs, **successkwargs)

def initConfig(**kwargs):
    default_smpt_cls_name_p = kwargs.get('default_smpt_cls_name', None)
    if default_smpt_cls_name_p is not None:
        global default_smpt_cls_name
        #default_smpt_cls_name = 'SMTP"
        default_smpt_cls_name = default_smpt_cls_name_p

    default_smpt_port_p = kwargs.get('default_smpt_port', None)
    if default_smpt_port_p is not None:
        global default_smpt_port
        # default_smpt_port = None
        default_smpt_port = default_smpt_port_p

