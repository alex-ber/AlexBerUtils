import logging
import threading
import time
import pytest
from smtplib import SMTP as _SMTP, LMTP as _LMTP
from alexber.utils.emails import SMTPHandler, OneMemoryHandler
import alexber.utils.emails as emails
#don't remove this
from platform import uname
from alexber.utils.emails import EmailStatus, FINISHED
logger = logging.getLogger(__name__)
emailLogger = None

@pytest.fixture
def errorMailHandler(mocker):

    d1 = {
     #   'level': logging.DEBUG,
        'smtpclsname': 'smtplib.SMTP',
        'mailhost': ['smtp-relay.gmail.com', 587],
        'fromaddr': f'{{uname()[1]}}@gmail.com',
        'toaddrs': ['no-reply@gmail.com'],
        'subject': 'mail_subject'
    }

    error_email_handler = SMTPHandler(**d1)
    error_email_handler.setLevel(logging.DEBUG)

    mocker.patch.object(error_email_handler, 'emit',autospec=True, spec_set=True)
    return error_email_handler


@pytest.fixture
def emailsSubject(request, mocker):
    request_param = 'Process Status : {{status}}' if (
        not hasattr(request, 'param')) else request.param
    yield request_param

@pytest.fixture
def errorMailMemoryHandler(request, mocker, errorMailHandler, emailsSubject):

    d2 = {
        #'formatter': detailFormatter,
        #'subject': 'Process Status : {{status}}',
        'subject': emailsSubject,
        #'target': error_email_handler
    }

    detailFormatter = logging.Formatter('%(asctime)-15s %(levelname)s [%(name)s.%(funcName)s] %(message)s',
                                        '%Y-%m-%d %H:%M:%S')
    error_mail_memory_handler = OneMemoryHandler(**d2)
    error_mail_memory_handler.setFormatter(detailFormatter)
    error_mail_memory_handler.setTarget(errorMailHandler)
    return error_mail_memory_handler

@pytest.fixture
def emailsFixture(request, mocker, errorMailMemoryHandler):
    global emailLogger
    emailLogger = logging.getLogger('emails')
    propagate_param = emailLogger.propagate if (not hasattr(request, 'param')) else request.param
    prev_propogate = emailLogger.propagate
    emailLogger.propagate = propagate_param
    emailLogger.addHandler(errorMailMemoryHandler)
    yield errorMailMemoryHandler.target
    emailLogger.removeHandler(errorMailMemoryHandler)
    emailLogger.propagate = prev_propogate

def run_successfuly():
    logger.debug("run_successfuly()")
    emailLogger.info("Start - Process")
    emailLogger.info("Step 1")
    emailLogger.info("Step 2")
    emailLogger.info("Done Successfully - Process")

def run_with_failure():
    logger.debug("run_with_failure()")
    emailLogger.info("Start - Process")
    emailLogger.info("Step 1")
    1/0
    emailLogger.info("Step 2")
    emailLogger.info("Done Successfully - Process")

def is_failed(logrecord):
    subject = str(logrecord.msg['subject'])
    assert '{status}' not in subject
    assert 'Done' in subject or 'Failed' in subject
    b = 'Failed' in subject
    return b

def check_failed(logrecord):
    subject = str(logrecord.msg['subject'])
    pytest.assume('Failed' in subject)
    pytest.assume('{status}' not in subject)
    message = str(logrecord.msg)
    pytest.assume('Start' in message)
    pytest.assume('division by zero' in message)
    pytest.assume('Step 1' in message)
    pytest.assume('Step 2' not in message)


def check_sucess(logrecord):
    subject = str(logrecord.msg['subject'])
    pytest.assume('Done' in subject)
    pytest.assume('{status}' not in subject)
    message = str(logrecord.msg)
    pytest.assume('Start' in message)
    pytest.assume('Step 1' in message)
    pytest.assume('Step 2' in message)

def test_emails_intented_success(request, mocker, emailsFixture):
    logger.info(f'{request._pyfuncitem.name}()')

    with EmailStatus(emailLogger=emailLogger, logger=None, faildargs={'status': 'Failed'},
                     successargs={'status': 'Done'}):
        run_successfuly()
    mock_log = emailsFixture.emit
    pytest.assume(mock_log.call_count == 1)
    (logrecord,), _ = mock_log.call_args

    check_sucess(logrecord)

#emailsSubject
@pytest.mark.parametrize('emailsSubject', ['Aggregates log from the Demo application',
                                                    ], indirect=True)
