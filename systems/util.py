import hashlib
import random


def generateSecretKey():
    """Internal code to generate a unique secret key"""
    key = hashlib.sha1()
    key.update(str(random.random()))
    return key.hexdigest()[:11]
## DEF
