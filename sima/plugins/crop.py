# -*- coding: utf-8 -*-
"""Crops playlist
"""

# standart library import
#from select import select

# third parties componants

# local import
from ..lib.plugin import Plugin

class Crop(Plugin):
    """
    Crop playlist on next track
    """

    def callback_playlist(self):
        player = self._Plugin__daemon.player
        target_lengh = 10
        while player.currentsong().pos > target_lengh:
            self.log.debug('cropping playlist')
            player.remove()


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
