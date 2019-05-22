import logging
import pytest
import inspect
from alexber.utils.inspects import issetdescriptor, ismethod
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
    d = OrderedDict()
    d['name'] = 'metoo'

    sig = inspect.signature(f)
    bound_args = sig.bind(**d)
    bound_args.apply_defaults()
    kwargs = bound_args.arguments
    obj = f(**kwargs)
    assert obj is not None



if __name__ == "__main__":
    pytest.main([__file__])
