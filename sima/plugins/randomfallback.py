# -*- coding: utf-8 -*-
"""
Fetching similar artists from last.fm web services
"""

# standart library import
import random

# third parties componants

# local import
from ..lib.plugin import Plugin
from ..lib.track import Track


class RandomFallBack(Plugin):

    def __init__(self, daemon):
        Plugin.__init__(self, daemon)
        self.daemon = daemon
        ##
        self.to_add = list()

    def get_history(self):
        """Constructs list of Track for already played titles.
        """
        duration = self.daemon.config.getint('sima', 'history_duration')
        tracks_from_db = self.daemon.sdb.get_history(duration=duration,)
        # Construct Track() objects list from database history
        played_tracks = [Track(artist=tr[-1], album=tr[1], title=tr[2],
                               file=tr[3]) for tr in tracks_from_db]
        return played_tracks

    def callback_need_track_fb(self):
        mode = self.plugin_conf.get('flavour')
        art = random.choice(self.player.list('artist'))
        self.log.debug('Random art: {}'.format(art))
        trk  = random.choice(self.player.find_track(art))
        self.log.info('random fallback ({}): {}'.format(mode, trk))
        return [trk]



# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
