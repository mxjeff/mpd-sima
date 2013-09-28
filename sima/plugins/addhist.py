# -*- coding: utf-8 -*-
"""Add playing tracks to history
"""

# standard library import

# third parties components

# local import
from ..lib.plugin import Plugin

class History(Plugin):
    """
    History
    """
    def __init__(self, daemon):
        Plugin.__init__(self, daemon)
        self.sdb = daemon.sdb
        self.player = daemon.player

    def shutdown(self):
        self.log.info('Cleaning database')
        self.sdb.purge_history()
        self.sdb.clean_database()

    def callback_next_song(self):
        current = self.player.current
        self.log.debug('add history: "{}"'.format(current))
        self.sdb.add_history(current)


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
