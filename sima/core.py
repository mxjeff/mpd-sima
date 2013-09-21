#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .client import PlayerClient

class Sima(object):
    """Main class, plugin and player management
    """

    def __init__(self):
        self.plugins = list()
        self.player = None
        self.connect_player()

    def register_plugin(self, plugin_class):
        self.plugins.append(plugin_class(self))

    def foreach_plugin(self, method, *args, **kwds):
        for plugin in self.plugins:
            getattr(plugin, method)(*args, **kwds)

    def connect_player(self):
        """Instanciate player client and connect it
        """
        self.player = PlayerClient()  # Player client
        self.player.connect()

    def shutdown(self):
        """General shutdown method
        """
        self.player.disconnect()
        self.foreach_plugin('shutdown')

    def run(self):
        """Dispatching callbacks to plugins
        """
        print(self.player.status())
        while 42:
            # hanging here untill a monitored event is raised in the player
            changed = self.player.monitor()
            print(changed)
            print(self.player.current)
            if 'playlist' in changed:
                self.foreach_plugin('callback_playlist')
            if 'player' in changed:
                pass



# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
