import pytest
import logging

logger = logging.getLogger(__name__)
from alexber.utils.importer import importer, new_instance

class TestImporter(object):
    def test_imported(self, request):
        logger.info(f'{request._pyfuncitem.name}()')

        cls_name = 'pathlib.Path'
        kls = importer(cls_name)

        path = kls()
        logger.info(path.resolve())

    def test_imported_implicit_namespace_package(self, request):
        logger.info(f'{request._pyfuncitem.name}()')

        module_name = 'tests.utils.splitpackage.other_module'
        module = importer(module_name)
        value = module.theansweris()
        evp_value = 42
        pytest.assume(evp_value, value)



def test_new_instance_function(request):
    logger.info(f'{request._pyfuncitem.name}()')
    cls_name = 'pathlib.Path.cwd'
    kls = new_instance(cls_name)

    path = kls()
    logger.info(path.absolute())


class PlayerEmpty(object):
    pass


class PlayerInitFull(object):
    def __init__(self, *args, **kwargs):
        pass

class PlayerInitArg(object):
    def __init__(self, first_name):
        self.first_name = first_name

class PlayerInitDefaultArg(object):
    def __init__(self, first_name='John', **kwargs):
        self.first_name = first_name

class PlayerNewAndInitEmpty(object):
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        logger.debug("PlayerNewAndInitEmpty.__new__()")
        return self

class PlayerNewOnlyEmpty(object):
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        return self

    def __init__(self, *args, **kwargs):
        pass

class PlayerNewOnlyEmptySneaky(object):
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        return 3    #3 is not instace of this class '__init__" shouldn't be called

    def __init__(self, *args, **kwargs):
        pass




from abc import ABCMeta, abstractmethod

class PlayerAbstractWithAbstractMethod(object, metaclass=ABCMeta):
    @abstractmethod
    def foo(self):
        raise NotImplementedError


class PlayerAbstractEmptyWithoutAbstractMethod(object, metaclass=ABCMeta):
    pass

class PlayerAbstractFullWithoutAbstractMethod(object, metaclass=ABCMeta):
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        return self

    def __init__(self, *args, **kwargs):
        pass


class PlayerPhilosopher:
    def __init_subclass__(cls, default_name, **kwargs):
        super().__init_subclass__(**kwargs)
        logger.debug(f"Called __init_subclass({cls}, {default_name})")
        cls.default_name = default_name


class PlayerAustralianPhilosopher(PlayerPhilosopher, default_name="Bruce"):
    pass



def test_new_instance_arg(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    mock = mocker.spy(PlayerInitArg, '__init__')

    input = '.'.join([__name__, PlayerInitArg.__name__])
    first_name = 'John'
    player=new_instance(input, first_name)
    assert player.first_name == first_name
    assert player.__init__.call_count == 1


def test_new_instance_default_arg1(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')

    input = '.'.join([__name__, PlayerInitDefaultArg.__name__])
    first_name = 'John'
    player=new_instance(input, first_name)
    assert player.first_name == first_name

def test_new_instance_default_arg2(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')

    input = '.'.join([__name__, PlayerInitDefaultArg.__name__])
    player=new_instance(input)
    assert player.first_name == "John"

def test_new_instance_default_arg3(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    mock = mocker.spy(PlayerInitDefaultArg, '__init__')

    input = '.'.join([__name__, PlayerInitDefaultArg.__name__])
    player=new_instance(input, last_name='Google')
    assert player.first_name == "John"


@pytest.mark.parametrize(
     'plcls',
    (PlayerEmpty, PlayerInitFull,PlayerNewOnlyEmpty, PlayerNewOnlyEmpty,PlayerNewAndInitEmpty,
     PlayerAbstractEmptyWithoutAbstractMethod, PlayerAbstractFullWithoutAbstractMethod),
)
def test_new_instance(request, plcls):
    logger.info(f'{request._pyfuncitem.name}()')

    input = '.'.join([__name__, plcls.__name__])
    player = new_instance(input)
    assert player is not None


def test_new_instance_init_subclass(request):
    logger.info(f'{request._pyfuncitem.name}()')
    input = '.'.join([__name__, PlayerAustralianPhilosopher.__name__])

    player=new_instance(input)
    assert player is not None


def test_new_instance_abstract_method(request):
    logger.info(f'{request._pyfuncitem.name}()')
    input = '.'.join([__name__, PlayerAbstractWithAbstractMethod.__name__])

    with pytest.raises(TypeError, match='abstract method') as excinfo:
        player = new_instance(input)
    logger.debug(excinfo.value, exc_info=(excinfo.type, excinfo.value, excinfo.tb))



def test_new_instance_sneaky(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    mock = mocker.spy(PlayerNewOnlyEmptySneaky, '__init__')

    input = '.'.join([__name__, PlayerNewOnlyEmptySneaky.__name__])
    player=new_instance(input)
    assert not hasattr(player.__init__, 'call_count') or player.__init__.call_count == 0


if __name__ == "__main__":
    pytest.main([__file__])