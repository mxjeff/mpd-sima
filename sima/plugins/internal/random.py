# -*- coding: utf-8 -*-
# Copyright (c) 2013-2015, 2020-2021 kaliko <kaliko@azylum.org>
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
    """

    def __init__(self, daemon):
        super().__init__(daemon)
        self.mode = self.plugin_conf.get('flavour', None)
        if self.mode not in ['pure', 'sensible']:
            self.log.warning('Bad value for flavour, '
                             '"%s" not in ["pure", "sensible"]', self.mode)
            self.mode = 'pure'
        self.log.debug('Random flavour: %s', self.mode)
        self.candidates = []

    def get_played_artist(self,):
        """Constructs list of already played artists."""
        duration = self.main_conf.getint('sima', 'history_duration')
        artists = self.sdb.fetch_artists_history(duration=duration)
        return artists

    def filtered_artist(self, artist):
        """Filters artists:
         * not already queued

        If sensible random is set:
         * not in recent history
         * not in blocklist
        """
        if self.mode == 'sensible':
            if self.sdb.get_bl_artist(Artist(artist), add=False):
                self.log.debug('Random plugin: Blacklisted "%s"', artist)
                return True
            if artist in self.get_played_artist():
                return True
        if artist in self.player.queue:
            return True
        if artist in self.candidates:
            return True
        return False

    def callback_need_track(self):
        self.candidates = []
        trks = []
        target = self.plugin_conf.getint('track_to_add')
        artists = self.player.list('artist', '( artist != "")')
        random.shuffle(artists)
        for art in artists:  # artists is a list of strings here
            if self.filtered_artist(art):
                continue
            self.log.debug('Random art: %s', art)
            trks = self.player.find_tracks(Artist(art))
            if trks:
                trk = random.choice(trks)
                self.candidates.append(trk)
                self.log.info('Random plugin chose (%s): %s', self.mode, trk)
            if len(self.candidates) >= target:
                break
        return self.candidates

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
