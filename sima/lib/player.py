# -*- coding: utf-8 -*-

# TODO:
# Add decorator to filter through history?

from sima.lib.track import Track


class Player(object):

    """Player interface to inherit from.

    When querying palyer music library for tracks, Player instance *must* return
    Track objects (usually a list of them)
    """

    def __init__(self):
        self.state = {}
        self.current = {}

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
            >>> player.find_track('Nirvana', 'Nevermind')

        Returns a list of Track objects
        """

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

