# -*- coding: utf-8 -*-
# Copyright (c) 2021 kaliko <kaliko@azylum.org>
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

import re

from logging import getLogger

from ..mpdclient import MPD, PlayerError

from ..plugins.internal.tags import forge_filter, control_config

log = getLogger('sima')


def tags_config_test(cli, config):
    tags_cfg = config['tags']
    if not control_config(tags_cfg):
        return
    filt = forge_filter(tags_cfg, log)
    log.info('Trying tags and filter config')
    log.debug('Complete filter (tag+filter): %s', filt)
    try:
        # Use window to limit reponse size
        res = cli.find(filt, 'window', (0, 300))
    except PlayerError as err:
        msg = re.split('{find}', str(err))
        if len(msg) == 2 and tags_cfg.get('filter'):
            log.info('user filter: %s', tags_cfg.get('filter'))
            log.error('failed to find tracks, error: %s', msg[1])
        raise PlayerError(err) from err
    artists = list({trk.albumartist for trk in res if trk.albumartist})
    if not artists:
        log.info('Tags config correct but got nothing from MPD\'s library')
        return
    log.info('Got results, here are some of the artists found:')
    log.info('%s', ' / '.join(artists[:6]))


def config_test(config):
    cli = MPD(config)
    log.info('Trying to connect MPD: %s:%s',
             config.get('MPD', 'host'),
             config.get('MPD', 'port'))
    cli.connect()
    if 'Tags' in config.get('sima', 'internal'):
        tags_config_test(cli, config)


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab fileencoding=utf8
