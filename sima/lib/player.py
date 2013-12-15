# -*- coding: utf-8 -*-

# TODO:
# Add decorator to filter through history?

# standard library import
import logging

# local import
#from sima.lib.track import Track


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
        *
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
