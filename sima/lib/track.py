# -*- coding: utf-8 -*-

# Copyright (c) 2009, 2010, 2011, 2013, 2014 Jack Kaliko <kaliko@azylum.org>
# Copyright (c) 2009 J. Alexander Treuman (Tag collapse method)
# Copyright (c) 2008 Rick van Hattem
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

import time

from .meta import Artist

class Track:
    """
    Track object.
    Instanciate with Player replies.
    """

    def __init__(self, file=None, time=0, pos=-1, **kwargs):
        self.title = self.artist = self.album = self.albumartist = ''
        self.musicbrainz_artistid = self.musicbrainz_albumartistid = None
        self.pos = int(pos)
        self._empty = False
        self._file = file
        if not kwargs:
            self._empty = True
        self._time = time
        self.__dict__.update(**kwargs)
        self.tags_to_collapse = ['artist', 'album', 'title', 'date',
                                 'genre', 'albumartist',
                                 'musicbrainz_artistid',
                                 'musicbrainz_albumartistid']
        #  have tags been collapsed?
        self.collapsed_tags = list()
        # Needed for multiple tags which returns a list instead of a string
        self.collapse_tags()

    def collapse_tags(self):
        """
        Necessary to deal with tags defined multiple times.
        These entries are set as lists instead of strings.
        """
        for tag, value in self.__dict__.items():
            if tag not in self.tags_to_collapse:
                continue
            if isinstance(value, list):
                self.collapsed_tags.append(tag)
                self.__dict__.update({tag: ', '.join(set(value))})

    def __repr__(self):
        return '%s(artist="%s", album="%s", title="%s", filename="%s")' % (
            self.__class__.__name__,
            self.artist,
            self.album,
            self.title,
            self.file,
        )

    def __str__(self):
        return '{artist} - {album} - {title} ({duration})'.format(
                duration=self.duration,
                **self.__dict__
                )

    def __int__(self):
        return self.time

    def __add__(self, other):
        return Track(time=self.time + other.time)

    def __sub__(self, other):
        return Track(time=self.time - other.time)

    def __hash__(self):
        if self.file:
            return hash(self.file)
        else:
            return id(self)

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __ne__(self, other):
        return hash(self) != hash(other)

    def __bool__(self):
        return not self._empty

    @property
    def file(self):
        """file is an immutable attribute that's used for the hash method"""
        return self._file

    def get_time(self):
        """get time property"""
        return self._time

    def set_time(self, value):
        """set time property"""
        self._time = int(value)

    time = property(get_time, set_time, doc='song duration in seconds')

    @property
    def duration(self):
        """Compute fancy duration"""
        temps = time.gmtime(int(self.time))
        if temps.tm_hour:
            fmt = '%H:%M:%S'
        else:
            fmt = '%M:%S'
        return time.strftime(fmt, temps)

    def get_artist(self):
        """Get artist object from track"""
        name = self.artist
        mbid = self.musicbrainz_artistid
        if self.albumartist and self.albumartist != 'Various Artists':
            name = self.albumartist.split(', ')[0]
        if (self.musicbrainz_albumartistid and
            self.musicbrainz_albumartistid != '89ad4ac3-39f7-470e-963a-56509c546377'):
            mbid = self.musicbrainz_albumartistid.split(', ')[0]
        return Artist(name=name, mbid=mbid)

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
