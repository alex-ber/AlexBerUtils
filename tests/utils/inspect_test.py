import logging
import pytest
import inspect
from alexber.utils.inspects import issetdescriptor, ismethod, has_method
from collections import OrderedDict

logger = logging.getLogger(__name__)


class Example(object):
    def __init__(self, name, address=None, *args, **kwargs):
        pass

    def foo1(self):
        pass

    @staticmethod
    def method1():
        pass

    @classmethod
    def method2(cls):
        pass

    @property
    def att1(self):
        return 5

    @att1.setter
    def att1(self, value):
        pass

    @property
    def att_get_only(self):
        return 5

    def _set_only(self):
        pass

    att_set_only = property(fset=_set_only)


    def set_x(self, x):
        pass

    def baz(self, a, b, c):
        pass

    def seed(self, a=None, version=2):
        pass

class Base(object):

    @property
    def att1(self):
        return 5

    @att1.setter
    def att1(self, value):
        pass

    @property
    def att_get_only(self):
        return 5

    def set_x(self, x):
        pass

class Derived(Base):
    def __init__(self, name, address=None, *args, **kwargs):
        pass



@pytest.mark.parametrize(
     'obj',
    (Example,
     Derived),
)
def test_property_get_set(request, obj):
    logger.info(f'{request._pyfuncitem.name}()')
    results = inspect.getmembers(obj, predicate=issetdescriptor)
    d = {key: value for key, value in results}

    prop = d['att1']

    setter = prop.fset
    setter(self=None, value=100)

    prop = d['att_get_only']
    setter = prop.fset
    assert setter is None


@pytest.mark.parametrize(
     'f',
    (Example,
     Derived),
)
def test_signature(request, f):
    logger.info(f'{request._pyfuncitem.name}()')
    sig = inspect.signature(f)

    d = OrderedDict()
    for var in sig.parameters.keys():
        d[var] = None

    var = d['name']

    logger.debug(d)
    logger.debug(var)

@pytest.mark.parametrize(
     'f',
    (Example,
     Derived),
)
#see https://stackoverflow.com/questions/218616/getting-method-parameter-names-in-python/45781963#45781963
#see https://stackoverflow.com/questions/218616/getting-method-parameter-names-in-python/44261531#44261531
def test_binding(request, f):
    logger.info(f'{request._pyfuncitem.name}()')
    d = OrderedDict()
    d['name'] = 'metoo'

    sig = inspect.signature(f)
    bound_args = sig.bind(**d)
    bound_args.apply_defaults()
    kwargs = bound_args.arguments
    obj = f(**kwargs)
    assert obj is not None

class SubDerived(Derived):
    def set_x(self, x):
        pass

class Derivitive(SubDerived, Base):
    def set_x(self, x):
        pass

    def cool(self):
        pass

@pytest.mark.parametrize(
     'cls, method_name, exp_value',

    [
        (Example, '__init__', True),
        (Example, 'foo1', True),
        (Example, 'method1', True),
        (Example, 'method2', True),
        (Example, 'att1', False),
        (Example, 'att_get_only', False),
        (Example, '_set_only', True),
        (Example, 'set_x', True),
        (Example, 'baz', True),
        (Example, '__init__', True),
        (Example, 'seed', True),
        (Example, 'this_is_method_is_not_here', False),
        (Derived, '__init__', True),
        (SubDerived, 'set_x', True),
        (SubDerived, 'set_non_exists', False),
        (Derivitive, 'set_x', True),
        (Derivitive, 'cool', True),
        (Derivitive, 'set_non_exists', False),


    ]
)
def test_has_method(request, cls, method_name, exp_value):
    logger.info(f'{request._pyfuncitem.name}()')

    b = has_method(cls, method_name)
    assert exp_value == b

if __name__ == "__main__":
    pytest.main([__file__])
