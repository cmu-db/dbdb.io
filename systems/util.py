import hashlib
import os
import random

from PIL import Image


def create_logo(filename):
    size = 256, 256
    new_filename = filename.replace('originals', 'thumbnails')
    directory = new_filename[0:new_filename.rfind('/')]
    if 'thumbnails' in directory and  not os.path.exists(directory):
        os.makedirs(directory)
    try:
        im = Image.open(filename)
        im.thumbnail(size, Image.ANTIALIAS)
        im.save(new_filename, "PNG")
        return im
    except IOError as e:
        print "cannot create thumbnail for '%s'" % new_filename
        print e


def generateSecretKey():
    """Internal code to generate a unique secret key"""
    key = hashlib.sha1()
    key.update(str(random.random()))
    return key.hexdigest()[:11]
## DEF
