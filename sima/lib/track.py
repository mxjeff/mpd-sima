# -*- coding: utf-8 -*-

# Copyright (c) 2009, 2010, 2011, 2013 Jack Kaliko <efrim@azylum.org>
# Copyright (c) 2009 J. Alexander Treuman (Tag collapse method)
# Copyright (c) 2008 Rick van Hattem
#
#  This file is part of MPD_sima
#
#  MPD_sima is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MPD_sima is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MPD_sima.  If not, see <http://www.gnu.org/licenses/>.
#
#

import time


class Track(object):
    """
    Track object.
    Instanciate with mpd replies.
    """

    def __init__(self, file=None, time=0, pos=0, **kwargs):
        self.title = self.artist = self.album = self.albumartist = ''
        self._pos = pos
        self.empty = False
        self._file = file
        if not kwargs:
            self.empty = True
        self.time = time
        self.__dict__.update(**kwargs)
        self.tags_to_collapse = list(['artist', 'album', 'title', 'date',
            'genre', 'albumartist'])
        #  have tags been collapsed?
        self.collapse_tags_bool = False
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
                self.collapse_tags_bool = True
                self.collapsed_tags.append(tag)
                self.__dict__.update({tag: ', '.join(set(value))})

    def get_filename(self):
        """return filename"""
        if not self.file:
            return None
        return self.file

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
        return not self.empty

    @property
    def pos(self):
        """return position of track in the playlist"""
        return int(self._pos)

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


def main():
    pass

# Script starts here
if __name__ == '__main__':
    main()

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
