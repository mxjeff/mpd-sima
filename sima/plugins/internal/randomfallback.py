# -*- coding: utf-8 -*-
"""
Fetching similar artists from last.fm web services
"""

# standard library import
import random

# third parties components

# local import
from ...lib.plugin import Plugin
from ...lib.track import Track


class RandomFallBack(Plugin):

    def __init__(self, daemon):
        super().__init__(daemon)
        self.daemon = daemon
        if not self.plugin_conf:
            return
        self.mode = self.plugin_conf.get('flavour', None)
        if self.mode not in ['pure', 'sensible', 'genre']:
            self.log.warning('Bad value for flavour, '
                    '{} not in ["pure", "sensible", "genre"]'.format(self.mode))
            self.mode = 'pure'

    def get_played_artist(self,):
        """Constructs list of already played artists.
        """
        duration = self.daemon.config.getint('sima', 'history_duration')
        tracks_from_db = self.daemon.sdb.get_history(duration=duration)
        # Construct Track() objects list from database history
        artists = [ tr[-1] for tr in tracks_from_db ]
        return set(artists)

    def callback_need_track_fb(self):
        art = random.choice(self.player.list('artist'))
        self.log.debug('Random art: {}'.format(art))
        if self.mode == 'sensitive':
            played_art = self.get_played_artist()
            while 42:
                art = random.choice(self.player.list('artist'))
                if art not in played_art:
                    break
        trk  = random.choice(self.player.find_track(art))
        self.log.info('random fallback ({}): {}'.format(self.mode, trk))
        return [trk]



# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
