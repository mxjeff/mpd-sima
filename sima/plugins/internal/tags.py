# -*- coding: utf-8 -*-
# Copyright (c) 2020, 2021 kaliko <kaliko@azylum.org>
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
import logging
import random

# third parties components
from musicpd import CommandError

# local import
from ...lib.plugin import AdvancedPlugin
from ...lib.meta import Artist, MetaContainer
from ...utils.utils import PluginException


def control_config(tags_config):
    log = logging.getLogger('sima')
    sup_tags = Tags.supported_tags
    config_tags = {k for k, v in tags_config.items()
                   if (v and k in Tags.supported_tags)}
    if not tags_config.get('filter', None) and \
            config_tags.isdisjoint(sup_tags):
        log.warning('Found no config for Tags plugin! '
                    'Need at least "filter" or a supported tag')
        log.info('Supported Tags are : %s', ', '.join(sup_tags))
        return False
    if config_tags.difference(sup_tags):
        log.error('Found unsupported tag in config: %s',
                  config_tags.difference(sup_tags))
        return False
    return True


def forge_filter(cfg, logger):
    """forge_filter merges tags config and user defined MPD filter into a single
    MPD filter"""
    tags = set(cfg.keys()) & Tags.supported_tags
    cfg_filter = cfg.get('filter', None)
    # Remove external enclosing parentheses in user defined MPD filter, for
    # instance  when there is more than one expression:
    #     ((genre == 'rock' ) AND (date =~ '198.'))
    # Even though it's a valid MPD filter, forge_filter will enclose it
    # properly. We do not want to through a syntax error at users since it's a
    # valid MPD filter, hence trying to transparently reformat the filter
    if cfg_filter.startswith('((') and cfg_filter.endswith('))'):
        logger.debug('Drop external enclosing parentheses in user filter: %s',
                     cfg_filter[1:-1])
        cfg['filter'] = cfg_filter[1:-1]
        cfg_filter = cfg['filter']
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
    # Ensure there is at least an artist name
    mpd_filter = f"({mpd_filter} AND (artist != ''))"
    return mpd_filter


class Tags(AdvancedPlugin):
    """Add track based on tags content
    """
    supported_tags = {'comment', 'date', 'genre', 'label', 'originaldate'}
    # options = {'queue_mode', 'priority', 'filter', 'track_to_add',
    #            'album_to_add'}

    def __init__(self, daemon):
        super().__init__(daemon)
        self._control_conf()
        self.mpd_filter = forge_filter(self.plugin_conf, self.log)
        self._setup_tagsneeded()
        self.log.debug('mpd filter: %s', self.mpd_filter)

    def _control_conf(self):
        if not control_config(self.plugin_conf):
            raise PluginException('plugin misconfiguration')

    def _setup_tagsneeded(self):
        """Ensure needed tags are exposed by MPD"""
        # At this point mpd_filter concatenetes {tags}+filter
        config_tags = set()
        for mpd_supp_tags in self.player.MPD_supported_tags:
            if mpd_supp_tags.lower() in self.mpd_filter.lower():
                config_tags.add(mpd_supp_tags.lower())
        self.log.debug('%s plugin needs the following metadata: %s',
                       self, config_tags)
        tags = config_tags & Tags.supported_tags
        self.player.needed_tags |= tags

    def start(self):
        if (0, 21, 0) > tuple(map(int, self.player.mpd_version.split('.'))):
            self.log.warning('MPD protocol version: %s < 0.21.0',
                             self.player.mpd_version)
            self.log.error(
                'Need at least MPD 0.21 to use Tags plugin (filters required)')
            self.player.disconnect()
            raise PluginException('MPD >= 0.21 required')
        if not self.plugin_conf['filter']:
            return
        # Check filter is valid
        try:
            # Use window to limit response size
            self.player.find(self.mpd_filter, "window", (0, 1))
        except CommandError as err:
            self.log.warning(err)
            raise PluginException('Badly formated filter in tags plugin configuration: "%s"'
                                  % self.plugin_conf['filter']) from err

    def callback_need_track(self):
        candidates = []
        queue_mode = self.plugin_conf.get('queue_mode', 'track')
        target = self.plugin_conf.getint(f'{queue_mode}_to_add')
        # look for artists acording to filter
        artists = [Artist(name=a) for a in self.player.list('artist', self.mpd_filter)]
        random.shuffle(artists)
        artists = MetaContainer(artists)
        if not artists:
            self.log.info('Tags plugin found nothing to queue')
            return candidates
        artists = self.get_reorg_artists_list(artists)
        self.log.debug('Tags plugin found: %s', ' / '.join(map(str, artists)))
        for artist in artists:
            self.log.debug('looking for %s', artist)
            tracks = self.player.find_tracks(artist)
            if not tracks:
                continue
            trk = self.filter_track(tracks, candidates)
            if not trk:
                continue
            if queue_mode == 'track':
                self.log.info('Tags plugin chose: %s', trk)
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
