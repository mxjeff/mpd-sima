# -*- coding: utf-8 -*-
# Copyright (c) 2013, 2014 Jack Kaliko <kaliko@azylum.org>
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
    Deal with MPD options ‑ idle and repeat mode
"""

# standard library import

# third parties components

# local import
from ...lib.plugin import Plugin


class MpdOptions(Plugin):
    """
    Deal with MPD options - idle and repeat mode
    """

    def __init__(self, daemon):
        Plugin.__init__(self, daemon)
        self.daemon = daemon

    def callback_player(self):
        """
        Called on player changes
        """
        player = self.daemon.player
        if player.status().get('single') == str(1):
            self.log.info('MPD "single" mode activated.')
            self.daemon.enabled = False
        elif player.status().get('repeat') == str(1):
            self.log.info('MPD "repeat" mode activated.')
            self.daemon.enabled = False
        else:
            if self.daemon.enabled is False:
                self.log.debug('enabling queuing (leaving single|repeat mode)')
                self.daemon.enabled = True

    def shutdown(self):
        pass


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
