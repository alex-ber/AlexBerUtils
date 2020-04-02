import inspect
#from inspect import signature as inspect_signature
import logging
logger = logging.getLogger(__name__)


def issetdescriptor(object):
    """Return true if the object is a method descriptor with setters.

    But not if ismethod() or isclass() or isfunction() are true.
    """
    if inspect.isclass(object) or inspect.ismethod(object) or inspect.isfunction(object):
        # mutual exclusion
        return False
    tp = type(object)

    return hasattr(tp, "__set__")


def ismethod(object):
    '''
    If object is class, return false.
    If object is not function, return false.

    :param object:
    :return: false if object is not a class and not a function. Otherwise, return true iff signature has 2 params.
    '''
    if inspect.isclass(object):
        return False

    if not inspect.isfunction(object):
        return False


    return True

def has_method(cls, methodName):
    '''
    Check if class cls has method with name methodName directly,
    or in one of it's super-classes.

    :param cls:
    :param methodName:
    :return:
    '''

    #see https://mail.python.org/pipermail/python-dev/2010-August/103200.html
    #see https://docs.python.org/3.7/library/abc.html

    #logger.info(list(methodName in B.__dict__ for B in cls.__mro__))

    if any(methodName in B.__dict__ for B in cls.__mro__):
        return True
    return False
