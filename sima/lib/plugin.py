# -*- coding: utf-8 -*-
# Copyright (c) 2013-2015 Jack Kaliko <kaliko@azylum.org>
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
"""
Plugin object to derive from
"""


class Plugin:
    """
    First non-empty line of the docstring is used as description
    Rest of the docstring at your convenience.

    The lowercased plugin Name MUST be the same as the module (file name),
    for instance Plugin → plugin.py
    It eases plugins discovery and simplifies the code to handle them,
    IMHO, it's a fair trade-off.
    """

    @classmethod
    def info(cls):
        """self documenting class method
        """
        doc = 'Undocumented plugin! Fill "{}" docstring'.format(cls.__name__)
        if cls.__doc__:
            doc = cls.__doc__.strip(' \n').splitlines()[0]
        return {'name': cls.__name__,
                'doc': doc,}

    def __init__(self, daemon):
        self.log = daemon.log
        self.__daemon = daemon
        self.player = daemon.player
        self.plugin_conf = None
        self.__get_config()

    def __str__(self):
        return self.__class__.__name__

    def __get_config(self):
        """Get plugin's specific configuration from global applications's config
        """
        conf = self.__daemon.config
        for sec in conf.sections():  # Discovering plugin conf
            if sec == self.__class__.__name__.lower():
                self.plugin_conf = conf[sec]
                if 'priority' not in self.plugin_conf:
                    self.plugin_conf['priority'] = '80'
        if not self.plugin_conf:
            self.plugin_conf = {'priority': '80'}
        #if self.plugin_conf:
        #    self.log.debug('Got config for {0}: {1}'.format(self,
        #                                                    self.plugin_conf))

    @property
    def priority(self):
        return self.plugin_conf.get('priority')

    def start(self):
        """
        Called when the daemon().run() is called and
        right after the player has connected successfully.
        """
        pass

    def callback_player(self):
        """
        Called on player changes, stopped, paused, skipped
        """
        pass

    def callback_player_database(self):
        """
        Called on player music library changes
        """
        pass

    def callback_playlist(self):
        """
        Called on playlist changes
        Not returning data
        """
        pass

    def callback_next_song(self):
        """
        Could be use to scrobble, maintain an history…
        Not returning data,
        """
        pass

    def callback_need_track(self):
        """
        Returns a list of Track objects to add
        """
        pass

    def callback_need_track_fb(self):
        """
        Called when callback_need_track failled to find tracks to queue
        Returns a list of Track objects to add
        """
        pass

    def shutdown(self):
        """Called on application shutdown"""
        pass


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
