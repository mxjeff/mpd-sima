"""
The cache object API for implementing caches. The default is just a
dictionary, which in turns means it is not threadsafe for writing.
"""

import os
import base64
import codecs

from hashlib import md5
from pickle import load, dump
from threading import Lock

from .filelock import FileLock


class BaseCache:

    def get(self, key):
        raise NotImplemented()

    def set(self, key, value):
        raise NotImplemented()

    def delete(self, key):
        raise NotImplemented()


class DictCache(BaseCache):

    def __init__(self, init_dict=None):
        self.lock = Lock()
        self.data = init_dict or {}

    def get(self, key):
        return self.data.get(key, None)

    def set(self, key, value):
        with self.lock:
            self.data.update({key: value})

    def delete(self, key):
        with self.lock:
            if key in self.data:
                self.data.pop(key)


class FileCache:

    def __init__(self, directory, forever=False):
        self.directory = directory
        self.forever = forever

        if not os.path.isdir(self.directory):
            os.mkdir(self.directory)

    def encode(self, x):
        return md5(x.encode('utf-8')).hexdigest()

    def _fn(self, name):
        return os.path.join(self.directory, self.encode(name))

    def get(self, key):
        name = self._fn(key)
        if os.path.exists(name):
            return load(codecs.open(name, 'rb'))

    def set(self, key, value):
        name = self._fn(key)
        with FileLock(name):
            with codecs.open(name, 'w+b') as fh:
                dump(value, fh)

    def delete(self, key):
        if not self.forever:
            os.remove(self._fn(key))
