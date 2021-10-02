# -*- coding: utf-8 -*-
# Copyright (c) 2020-2021 kaliko <kaliko@azylum.org>
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
Add titles based on Genre tag
"""

# standard library import
from collections import Counter
from random import shuffle

# third parties components

# local import
from ...lib.plugin import AdvancedPlugin
from ...lib.meta import Artist, MetaContainer
from ...utils.utils import PluginException


def forge_filter(genre):
    mpd_filter = f"(Genre == '{genre.strip()}')"
    # Ensure there is at least an artist name
    mpd_filter = f"({mpd_filter} AND (artist != ''))"
    return mpd_filter


class Genre(AdvancedPlugin):
    """Add track based on tags content
    """

    def __init__(self, daemon):
        super().__init__(daemon)
        self._setup_tagsneeded()

    def _setup_tagsneeded(self):
        """Ensure needed tags are exposed by MPD"""
        self.log.debug('%s plugin needs the following metadata: Genre', self)
        self.player.needed_tags |= {'genre'}

    def start(self):
        if (0, 21, 0) > tuple(map(int, self.player.mpd_version.split('.'))):
            self.log.warning('MPD protocol version: %s < 0.21.0',
                             self.player.mpd_version)
            self.log.error(
                'Need at least MPD 0.21 to use Genre plugin (filters required)')
            self.player.disconnect()
            raise PluginException('MPD >= 0.21 required')

    def fetch_genres(self):
        """Fetches ,at most, nb-depth genre from history,
        and returns the nbgenres most present"""
        depth = 10  # nb of genre to fetch from history for analysis
        nbgenres = 2  # nb of genre to return
        genres = [g[0] for g in self.sdb.fetch_genres_history(limit=depth)]
        if not genres:
            self.log.debug('No genre found in current track history')
            return []
        genres_analysis = Counter(genres)
        if genres_analysis.most_common():
            self.log.debug('Most common genres: %s', genres_analysis.most_common())
        return dict(genres_analysis.most_common(nbgenres)).keys()

    def callback_need_track(self):
        candidates = []
        queue_mode = self.plugin_conf.get('queue_mode', 'track')
        target = self.plugin_conf.getint(f'{queue_mode}_to_add')
        genres = self.fetch_genres()
        if not genres:
            self.log.warning('No genre tag set in current tracks!')
            return []
        self.log.info('Genre plugin looking for genre: %s', ' / '.join(genres))
        artists = MetaContainer([])
        for genre in genres:
            mpd_filter = forge_filter(genre)
            self.log.debug('mpd filter: %s', mpd_filter)
            _ = self.player.list('artist', mpd_filter)
            shuffle(_)
            artists |= MetaContainer([Artist(name=a) for a in _])
        if not artists:
            self.log.info('Genre plugin found nothing to queue')
            return []
        artists = self.get_reorg_artists_list(artists)
        self.log.debug('Genre plugin found: %s…', ' / '.join(map(str, artists[:4])))
        for artist in artists:
            self.log.debug('looking for %s', artist)
            tracks = self.player.find_tracks(artist)
            if not tracks:
                continue
            trk = self.filter_track(tracks, candidates)
            if not trk:
                continue
            if queue_mode == 'track':
                self.log.info('Genre plugin chose: %s', trk)
                candidates.append(trk)
                if len(candidates) == target:
                    break
            else:
                album = self.album_candidate(trk.Artist, unplayed=True)
                if not album:
                    continue
                candidates.extend(self.player.find_tracks(album))
                if len({t.album for t in candidates}) == target:
                    break
        return candidates

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
