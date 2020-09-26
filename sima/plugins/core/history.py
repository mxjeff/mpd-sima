# -*- coding: utf-8 -*-
# Copyright (c) 2013, 2014, 2020 kaliko <kaliko@azylum.org>
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
"""Add playing tracks to history
"""

# standard library import
from time import time

# third parties components

# local import
from ...lib.plugin import Plugin

class History(Plugin):
    """
    History management
    """
    def __init__(self, daemon):
        Plugin.__init__(self, daemon)
        self.sdb = daemon.sdb
        self._last_clean = time()

    def shutdown(self):
        self.log.info('Cleaning database')
        self.sdb.purge_history()
        self.sdb.clean_database()

    def callback_player(self):
        current = self.player.current
        last_hist = next(self.sdb.get_history(), None)
        if last_hist and last_hist[3] == current.file:
            return
        if not current:
            self.log.debug('Cannot add "%s" to history (empty or missing file)', current)
            return
        self.log.debug('add history: "%s"', current)
        self.sdb.add_history(current)
        if self._last_clean - time() > 86400:
            self.shutdown()
            self._last_clean = time()


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
