# -*- coding: utf-8 -*-
"""Core Object dealing with plugins and player client
"""

__version__ = '0.12.0pr1'
__author__ = 'kaliko jack'
__url__ = 'git://git.kaliko.me/sima.git'

import sys
import time

from collections import deque
from logging import getLogger

from .client import PlayerClient
from .client import PlayerError, PlayerUnHandledError
from .lib.simadb import SimaDB
from .lib.daemon import Daemon

class Sima(Daemon):
    """Main class, plugin and player management
    """

    def __init__(self, conf):
        ## Set daemon
        Daemon.__init__(self, conf.get('daemon', 'pidfile'))
        self.enabled = True
        self.config = conf
        self.sdb = SimaDB(db_path=conf.get('sima', 'db_file'))
        PlayerClient.database = self.sdb
        self.log = getLogger('sima')
        self.plugins = list()
        self.player = self.__get_player()  # Player client
        try:
            self.player.connect()
        except (PlayerError, PlayerUnHandledError) as err:
            self.log.error('Fails to connect player: {}'.format(err))
            self.shutdown()
        self.short_history = deque(maxlen=60)

    def __get_player(self):
        """Instanciate the player"""
        host = self.config.get('MPD', 'host')
        port = self.config.get('MPD', 'port')
        pswd = self.config.get('MPD', 'password', fallback=None)
        return PlayerClient(host, port, pswd)

    def add_history(self):
        self.short_history.appendleft(self.player.current)

    def register_plugin(self, plugin_class):
        """Registers plubin in Sima instance..."""
        self.plugins.append(plugin_class(self))

    def foreach_plugin(self, method, *args, **kwds):
        """Plugin's callbacks dispatcher"""
        for plugin in self.plugins:
            #self.log.debug('dispatching {0} to {1}'.format(method, plugin))
            getattr(plugin, method)(*args, **kwds)

    def need_tracks(self):
        if not self.enabled:
            self.log.debug('Queueing disabled!')
            return False
        queue = self.player.queue
        queue_trigger = self.config.getint('sima', 'queue_length')
        self.log.debug('Currently {0} track(s) ahead. (target {1})'.format(
                       len(queue), queue_trigger))
        if len(queue) < queue_trigger:
            return True
        return False

    def queue(self):
        to_add = list()
        for plugin in self.plugins:
            pl_callback =  getattr(plugin, 'callback_need_track')()
            if pl_callback:
                to_add.extend(pl_callback)
        if not to_add:
            self.log.warning('Queue plugins returned nothing!')
            for plugin in self.plugins:
                pl_callback =  getattr(plugin, 'callback_need_track_fb')()
                if pl_callback:
                    to_add.extend(pl_callback)
        for track in to_add:
            self.player.add(track)

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

    def run(self):
        """
        """
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
        if getattr(self, 'changed', False): # first iteration exception
            self.changed = self.player.monitor()
        else:  # first iteration goes through else
            self.changed = ['playlist', 'player', 'skipped']
        self.log.debug('changed: {}'.format(', '.join(self.changed)))
        if 'playlist' in self.changed:
            self.foreach_plugin('callback_playlist')
        if ('player' in self.changed
            or 'options' in self.changed):
            self.foreach_plugin('callback_player')
        if 'database' in self.changed:
            self.foreach_plugin('callback_player_database')
        if 'skipped' in self.changed:
            if self.player.state == 'play':
                self.log.info('Playing: {}'.format(self.player.current))
                self.add_history()
                self.foreach_plugin('callback_next_song')
        if self.need_tracks():
            self.queue()

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
