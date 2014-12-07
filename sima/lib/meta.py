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

import re

UUID_RE = r'^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89aAbB][a-f0-9]{3}-[a-f0-9]{12}$'

def is_uuid4(uuid):
    regexp = re.compile(UUID_RE, re.IGNORECASE)
    if regexp.match(uuid):
        return True
    raise WrongUUID4(uuid)

class MetaException(Exception):
    """Generic Meta Exception"""
    pass

class WrongUUID4(MetaException):
    pass


class Meta:
    """Generic Class for Meta object
    Meta(name=<str>[, mbid=UUID4])
    """

    def __init__(self, **kwargs):
        self.name = None
        self.__mbid = None
        if 'name' not in kwargs or not kwargs.get('name'):
            raise MetaException('Need a "name" argument')
        if 'mbid' in kwargs and kwargs.get('mbid'):
            is_uuid4(kwargs.get('mbid'))
            # mbid immutable as hash rests on
            self.__mbid = kwargs.pop('mbid')
        self.__dict__.update(**kwargs)

    def __repr__(self):
        fmt = '{0}(name={1.name!r}, mbid={1.mbid!r})'
        return fmt.format(self.__class__.__name__, self)

    def __str__(self):
        return self.name.__str__()

    def __eq__(self, other):
        """
        Perform mbid equality test
        """
        #if hasattr(other, 'mbid'):  # better isinstance?
        if isinstance(other, Meta) and self.mbid and other.mbid:
            if self.mbid and other.mbid:
                return self.mbid == other.mbid
        else:
            return other.__str__() == self.__str__()
        return False

    def __hash__(self):
        if self.mbid:
            return hash(self.mbid)
        return id(self)

    @property
    def mbid(self):
        return self.__mbid


class Album(Meta):

    @property
    def album(self):
        return self.name

class Artist(Meta):

    def __init__(self, name=None, **kwargs):
        """Artist object built from a mapping dict containing at least an
        "artist" entry:
            >>> trk = {'artist':'Art Name',
            >>>        'albumartist': 'Alb Art Name',           # optional
            >>>        'musicbrainz_artistid': '<UUID4>'    ,   # optional
            >>>        'musicbrainz_albumartistid': '<UUID4>',  # optional
            >>>       }
            >>> artobj0 = Artist(**trk)
            >>> artobj1 = Artist(name='Tool')
        """
        self.__aliases = set()
        name = kwargs.get('artist', name)
        mbid = kwargs.get('musicbrainz_artistid', None)
        if (kwargs.get('albumartist', False) and
                kwargs.get('albumartist') != 'Various Artists'):
            name = kwargs.get('albumartist').split(', ')[0]
        if (kwargs.get('musicbrainz_albumartistid', False) and
                kwargs.get('musicbrainz_albumartistid') != '89ad4ac3-39f7-470e-963a-56509c546377'):
            mbid = kwargs.get('musicbrainz_albumartistid').split(', ')[0]
        super().__init__(name=name, mbid=mbid)

    def add_alias(self, other):
        if getattr(other, '__str__', None):
            if callable(other.__str__):
                self.__aliases |= {other.__str__()}
        elif isinstance(other, Artist):
            self.__aliases |= other._Artist__aliases
        else:
            raise MetaException('No __str__ method found in {!r}'.format(other))

    @property
    def names(self):
        return self.__aliases | {self.name,}

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
