import logging
logger = logging.getLogger(__name__)
import pytest

from alexber.utils.props import Properties, lazyproperty
from importlib.resources import open_text


def test_parse_java_properties_alternative_delim(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    mocker.patch.object(Properties, 'PLACEHOLDER_TOKEN', new='@', spec_set=True)
    exp_cls_name_a = 'alexber.rpsgame.players.ConstantPlayer'
    exp_cls_name_b = exp_cls_name_a
    expdd = {'playera.cls': 'alexber.rpsgame.players.ConstantPlayer',
             'playerb.cls': 'alexber.rpsgame.players.ConstantPlayer', }


    p = Properties()
    pck = '.'.join(['tests_data', __package__])

    with open_text(pck, 'config2.properties') as f:
        p.load(f)
    dd = p.as_dict()

    assert expdd == dd


def test_parse_java_properties(request):
    logger.info(f'{request._pyfuncitem.name}()')
    exp_cls_name_a = 'alexber.rpsgame.players.ConstantPlayer'
    exp_cls_name_b = exp_cls_name_a
    expdd = {'playera.cls': 'alexber.rpsgame.players.ConstantPlayer',
             'playerb.cls': 'alexber.rpsgame.players.ConstantPlayer',}

    p = Properties()
    pck = '.'.join(['tests_data', __package__])
    with open_text(pck, 'config.properties') as f:
        p.load(f)
    dd = p.as_dict()
    #we want to ignore key inner.*
    a_cls_name = dd['playera.cls']
    b_cls_name = dd['playerb.cls']

    d = {'playera.cls': a_cls_name,
         'playerb.cls': b_cls_name,}

    assert expdd==d

class ProperyBase:

    @property
    def answer(self):
        return -1

class ProperyDerived(ProperyBase):
    @property
    def answer(self):
        return 42

def test_regular_properties_support_override(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    a = ProperyDerived()
    actual = a.answer
    assert 42 == actual

class LazyProperty:
    def __init__(self, a=42):
        self._answer = a

    @lazyproperty
    def answer(self):
        return self._make_long_calc()





if __name__ == "__main__":
    pytest.main([__file__])
