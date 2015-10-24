# -*- coding: utf-8 -*-
# Copyright (c) 2014 Jack Kaliko <kaliko@azylum.org>
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
    Publish presence on the MPD host message bus

    Notifies when concurrent instance run on the same host.
"""

# standard library import
from os import  getpid
from socket import getfqdn

# third parties components

# local import
from ...client import PlayerError
from ...lib.plugin import Plugin


class Uniq(Plugin):
    """
    Publish presence on the MPD host message bus
    """

    def __init__(self, daemon):
        Plugin.__init__(self, daemon)
        self.chan = 'mpd_sima:{0}.{1}'.format(getfqdn(), getpid())
        self.channels = []
        self._registred = False

    def start(self):
        if not self.is_capable():
            self.log.warning('MPD does not provide client to client')
            return
        self.is_uniq()
        if not self._registred:
            self.sub_chan()

    def is_capable(self):
        if {'channels', 'subscribe'}.issubset(set(self.player.commands())):
            # Groove Basin compatibility
            # For some reason Groove Basin have channels command but no
            # subscribe command‽
            return True

    def get_channels(self):
        return [chan for chan in self.player.channels() if
                chan.startswith('mpd_sima') and chan != self.chan]

    def is_uniq(self):
        channels = self.get_channels()
        if channels:
            self.log.warning('Another instance is queueing on this MPD host')
            self.log.warning(' '.join(channels))

    def sub_chan(self):
        self.log.debug('Registering as {}'.format(self.chan))
        try:
            self.player.subscribe(self.chan)
            self._registred = True
        except PlayerError as err:
            self.log.error('Failed to register: %s', err)

    def callback_need_track(self):
        if self.is_capable():
            self.is_uniq()


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