def test_emails_intented_simple_success(request, mocker, emailsFixture, emailsSubject):
    logger.info(f'{request._pyfuncitem.name}()')

    emailLogger.log(FINISHED, None)
    mock_log = emailsFixture.emit
    pytest.assume(mock_log.call_count == 1)
    (logrecord,), _ = mock_log.call_args
    subject = str(logrecord.msg['subject'])
    pytest.assume(emailsSubject in subject)

#emailsSubject
@pytest.mark.parametrize('emailsSubject', ['Aggregates log from the Demo application',
                                                    ], indirect=True)
def test_emails_intented_simple_success2(request, mocker, emailsFixture, emailsSubject):
    logger.info(f'{request._pyfuncitem.name}()')

    emailLogger.log(FINISHED, '')
    mock_log = emailsFixture.emit
    pytest.assume(mock_log.call_count == 1)
    (logrecord,), _ = mock_log.call_args
    subject = str(logrecord.msg['subject'])
    pytest.assume(emailsSubject in subject)

#emailsSubject
@pytest.mark.parametrize('emailsSubject', ['Aggregates log from the Demo application',
                                                    ], indirect=True)
def test_emails_intented_simple_success_wrong(request, mocker, emailsFixture, emailsSubject):
    logger.info(f'{request._pyfuncitem.name}()')

    with pytest.raises(ValueError):
        emailLogger.log(FINISHED, ['some non-dict value'])

@pytest.fixture
def specialAbruptCleanup(request, mocker):
    yield None
    setattr(emails._thread_locals, 'buffer', [])


def test_emails_intented_abrupt_execution(request, mocker, emailsFixture, errorMailMemoryHandler, specialAbruptCleanup):
    logger.info(f'{request._pyfuncitem.name}()')
    emailLogger.info("Started")
    emailLogger.info('Step 1')
    logging.shutdown([lambda: errorMailMemoryHandler])
    emailLogger.info('Step 2')

    mock_log = emailsFixture.emit
    pytest.assume(mock_log.call_count == 1)
    (logrecord,), _ = mock_log.call_args

    subject = str(logrecord.msg['subject'])
    pytest.assume('Abrupt' in subject)
    pytest.assume('{status}' not in subject)
    message = str(logrecord.msg)
    pytest.assume('Start' in message)
    pytest.assume('Step 1' in message)
    pytest.assume('Step 2' not in message)


@pytest.mark.parametrize('emailsFixture', [False], indirect=True)
def test_emails_intented_failure(request, mocker, emailsFixture):
    logger.info(f'{request._pyfuncitem.name}()')


    with EmailStatus(emailLogger=emailLogger, logger=None, faildargs={'status': 'Failed'},
                     successargs={'status': 'Done'}):
        run_with_failure()
    mock_log = emailsFixture.emit
    pytest.assume(mock_log.call_count == 1)
    (logrecord,), _ = mock_log.call_args


    check_failed(logrecord)


def test_init_config_default(request, mocker, emailsFixture):
    logger.info(f'{request._pyfuncitem.name}()')
    emails.initConfig()
    pytest.assume(_SMTP==emails.default_smtp_cls)


def test_init_config2(request, mocker, emailsFixture):
    logger.info(f'{request._pyfuncitem.name}()')
    exp_default_smtp_port='9000'
    emails.initConfig(default_smtp_cls_name='smtplib.LMTP')
    pytest.assume(_LMTP==emails.default_smtp_cls)


@pytest.mark.parametrize('emailsFixture', [False], indirect=True)
def test_emails_multithreaded(request, mocker, emailsFixture):
    logger.info(f'{request._pyfuncitem.name}()')

    stop =10

    def _run_successfuly(stop):
        for i in range(stop):
            with EmailStatus(emailLogger=emailLogger, logger=None, faildargs={'status': 'Failed'},
                             successargs={'status': 'Done'}):
                run_successfuly()
        time.sleep(1)

    def _run_with_failure(stop):
        for i in range(stop):
            with EmailStatus(emailLogger=emailLogger, logger=None, faildargs={'status': 'Failed'},
                             successargs={'status': 'Done'}):
                run_with_failure()


    th1 = threading.Thread(name="run_successfuly",
                               target=_run_successfuly, args=(stop,))

    th2 = threading.Thread(name="run_with_failure",
                           target=_run_with_failure, args=(stop,))

    th1.start()
    th2.start()
    th1.join()
    th2.join()

    mock_log = emailsFixture.emit
    pytest.assume(mock_log.call_count == 2*stop)
    for kall in mock_log.call_args_list:
        (logrecord,), _ = kall
        if is_failed(logrecord):
            check_failed(logrecord)
        else:
            check_sucess(logrecord)





if __name__ == "__main__":
    pytest.main([__file__])
