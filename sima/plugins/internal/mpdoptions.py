# -*- coding: utf-8 -*-
"""
    Deal with MPD options ‑ idle and repeat mode
"""

# standard library import

# third parties components

# local import
from ...lib.plugin import Plugin


class MpdOptions(Plugin):
    """
    Deal with MPD options ‑ idle and repeat mode
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
