

from enum import *
import enum #don't delete
import logging
logger = logging.getLogger(__name__)


_orig_enum_new = Enum.__new__

#we want to use None to indicate missing Enumm, but
#https://bugs.python.org/issue34536 prohibts using None in _missing_() @classmethod
#this fix re-enable it
def _fixed_new_enum(cls, value):
    try:
        return _orig_enum_new(cls, value)
    except ValueError as e:
        msg = str(e)
        if 'is not a valid' in msg:
            return None
        raise e

Enum.__new__ = _fixed_new_enum

class StrAsReprMixinEnum(Enum):
    '''
    This is Enum Mixin that has __str__() equal to __repr__().
    '''
    def __str__(self):
        return self.__repr__()


class AutoNameMixinEnum(Enum):
    '''
    This is Enum Mixin that generate value equal to the name.
    '''
    def _generate_next_value_(name, start, count, last_values):
        return name



class MissingNoneMixinEnum(Enum):
    '''
    This is Enum Mixin will return None if value will not be found.
    '''

    @classmethod
    def _missing_(cls, value):
        # raise ValueError("%r is not a valid %s" % (value, cls.__name__))
        return None


class LookUpMixinEnum(StrAsReprMixinEnum, MissingNoneMixinEnum):
    '''
    This is Enim Mixin that is designed to be used for lookup by value.
    If lookup fail, None will be return.
    Also, __str__() will return the same value as __repr__()
    '''
    pass

