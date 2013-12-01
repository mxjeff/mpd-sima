# -*- coding: utf-8 -*-
"""Crops playlist
"""

# standart library import
#from select import select

# third parties componants

# local import
from ...lib.plugin import Plugin

class Crop(Plugin):
    """
    Crop playlist on next track
    kinda MPD's consume
    """
    def __init__(self, daemon):
        super().__init__(daemon)
        self.target = None
        if not self.plugin_conf:
            return
        target = self.plugin_conf.get('consume', None)
        if not target:
            return
        if not target.isdigit():
            self.log.warning('Bad value for consume, '
                    'expecting an integer, not "{}"'.format(target))
        else:
            self.target = int(target)

    def callback_playlist(self):
        if not self.target:
            return
        player = self._Plugin__daemon.player
        while player.currentsong().pos > self.target:
            self.log.debug('cropping playlist')
            player.remove()


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab