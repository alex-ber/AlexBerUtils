import logging
import pytest

logger = logging.getLogger(__name__)

from uuid import uuid1
_int_from_bytes = int.from_bytes
from os import urandom
from alexber.utils import uuid1mc

#refference implementation
#https://stackoverflow.com/questions/1785503/when-should-i-use-uuid-uuid1-vs-uuid-uuid4-in-python
def ref_uuid1mc():
    return uuid1(_int_from_bytes(urandom(6), "big") | 0x010000000000)

def test_uuid1mc(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    # logger.debug(urandom(6))
    rnd = b'W\x91\x8e\xb3!\x08'

    mocker.patch("random._urandom",  side_effect=lambda _: rnd, create=True)
    mocker.patch('.'.join([__name__, 'urandom']),  side_effect=lambda _: rnd, create=True)
    mocker.patch('.'.join([__name__, 'uuid1']), side_effect=lambda p:p, autospec=True, spec_set=True)
    mocker.patch('.'.join(['alexber.utils.uuids', '_uuid1']), side_effect=lambda p: p, autospec=True, spec_set=True)

    exp = ref_uuid1mc()
    actual = uuid1mc()
    assert  exp==actual





if __name__ == "__main__":
    pytest.main([__file__])
