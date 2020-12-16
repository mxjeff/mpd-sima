# -*- coding: utf-8 -*-
# Copyright (c) 2013-2015, 2020 kaliko <kaliko@azylum.org>
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
"""Crops playlist
"""

# standard library import

# third parties components

# local import
from ...lib.plugin import Plugin


class Crop(Plugin):
    """
    Crop playlist on next track
    """
    def __init__(self, daemon):
        super().__init__(daemon)
        self.daemon = daemon
        self.target = None
        if not self.plugin_conf:
            return
        target = self.plugin_conf.get('consume')
        if not target:
            return
        try:
            if int(target) < 0:
                self.log.info('Negative value for consume, not cropping')
                return
        except ValueError:
            self.log.warning('Bad value for consume, '
                             'expecting an integer, not "%s"', target)
        else:
            self.target = int(target)
            self.log.debug('Cropping at %s', self.target)

    def callback_next_song(self):
        if not self.target:
            return
        if not self.daemon.enabled:
            self.log.debug('Queueing disabled, not cropping')
            return
        player = self.daemon.player
        if player.currentsong().pos > self.target:
            self.log.debug('cropping playlist')
        while player.currentsong().pos > self.target:
            player.delete(0)


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
