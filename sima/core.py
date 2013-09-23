#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Core Object dealing with plugins and player client
"""

__version__ = '0.12.0.b'
__author__ = 'kaliko jack'
__url__ = 'git://git.kaliko.me/sima.git'

import sys
import time

from logging import getLogger

from .client import PlayerClient, Track
from .client import PlayerError, PlayerUnHandledError
from .lib.simadb import SimaDB

class Sima(object):
    """Main class, plugin and player management
    """

    def __init__(self, conf, dbfile):
        self.config = conf
        self.sdb = SimaDB(db_path=dbfile)
        self.log = getLogger('sima')
        self.plugins = list()
        self.player = PlayerClient()  # Player client
        try:
            self.player.connect()
        except (PlayerError, PlayerUnHandledError) as err:
            self.log.error('Fails to connect player: {}'.format(err))
            self.shutdown()
        self.current_track = None

    def register_plugin(self, plugin_class):
        """Registers plubin in Sima instance..."""
        self.plugins.append(plugin_class(self))

    def foreach_plugin(self, method, *args, **kwds):
        """Plugin's callbacks dispatcher"""
        for plugin in self.plugins:
            getattr(plugin, method)(*args, **kwds)

    def reconnect_player(self):
        """Trying to reconnect cycling through longer timeout
        cycle : 5s 10s 1m 5m 20m 1h
        """
        sleepfor = [5, 10, 60, 300, 1200, 3600]
        while True:
            tmp = sleepfor.pop(0)
            sleepfor.append(tmp)
            self.log.info('Trying to reconnect in {:>4d} seconds'.format(tmp))
            time.sleep(tmp)
            try:
                self.player.connect()
            except PlayerError:
                continue
            except PlayerUnHandledError as err:
                #TODO: unhandled Player exceptions
                self.log.warning('Unhandled player exception: %s' % err)
            self.log.info('Got reconnected')
            break

    def shutdown(self):
        """General shutdown method
        """
        self.log.warning('Starting shutdown.')
        self.player.disconnect()
        self.foreach_plugin('shutdown')

        self.log.info('The way is shut, it was made by those who are dead. '
                      'And the dead keep it…')
        self.log.info('bye...')
        sys.exit(0)

    def run(self):
        """
        """
        self.current_track = Track()
        while 42:
            try:
                self.loop()
            except PlayerUnHandledError as err:
                #TODO: unhandled Player exceptions
                self.log.warning('Unhandled player exception: {}'.format(err))
                del(self.player)
                self.player = PlayerClient()
                time.sleep(10)
            except PlayerError as err:
                self.log.warning('Player error: %s' % err)
                self.reconnect_player()

    def loop(self):
        """Dispatching callbacks to plugins
        """
        # hanging here untill a monitored event is raised in the player
        if getattr(self, 'changed', False): # first loop detection
            self.changed = self.player.monitor()
        else:
            self.changed = ['playlist', 'player', 'skipped']
        self.log.debug('changed: {}'.format(', '.join(self.changed)))
        if 'playlist' in self.changed:
            self.foreach_plugin('callback_playlist')
        if 'player' in self.changed:
            self.foreach_plugin('callback_player')
        if 'skipped' in self.changed:
            if self.player.state == 'play':
                self.log.info('Playing: {}'.format(self.player.current))
                self.foreach_plugin('callback_next_song')
                self.current_track = self.player.current


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
