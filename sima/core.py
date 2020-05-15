# -*- coding: utf-8 -*-
# Copyright (c) 2009-2015, 2020 kaliko <kaliko@azylum.org>
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
"""Core Object dealing with plugins and player client
"""

import time

from collections import deque
from logging import getLogger

from .mpdclient import MPD as PlayerClient
from .mpdclient import PlayerError, MPDError
from .lib.simadb import SimaDB
from .lib.daemon import Daemon
from .utils.utils import SigHup


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
        self._plugins = list()
        self._core_plugins = list()
        self.player = PlayerClient(self)  # Player client
        self.short_history = deque(maxlen=60)

    def add_history(self):
        """Handle local, in memory, short history"""
        self.short_history.appendleft(self.player.current)

    def register_plugin(self, plugin_class):
        """Registers plugin in Sima instance..."""
        plgn = plugin_class(self)
        prio = int(plgn.priority)
        self._plugins.append((prio, plgn))

    def register_core_plugin(self, plugin_class):
        """Registers core plugins"""
        plgn = plugin_class(self)
        prio = int(plgn.priority)
        self._core_plugins.append((prio, plgn))

    def foreach_plugin(self, method, *args, **kwds):
        """Plugin's callbacks dispatcher"""
        self.log.trace('dispatching %s to plugins', method)  # pylint: disable=no-member
        for plugin in self.core_plugins:
            getattr(plugin, method)(*args, **kwds)
        for plugin in self.plugins:
            getattr(plugin, method)(*args, **kwds)

    @property
    def core_plugins(self):
        return [plugin[1] for plugin in
                sorted(self._core_plugins, key=lambda pl: pl[0], reverse=True)]

    @property
    def plugins(self):
        return [plugin[1] for plugin in sorted(self._plugins, key=lambda pl: pl[0], reverse=True)]

    def need_tracks(self):
        """Is the player in need for tracks"""
        if not self.enabled:
            self.log.debug('Queueing disabled!')
            return False
        queue_trigger = self.config.getint('sima', 'queue_length')
        if self.player.playmode.get('random'):
            queue = self.player.playlist
            self.log.debug('Currently %s track(s) in the playlist. (target %s)', len(queue), queue_trigger)
        else:
            queue = self.player.queue
            self.log.debug('Currently %s track(s) ahead. (target %s)', len(queue), queue_trigger)
        if len(queue) < queue_trigger:
            return True
        return False

    def queue(self):
        to_add = list()
        for plugin in self.plugins:
            self.log.info('callback_need_track: %s', plugin)
            pl_candidates = getattr(plugin, 'callback_need_track')()
            if pl_candidates:
                to_add.extend(pl_candidates)
            if to_add:
                break
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
            self.log.info('Trying to reconnect in %4d seconds', tmp)
            time.sleep(tmp)
            try:
                self.player.connect()
            except PlayerError as err:
                self.log.debug(err)
                continue
            except MPDError as err:
                #TODO: unhandled Player exceptions
                self.log.warning('Unhandled player exception: %s', err)
            self.log.info('Got reconnected')
            break
        self.foreach_plugin('start')

    def hup_handler(self, signum, frame):
        self.log.warning('Caught a sighup!')
        # Cleaning pending command
        self.player.clean()
        self.foreach_plugin('shutdown')
        self.player.disconnect()
        raise SigHup('SIGHUP caught!')

    def shutdown(self):
        """General shutdown method
        """
        self.log.warning('Starting shutdown.')
        # Cleaning pending command
        self.player.clean()
        self.foreach_plugin('shutdown')
        self.player.disconnect()

        self.log.info('The way is shut, it was made by those who are dead. '
                      'And the dead keep it…')
        self.log.info('bye...')

    def run(self):
        """
        """
        try:
            self.log.info('Connecting MPD: %(host)s:%(port)s', self.config['MPD'])
            self.player.connect()
            self.foreach_plugin('start')
        except (PlayerError, MPDError) as err:
            self.log.warning('Player: %s', err)
            self.reconnect_player()
        while 42:
            try:
                self.loop()
            except (PlayerError, MPDError) as err:
                self.log.warning('Player error: %s', err)
                self.reconnect_player()
                del self.changed

    def loop(self):
        """Dispatching callbacks to plugins
        """
        # hanging here until a monitored event is raised in the player
        if getattr(self, 'changed', False): # first iteration exception
            self.changed = self.player.monitor()
        else:  # first iteration goes through else
            self.changed = ['playlist', 'player', 'skipped']
        self.log.debug('changed: %s', ', '.join(self.changed))
        if 'playlist' in self.changed:
            self.foreach_plugin('callback_playlist')
        if 'player' in self.changed or 'options' in self.changed:
            self.foreach_plugin('callback_player')
        if 'database' in self.changed:
            self.foreach_plugin('callback_player_database')
        if 'skipped' in self.changed:
            if self.player.state == 'play':
                self.log.info('Playing: %s', self.player.current)
                self.add_history()
                self.foreach_plugin('callback_next_song')
        if self.need_tracks():
            self.queue()

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
