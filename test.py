from random import randint
from hashids import Hashids

def create_code(pk, n):
    """Helper function to create ticket codes."""
    hashids = Hashids(
        salt='abcd1234',
        min_length=n,
        alphabet='abcdefghijkmnopqrstuvwxyz123456789'
    )
    code = hashids.encode(pk)[:n]
    return code

password = create_code(randint(0, 1000000000000), 6)
print(password)
