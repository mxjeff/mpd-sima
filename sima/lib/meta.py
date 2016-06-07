# -*- coding: utf-8 -*-
# Copyright (c) 2013, 2014, 2015 Jack Kaliko <kaliko@azylum.org>
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

try:
    from collections.abc import Set # python >= 3.3
except ImportError:
    from collections import Set # python 3.2
import logging
import re

UUID_RE = r'^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89aAbB][a-f0-9]{3}-[a-f0-9]{12}$'
# The Track Object is collapsing multiple tags into a single string using this
# separator. It is used then to split back the string to tags list.
SEPARATOR = chr(0x1F)  # ASCII Unit Separator

def is_uuid4(uuid):
    """Controls MusicBrainz UUID4 format

    :param str uuid: String representing the UUID
    :returns: boolean
    """
    regexp = re.compile(UUID_RE, re.IGNORECASE)
    if regexp.match(uuid):
        return True
    return False

class MetaException(Exception):
    """Generic Meta Exception"""
    pass

def mbidfilter(func):
    def wrapper(*args, **kwargs):
        cls = args[0]
        if not cls.use_mbid:
            kwargs.pop('mbid', None)
            kwargs.pop('musicbrainz_artistid', None)
            kwargs.pop('musicbrainz_albumartistid', None)
        func(*args, **kwargs)
    return wrapper


class Meta:
    """
    A generic Class to handle tracks metadata such as artist, album, albumartist
    names and their associated MusicBrainz's ID.


    Using generic kwargs in constructor for convenience but the actual signature is:

    >>> Meta(name, mbid=None, **kwargs)

    :param str name: set name attribute
    :param str mbid: set MusicBrainz ID
    """
    use_mbid = True
    """Class attribute to disable use of MusicBrainz IDs"""

    def __init__(self, **kwargs):
        """Meta(name=<str>[, mbid=UUID4])"""
        self.__name = None #TODO: should be immutable
        self.__mbid = None
        self.__aliases = set()
        self.log = logging.getLogger(__name__)
        if 'name' not in kwargs or not kwargs.get('name'):
            raise MetaException('Need a "name" argument (str type)')
        elif not isinstance(kwargs.get('name'), str):
            raise MetaException('"name" argument not a string')
        else:
            self.__name = kwargs.pop('name')
        if 'mbid' in kwargs and kwargs.get('mbid'):
            if is_uuid4(kwargs.get('mbid')):
                self.__mbid = kwargs.pop('mbid').lower()
            else:
                self.log.warning('Wrong mbid %s:%s', self.__name,
                                 kwargs.get('mbid'))
            # mbid immutable as hash rests on
        self.__dict__.update(**kwargs)

    def __repr__(self):
        fmt = '{0}(name={1.name!r}, mbid={1.mbid!r})'
        return fmt.format(self.__class__.__name__, self)

    def __str__(self):
        return self.__name.__str__()

    def __eq__(self, other):
        """
        Perform mbid equality test
        """
        #if hasattr(other, 'mbid'):  # better isinstance?
        if isinstance(other, Meta) and self.mbid and other.mbid:
            return self.mbid == other.mbid
        elif isinstance(other, Meta):
            return bool(self.names & other.names)
        elif getattr(other, '__str__', None):
            # is other.__str__() in self.__name or self.__aliases
            return other.__str__() in self.names
        return False

    def __hash__(self):
        if self.mbid:
            return hash(self.mbid)
        return hash(self.__name)

    def add_alias(self, other):
        """Add alternative name to `aliases` attibute.

        `other` can be a :class:`sima.lib.meta.Meta` object in which case aliases are merged.

        :param str other: Alias to add, could be any object with ``__str__`` method.
        """
        if getattr(other, '__str__', None):
            if callable(other.__str__) and other.__str__() != self.name:
                self.__aliases |= {other.__str__()}
        elif isinstance(other, Meta):
            if other.name != self.name:
                self.__aliases |= other.__aliases
        else:
            raise MetaException('No __str__ method found in {!r}'.format(other))

    @property
    def name(self):
        return self.__name

    @property
    def mbid(self):
        return self.__mbid

    @property
    def aliases(self):
        return self.__aliases

    @property
    def names(self):
        """aliases + name"""
        return self.__aliases | {self.__name,}


class Album(Meta):
    """Album object"""

    @property
    def album(self):
        return self.name

class Artist(Meta):
    """Artist object deriving from :class:`Meta`.

    :param str name: Artist name
    :param str mbid: Musicbrainz artist ID
    :param str artist: Overrides "name" argument
    :param str albumartist: Overrides "name" and "artist" argument
    :param str musicbrainz_artistid: Overrides "mbid" argument
    :param str musicbrainz_albumartistid: Overrides "musicbrainz_artistid" argument

    :Example:

    >>> trk = {'artist':'Art Name',
    >>>        'albumartist': 'Alb Art Name',           # optional
    >>>        'musicbrainz_artistid': '<UUID4>',       # optional
    >>>        'musicbrainz_albumartistid': '<UUID4>',  # optional
    >>>       }
    >>> artobj0 = Artist(**trk)
    >>> artobj1 = Artist(name='Tool')
    """

    @mbidfilter
    def __init__(self, name=None, mbid=None, **kwargs):
        if kwargs.get('artist', False):
            name = kwargs.get('artist').split(SEPARATOR)[0]
        if kwargs.get('musicbrainz_artistid', False):
            mbid = kwargs.get('musicbrainz_artistid').split(SEPARATOR)[0]
        if (kwargs.get('albumartist', False) and
                kwargs.get('albumartist') != 'Various Artists'):
            name = kwargs.get('albumartist').split(SEPARATOR)[0]
        if (kwargs.get('musicbrainz_albumartistid', False) and
                kwargs.get('musicbrainz_albumartistid') != '89ad4ac3-39f7-470e-963a-56509c546377'):
            mbid = kwargs.get('musicbrainz_albumartistid').split(SEPARATOR)[0]
        super().__init__(name=name, mbid=mbid)

class MetaContainer(Set):

    def __init__(self, iterable):
        self.elements = lst = []
        for value in iterable:
            if value not in lst:
                lst.append(value)
            else:
                for inlst in lst:
                    if value == inlst:
                        inlst.add_alias(value)

    def __iter__(self):
        return iter(self.elements)

    def __contains__(self, value):
        return value in self.elements

    def __len__(self):
        return len(self.elements)

    def __repr__(self):
        return repr(self.elements)

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
