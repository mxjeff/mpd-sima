# -*- coding: utf-8 -*-
# Copyright (c) 2020 kaliko <kaliko@azylum.org>
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
Add titles based on tags
"""

# standard library import
import random

# third parties components
from musicpd import CommandError

# local import
from ...lib.plugin import Plugin
from ...lib.track import Track
from ...utils.utils import PluginException


def forge_filter(cfg):
    tags = set(cfg.keys()) & Tags.supported_tags
    cfg_filter = cfg.get('filter', None)
    mpd_filter = []
    if cfg_filter:
        mpd_filter.append(cfg_filter)
    for tag in tags:
        if not cfg[tag]:  # avoid empty tags entries in config
            continue
        if ',' in cfg[tag]:
            patt = '|'.join(map(str.strip, cfg[tag].split(',')))
            mpd_filter.append(f"({tag} =~ '({patt})')")
        else:
            mpd_filter.append(f"({tag} == '{cfg[tag].strip()}')")
    mpd_filter = ' AND '.join(mpd_filter)
    if 'AND' in mpd_filter:
        mpd_filter = f'({mpd_filter})'
    return mpd_filter


class Tags(Plugin):
    """Add track based on tags content
    """
    supported_tags = {'comment', 'date', 'genre', 'label', 'originaldate'}

    def __init__(self, daemon):
        super().__init__(daemon)
        self.daemon = daemon
        self._control_conf()
        self._setup_tagsneeded()
        self.mpd_filter = forge_filter(self.plugin_conf)
        self.log.debug('mpd filter: %s', self.mpd_filter)

    def _control_conf(self):
        sup_tags = Tags.supported_tags
        config_tags = {k for k, v in self.plugin_conf.items()
                       if (v and k not in ['filter', 'priority', 'track_to_add'])}
        if not self.plugin_conf.get('filter', None) and \
                config_tags.isdisjoint(sup_tags):
            self.log.error('Found no config for %s plugin! '
                           'Need at least "filter" or a supported tag', self)
            self.log.info('Supported Tags are : %s', ', '.join(sup_tags))
            raise PluginException('plugin misconfiguration')
        if config_tags.difference(sup_tags):
            self.log.error('Found unsupported tag in config: %s',
                           config_tags.difference(sup_tags))
            raise PluginException('plugin misconfiguration')

    def _setup_tagsneeded(self):
        config_tags = {k for k, v in self.plugin_conf.items() if v}
        self.log.debug('%s plugin needs the followinng metadata: %s',
                       self, config_tags & Tags.supported_tags)
        tags = config_tags & Tags.supported_tags
        self.player.needed_tags |= tags

    def _get_history(self):
        """Constructs list of already played artists.
        """
        duration = self.daemon.config.getint('sima', 'history_duration')
        tracks_from_db = self.daemon.sdb.get_history(duration=duration)
        hist = [Track(file=tr[3], artist=tr[0]) for tr in tracks_from_db]
        return hist

    def start(self):
        if (0, 21, 0) > tuple(map(int, self.player.mpd_version.split('.'))):
            self.log.warning('MPD protocol version: %s < 0.21.0',
                             self.player.mpd_version)
            self.log.error(
                'Need at least MPD 0.21 to use Tags plugin (filters required)')
            self.player.disconnect()
            raise PluginException('MPD >= 0.21 required')
        # Check filter is valid
        try:
            if self.plugin_conf['filter']:
                self.player.find(self.plugin_conf['filter'])
        except CommandError:
            raise PluginException('Badly formated filter in tags plugin configuration: "%s"'
                                  % self.plugin_conf['filter'])

    def callback_need_track(self):
        candidates = []
        target = self.plugin_conf.getint('track_to_add')
        tracks = self.player.find(self.mpd_filter)
        random.shuffle(tracks)
        history = self._get_history()
        while tracks:
            trk = tracks.pop()
            if trk in self.player.queue or \
               trk in candidates:
                self.log.debug('%s already queued', trk)
                continue
            if trk in history:
                self.log.debug('%s in history', trk)
                continue
            candidates.append(trk)
            self.log.info('Tags candidate: {}'.format(trk))
            if len(candidates) >= target:
                break
        if not candidates:
            self.log.info('Tags plugin failed to find some tracks')
        return candidates

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
