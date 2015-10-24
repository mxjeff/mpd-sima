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
"""Sima
"""

# standard library import
import logging
import sys

from importlib import __import__ as sima_import
from os.path import isfile
##

# third parties components
##

# local import
from . import core, info
from .lib.logger import set_logger
from .lib.meta import Meta
from .lib.simadb import SimaDB
from .utils.config import ConfMan
from .utils.startopt import StartOpt
from .utils.utils import exception_log, SigHup
 # core plugins
from .plugins.core.history import History
from .plugins.core.mpdoptions import MpdOptions
from .plugins.core.uniq import Uniq
##


def load_plugins(sima, source):
    """Handles internal/external plugins
        sima:   sima.core.Sima instance
        source: ['internal', 'contrib']
    """
    if not sima.config.get('sima', source):
        return
    logger = logging.getLogger('sima')
    # TODO: Sanity check for "sima.config.get('sima', source)" ?
    for plugin in sima.config.get('sima', source).split(','):
        plugin = plugin.strip(' \n')
        module = 'sima.plugins.{0}.{1}'.format(source, plugin.lower())
        try:
            mod_obj = sima_import(module, fromlist=[plugin])
        except ImportError as err:
            logger.error('Failed to load "{}" plugin\'s module: '.format(plugin) +
                         '{0} ({1})'.format(module, err))
            sima.shutdown()
            sys.exit(1)
        try:
            plugin_obj = getattr(mod_obj, plugin)
        except AttributeError as err:
            logger.error('Failed to load plugin %s (%s)', plugin, err)
            sima.shutdown()
            sys.exit(1)
        logger.info('Loading {0} plugin: {name} ({doc})'.format(
            source, **plugin_obj.info()))
        sima.register_plugin(plugin_obj)


def start(sopt, restart=False):
    """starts application
    """
    # loads configuration
    config = ConfMan(sopt.options).config
    # set logger
    logger = logging.getLogger('sima')
    logfile = config.get('log', 'logfile', fallback=None)
    verbosity = config.get('log', 'verbosity')
    set_logger(verbosity, logfile)
    logger.debug('Command line say: %s', sopt.options)
    # Create Database
    db_file = config.get('sima', 'db_file')
    if (sopt.options.get('create_db', None)
            or not isfile(db_file)):
        logger.info('Creating database in "%s"', db_file)
        open(db_file, 'a').close()
        SimaDB(db_path=db_file).create_db()
        if sopt.options.get('create_db', None):
            logger.info('Done, bye...')
            sys.exit(0)

    if sopt.options.get('generate_config'):
        config.write(sys.stdout, space_around_delimiters=True)
        sys.exit(0)

    logger.info('Starting (%s)...', info.__version__)
    sima = core.Sima(config)

    # required core plugins
    core_plugins = [History, MpdOptions, Uniq]
    for cplgn in core_plugins:
        logger.debug('Register core {name} ({doc})'.format(**cplgn.info()))
        sima.register_core_plugin(cplgn)
    logger.debug('core loaded, prioriy: {}'.format(' > '.join(map(str, sima.core_plugins))))

    #  Loading internal plugins
    load_plugins(sima, 'internal')

    #  Loading contrib plugins
    load_plugins(sima, 'contrib')
    logger.info('plugins loaded, prioriy: {}'.format(' > '.join(map(str, sima.plugins))))
    #  Set use of MusicBrainzIdentifier
    if not config.getboolean('sima', 'musicbrainzid'):
        logger.info('Disabling MusicBrainzIdentifier')
        Meta.use_mbid = False

    # Run as a daemon
    if config.getboolean('daemon', 'daemon'):
        if restart:
            sima.run()
        else:
            logger.info('Daemonize process...')
            sima.start()

    try:
        sima.foreground()
    except KeyboardInterrupt:
        logger.info('Caught KeyboardInterrupt, stopping')
        sys.exit(0)


def run(sopt, restart=False):
    """
    Handles SigHup exception
    Catches Unhandled exception
    """
    # pylint: disable=broad-except
    try:
        start(sopt, restart)
    except SigHup:  # SigHup inherit from Exception
        run(sopt, True)
    except Exception:  # Unhandled exception
        exception_log()

# Script starts here
def main():
    """Entry point"""
    nfo = dict({'version': info.__version__,
                'prog': 'sima'})
    # StartOpt gathers options from command line call (in StartOpt().options)
    sopt = StartOpt(nfo)
    run(sopt)


if __name__ == '__main__':
    main()

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
