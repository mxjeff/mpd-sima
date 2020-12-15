# coding: utf-8
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
"""Testing Tags plugin config
"""

import argparse
import os.path
import sys

from configparser import ConfigParser

import musicpd

from ..plugins.internal.tags import forge_filter


def is_valid_file(parser, arg):
    if not os.path.exists(arg) or not os.path.isfile(arg):
        parser.error('The file "%s" does not exist!' % arg)
    else:
        return arg


def main():
    parser = argparse.ArgumentParser(description='Tests Tags plugin config')
    parser.add_argument('config', nargs=1,
                        type=lambda x: is_valid_file(parser, x))
    pargs = parser.parse_args(sys.argv[1:])
    conf = ConfigParser()
    conf.read(pargs.config)
    if not conf['tags']:
        print('Nothing in "tags" section', file=sys.stderr)
        sys.exit(1)
    tags_cfg = conf['tags']
    filt = forge_filter(tags_cfg)
    print(f'Filter forged: "{filt}"')
    host = conf['MPD'].get('host', None)
    port = conf['MPD'].get('port', None)
    cli = musicpd.MPDClient()
    try:
        cli.connect(host=host, port=port)
    except musicpd.ConnectionError as err:
        print(err, file=sys.stderr)
        sys.exit(1)
    try:
        res = cli.find(filt)
    except musicpd.CommandError as err:
        cli.disconnect()
        print(err, file=sys.stderr)
        sys.exit(1)
    print({trk.get('artist', 'ukn') for trk in res})


# Script starts here
if __name__ == '__main__':
    main()

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab fileencoding=utf8
