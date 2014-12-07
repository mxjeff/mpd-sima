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

# local import
from .simastr import SimaStr
from ..utils.leven import levenshtein_ratio

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

    def find_albums(self, artist):
        """
        Find albums by artist's name
            >>> player.find_alums('Nirvana')

        Returns a list of string objects
        """
        raise NotImplementedError

    def fuzzy_find_artist(self, artist):
        """
        Find artists based on a fuzzy search in the media library
            >>> bea = player.fuzzy_find_artist('beatles')
            >>> print(bea)
            >>> ['The Beatles']

        Returns a list of strings (artist names)
        """
        raise NotImplementedError

    def disconnect(self):
        """Closing client connection with the Player
        """
        raise NotImplementedError

    def connect(self):
        """Connect client to the Player
        """
        raise NotImplementedError

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
