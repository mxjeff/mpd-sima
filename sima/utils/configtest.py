# coding: utf-8

import sys

from logging import getLogger

from ..mpdclient import MPD
from ..mpdclient import MPDError, PlayerError

from ..plugins.internal.tags import forge_filter, control_config

log = getLogger('sima')


def tags_config_test(cli, config):
    tags_cfg = config['tags']
    if not control_config(tags_cfg):
        return
    filt = forge_filter(tags_cfg)
    log.info('Trying tags and filter config:')
    log.info('%s', filt)
    try:
        # Use window to limit reponse size
        res = cli.find(filt, 'window', (0, 300))
    except MPDError as err:
        cli.disconnect()
        print('filter error: %s' % err, file=sys.stderr)
        sys.exit(1)
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
    try:
        cli.connect()
    except PlayerError as err:
        print(err, file=sys.stderr)
        sys.exit(1)
    tags_config_test(cli, config)


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab fileencoding=utf8
