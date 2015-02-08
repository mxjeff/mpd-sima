# -*- coding: utf-8 -*-

# Copyright (c) 2014 Jack Kaliko <kaliko@azylum.org>
# Copyright (c) 2012, 2013 Eric Larson <eric@ionrock.org>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
"""
The cache object API for implementing caches. The default is just a
dictionary, which in turns means it is not threadsafe for writing.
"""

import os
import codecs

from hashlib import md5
from pickle import load, dump
from threading import Lock

from ..utils.filelock import FileLock


class BaseCache:

    def get(self, key):
        """Get cache value"""
        raise NotImplementedError

    def set(self, key, value):
        """Set cache value"""
        raise NotImplementedError

    def delete(self, key):
        """Remove cache value"""
        raise NotImplementedError


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
            os.makedirs(self.directory, mode=0o755)

    def encode(self, val):
        return md5(val.encode('utf-8')).hexdigest()

    def _fn(self, name):
        return os.path.join(self.directory, self.encode(name))

    def get(self, key):
        name = self._fn(key)
        if os.path.exists(name):
            return load(codecs.open(name, 'rb'))

    def set(self, key, value):
        name = self._fn(key)
        with FileLock(name):
            with codecs.open(name, 'w+b') as flh:
                dump(value, flh)

    def delete(self, key):
        if not self.forever:
            os.remove(self._fn(key))

    def __iter__(self):
        for dirpath, _, filenames in os.walk(self.directory):
            for item in filenames:
                name = os.path.join(dirpath, item)
                yield load(codecs.open(name, 'rb'))
