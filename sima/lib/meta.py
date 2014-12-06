# -*- coding: utf-8 -*-
# Copyright (c) 2013, 2014 Jack Kaliko <kaliko@azylum.org>
#
#  This file is part of sima
#
#  sima is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  sima is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with sima.  If not, see <http://www.gnu.org/licenses/>.
#
#
"""
Defines some object to handle audio file metadata
"""

from .simastr import SimaStr

class MetaException(Exception):
    """Generic Meta Exception"""
    pass

class NotSameArtist(MetaException):
    pass


class Meta:
    """Generic Class for Meta object"""

    def __init__(self, **kwargs):
        self.name = None
        self.mbid = None
        if 'name' not in kwargs:
            raise MetaException('need at least a "name" argument')
        self.__dict__.update(kwargs)

    def __repr__(self):
        fmt = '{0}(name="{1.name}", mbid="{1.mbid}")'
        return fmt.format(self.__class__.__name__, self)

    def __str__(self):
        return str(self.name)

    def __eq__(self, other):
        """
        Perform mbid equality test if present,
        else fallback on fuzzy equality
        """
        if hasattr(other, 'mbid'):
            if other.mbid and self.mbid:
                return self.mbid == other.mbid
        return SimaStr(str(self)) == SimaStr(str(other))

    def __hash__(self):
        if self.mbid is not None:
            return hash(self.mbid)
        else:
            return id(self)

    def __bool__(self):  # empty name not possible for a valid obj
        return bool(self.name)

class Album(Meta):
    """Info:
    If a class that overrides __eq__() needs to retain the implementation of
    __hash__() from a parent class, the interpreter must be told this explicitly
    by setting __hash__ = <ParentClass>.__hash__.
    """
    __hash__ = Meta.__hash__

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __eq__(self, other):
        """
        Perform mbid equality test if present,
        else fallback on self.name equality
        """
        if hasattr(other, 'mbid'):
            if other.mbid and self.mbid:
                return self.mbid == other.mbid
        return str(self) == str(other)

    @property
    def album(self):
        return self.name


class Artist(Meta):

    def __init__(self, **kwargs):
        self._aliases = set()
        super().__init__(**kwargs)

    def append(self, name):
        self._aliases.update({name,})

    @property
    def names(self):
        return self._aliases | {self.name,}

    def __add__(self, other):
        if isinstance(other, Artist):
            if self.mbid == other.mbid:
                res = Artist(**self.__dict__)
                res._aliases.extend(other.names)
                return res
            else:
                raise NotSameArtist('different mbids: {0} and {1}'.format(self, other))

# vim: ai ts=4 sw=4 sts=4 expandtab
