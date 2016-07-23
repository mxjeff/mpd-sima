# -*- coding: utf-8 -*-
# Copyright (c) 2013, 2014, 2015 Jack Kaliko <kaliko@azylum.org>
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
Add random title
"""

# standard library import
import random

# third parties components

# local import
from ...lib.plugin import Plugin
from ...lib.meta import Artist


class Random(Plugin):
    """Add random track
    TODO: refactor, this plugin does not look good to me.
          callback_need_track_fb/get_trk articulation is not elegant at all
    """

    def __init__(self, daemon):
        super().__init__(daemon)
        self.daemon = daemon
        if not self.plugin_conf:
            return
        self.mode = self.plugin_conf.get('flavour', None)
        if self.mode not in ['pure', 'sensible']:
            self.log.warning('Bad value for flavour, '
                             '"%s" not in ["pure", "sensible"]', self.mode)
            self.mode = 'pure'
        self.log.debug('Random flavour: %s', self.mode)

    def get_played_artist(self,):
        """Constructs list of already played artists.
        """
        duration = self.daemon.config.getint('sima', 'history_duration')
        tracks_from_db = self.daemon.sdb.get_history(duration=duration)
        # Construct Track() objects list from database history
        artists = [tr[-1] for tr in tracks_from_db]
        return set(artists)

    def callback_need_track(self):
        trks = list()
        target = self.plugin_conf.getint('track_to_add')
        limit = 0
        while len(trks) < target:
            trk = self.get_trk()
            if trk:
                trks.append(trk)
            else:
                limit += 1
                if limit > 3:
                    return trks
        return trks

    def get_trk(self):
        """Get a single track according to random flavour
        """
        trk = None
        art = None
        artists = list(self.player.artists)
        if self.mode == 'sensible':
            played_art = self.get_played_artist()
            while artists:
                art = random.choice(artists)
                if art not in played_art:
                    break
                artists.pop(art)
        elif self.mode == 'pure':
            art = random.choice(artists)
        if art is None:
            return None
        self.log.debug('Random art: {}'.format(art))
        trks = self.player.find_track(Artist(art))
        if trks:
            trk = random.choice(trks)
            self.log.info('Random candidate ({}): {}'.format(self.mode, trk))
        return trk



# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
