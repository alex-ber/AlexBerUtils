#see https://stackoverflow.com/questions/1785503/when-should-i-use-uuid-uuid1-vs-uuid-uuid4-in-python
#https://stackoverflow.com/questions/703035/when-are-you-truly-forced-to-use-uuid-as-part-of-the-design/786541#786541

from uuid import uuid1 as _uuid1
_int_from_bytes = int.from_bytes  # py3 only

from random import SystemRandom as _SystemRandom

_system_random = _SystemRandom()





def uuid1mc():
    '''
    This is v1 with random MAC ("v1mc"). This is a hybrid between version 1 & version 4.

    Version 1 UUIDs use the network card's MAC address (which unless spoofed, should be unique),
    plus a timestamp, plus the usual bit-twiddling to generate the UUID.

    Version 4 UUIDs Generate a random UUID.

    uuid1mc() is deliberately generating v1 UUIDs with a random broadcast MAC address (this is allowed by the v1 spec).
    The resulting v1 UUID is time dependant (like regular v1), but lacks all host-specific information (like v4).
    It's also much closer to v4 in it's collision-resistance:
        v1mc = 60 bits of time + 61 random bits = 121 unique bits; v4 = 122 random bits.

    Note: somebody reported that ran into trouble using UUID1 in Amazon EC2 instances.
    He use UUID1 for a database upgrade script where he generated ~120k UUIDs within a couple of minutes.
    The UUID collision led to violation of a primary key constraint.
    He suspect poor clock resolution and switching to UUID4 solved it for him.

    '''
    #return uuid1(_int_from_bytes(urandom(6), "big") | 0x010000000000)
    node = _system_random.getrandbits(8) #6 and not 8, because this function round up to bits / 8 and rounded up
    # NOTE: The constant here is required by the UUIDv1 spec...
    return  _uuid1(node | 0x010000000000)


