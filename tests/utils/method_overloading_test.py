import logging
import sys
import pytest

logger = logging.getLogger(__name__)

try:
    #python3 -m pip uninstall multidispatch==0.2
    from multidispatch import multimethod
except ImportError:
    class _dummy(object):
        def dispatch(self, *types):
            return self

    def multimethod(func):
        def with_md(*args, **kwargs):
            return _dummy
        return with_md

from alexber.utils.importer import importer


class Engine(object):


    @multimethod(object)
    def _set_playerA(self, player):
        logging.debug('instance')
        pass

    @_set_playerA.dispatch(str)
    def _(self, st):
        logging.debug('str')
        player_cls = importer(st)
        player = player_cls()
        player.say()
        pass

    #alternative (recent) syntax
    # @_set_playerA.dispatch
    # def _(self, st: str):
    #     print('str')
    #     player_cls = importer(st)
    #     player = player_cls()
    #     player.say()
    #     pass


    playerA = property(fset=_set_playerA)


class Player(object):
    def say(self):
        logging.debug('hello')

@pytest.mark.md
def test_overloading_object(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    namespace = sys.modules[__name__]

    importer = mocker.spy(namespace, 'importer')
    engine = Engine()
    input = Player()
    engine.playerA= input

    assert namespace.importer == importer
    assert importer.call_count ==0, "Engine.playerA(str) was called, when Engine.playerA(object) was expected"
                                                            # #we shouldn't use  importer when we have explicit object."
    logger.info(dir(importer))

@pytest.mark.md
def test_overloading_str(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    namespace = sys.modules[__name__]

    importer = mocker.spy(namespace, 'importer')
    engine = Engine()
    input = '.'.join([__name__, 'Player'])
    engine.playerA = input

    assert namespace.importer == importer
    importer.assert_called_once_with(input)

class PlayerPhilosopher:
    def __init_subclass__(cls, default_name, **kwargs):
        super().__init_subclass__(**kwargs)
        logger.debug(f"Called __init_subclass({cls}, {default_name})")
        cls.default_name = default_name


class PlayerAustralianPhilosopher(PlayerPhilosopher, default_name="Bruce"):
    pass



if __name__ == "__main__":
    import pytest
    pytest.main([__file__])