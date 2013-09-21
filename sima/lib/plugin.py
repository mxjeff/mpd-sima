# -*- coding: utf-8 -*-

class Plugin():
    def __init__(self, daemon):
        self.__daemon = daemon
        #self.history = daemon.player.history

    @property
    def name(self):
        return self.__class__.__name__.lower()

    def callback_playlist(self):
        """
        Called on playlist changes

        Not returning data
        """
        pass

    def callback_next_song(self):
        """Not returning data,
        Could be use to scrobble
        """
        pass

    def callback_need_song(self):
        """Returns a list of Track objects to add
        """
        pass

    def callback_player_stop(self):
        """Not returning data,
        Could be use to ensure player never stops
        """
        pass

    def shutdown(self):
        pass


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
