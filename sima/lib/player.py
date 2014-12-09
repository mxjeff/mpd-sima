# -*- coding: utf-8 -*-
# Copyright (c) 2009-2014 Jack Kaliko <jack@azylum.org>
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

# TODO:
# Add decorator to filter through history?

# standard library import
import logging
from difflib import get_close_matches
from itertools import dropwhile

# local import
from .meta import Artist
from .simastr import SimaStr
from ..utils.leven import levenshtein_ratio

def blacklist(artist=False, album=False, track=False):
    #pylint: disable=C0111,W0212
    field = (album, track)
    def decorated(func):
        def wrapper(*args, **kwargs):
            if not args[0].database:
                return func(*args, **kwargs)
            cls = args[0]
            boolgen = (bl for bl in field)
            bl_fun = (cls.database.get_bl_album,
                      cls.database.get_bl_track,)
            #bl_getter = next(fn for fn, bl in zip(bl_fun, boolgen) if bl is True)
            bl_getter = next(dropwhile(lambda _: not next(boolgen), bl_fun))
            #cls.log.debug('using {0} as bl filter'.format(bl_getter.__name__))
            results = list()
            for elem in func(*args, **kwargs):
                if bl_getter(elem, add_not=True):
                    cls.log.debug('Blacklisted "{0}"'.format(elem))
                    continue
                if track and cls.database.get_bl_album(elem, add_not=True):
                    # filter album as well in track mode
                    # (artist have already been)
                    cls.log.debug('Blacklisted alb. "{0.album}"'.format(elem))
                    continue
                results.append(elem)
            return results
        return wrapper
    return decorated

def bl_artist(func):
    def wrapper(*args, **kwargs):
        cls = args[0]
        if not args[0].database:
            return func(*args, **kwargs)
        result = func(*args, **kwargs)
        if not result:
            return
        names = list()
        for art in result.names:
            if cls.database.get_bl_artist(art, add_not=True):
                cls.log.debug('Blacklisted "{0}"'.format(art))
                continue
            names.append(art)
        if not names:
            return
        resp = Artist(name=names.pop(), mbid=result.mbid)
        for name in names:
            resp.add_alias(name)
        return resp
    return wrapper


class Player(object):
    """Player interface to inherit from.

    When querying player music library for tracks, Player instance *must* return
    Track objects (usually a list of them)

    Player instance should expose the following immutable attributes:
        * artists
        * state
        * current
        * queue
        * playlist
    """

    def __init__(self):
        super().__init__()
        self.log = logging.getLogger('sima')

    def monitor(self):
        """Monitor player for change
        Returns :
            * database  player media library has changed
            * playlist  playlist modified
            * options   player options changed: repeat mode, etc…
            * player    player state changed: paused, stopped, skip track…
        """
        raise NotImplementedError

    def clean(self):
        """Any cleanup necessary"""
        pass

    def remove(self, position=0):
        """Removes the oldest element of the playlist (index 0)
        """
        raise NotImplementedError

    def find_track(self, artist, title=None):
        """
        Find tracks for a specific artist or filtering with a track title
            >>> player.find_track('The Beatles')
            >>> player.find_track('Nirvana', title='Smells Like Teen Spirit')

        Returns a list of Track objects
        """
        raise NotImplementedError

    def find_album(self, artist, album):
        """
        Find tracks by track's album name
            >>> player.find_album('Nirvana', 'Nevermind')

        Returns a list of Track objects
        """
        raise NotImplementedError

    def search_albums(self, artist):
        """
        Find albums by artist's name
            >>> art = Artist(name='Nirvana')
            >>> player.search_albums(art)

        Returns a list of string objects
        """
        raise NotImplementedError

    @bl_artist
    def search_artist(self, artist):
        """
        Search artists based on a fuzzy search in the media library
            >>> bea = player.search_artist('The beatles')
            >>> print(bea.names)
            >>> ['The Beatles', 'Beatles', 'the beatles']

        Returns a list of strings (artist names)
        """
        found = False
        # Then proceed with fuzzy matching if got nothing
        match = get_close_matches(artist.name, self.artists, 50, 0.73)
        if not match:
            return
        if len(match) > 1:
            self.log.debug('found close match for "%s": %s' %
                           (artist, '/'.join(match)))
        # Does not perform fuzzy matching on short and single word strings
        # Only lowercased comparison
        if ' ' not in artist.name and len(artist.name) < 8:
            for fuzz_art in match:
                # Regular lowered string comparison
                if artist.name.lower() == fuzz_art.lower():
                    artist.add_alias(fuzz_art)
                    return artist
        fzartist = SimaStr(artist.name)
        for fuzz_art in match:
            # Regular lowered string comparison
            if artist.name.lower() == fuzz_art.lower():
                found = True
                artist.add_alias(fuzz_art)
                if artist.name != fuzz_art:
                    self.log.debug('"%s" matches "%s".' % (fuzz_art, artist))
                continue
            # SimaStr string __eq__ (not regular string comparison here)
            if fzartist == fuzz_art:
                found = True
                artist.add_alias(fuzz_art)
                self.log.info('"%s" quite probably matches "%s" (SimaStr)' %
                              (fuzz_art, artist))
        if found:
            if artist.aliases:
                self.log.debug('Found: {}'.format('/'.join(artist.names)))
            return artist
        return

    def disconnect(self):
        """Closing client connection with the Player
        """
        raise NotImplementedError

    def connect(self):
        """Connect client to the Player
        """
        raise NotImplementedError

    @property
    def artists(self):
        raise NotImplementedError

    @property
    def state(self):
        raise NotImplementedError

    @property
    def current(self):
        raise NotImplementedError

    @property
    def queue(self):
        raise NotImplementedError

    @property
    def playlist(self):
        raise NotImplementedError

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
