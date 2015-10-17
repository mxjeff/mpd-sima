# -*- coding: utf-8 -*-
# Copyright (c) 2009, 2010, 2011, 2013, 2014, 2015 Jack Kaliko <kaliko@azylum.org>
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
# pylint: disable=bad-continuation

"""
Deal with configuration and data files.
Parse configuration file and set defaults for missing options.
"""

# IMPORTS
import configparser
import logging
import sys

from configparser import Error
from os import (access, makedirs, environ, stat, chmod, W_OK)
from os.path import (join, isdir, isfile, dirname, exists)
from stat import (S_IMODE, ST_MODE, S_IRWXO, S_IRWXG)

from . import utils

# DEFAULTS
DIRNAME = 'mpd_sima'
CONF_FILE = 'mpd_sima.cfg'

DEFAULT_CONF = {
        'MPD': {
            'host': "localhost",
            #'password': "",
            'port': 6600,
            },
        'sima': {
            'internal': "Crop, Lastfm, Random",
            'contrib': "",
            'user_db': "false",
            'history_duration': 8,
            'queue_length': 2,
            'var_dir': 'empty',
            'musicbrainzid': "true",
            },
        'daemon':{
            'daemon': False,
            'pidfile': "",
            },
        'log': {
            'verbosity': "info",
            'logfile': "",
            },
        'crop': {
            'consume': 10,
            'priority': 0,
            },
        'echonest': {
            'queue_mode': "track", #TODO control values
            'max_art': 15,
            'single_album': "false",
            'track_to_add': 1,
            'album_to_add': 1,
            'depth': 1,
            'priority': 100,
            },
        'lastfm': {
            'queue_mode': "track", #TODO control values
            'max_art': 10,
            'single_album': "false",
            'track_to_add': 1,
            'album_to_add': 1,
            'depth': 1,
            'cache': True,
            'priority': 100,
            },
        'random': {
            'flavour': "sensible", # in pure, sensible
            'track_to_add': 1,
            'priority': 50,
            },
        }
#


class ConfMan(object):  # CONFIG MANAGER CLASS
    """
    Configuration manager.
    Default configuration is stored in DEFAULT_CONF dictionnary.
    First init_config() run to get config from file.
    Then control_conf() is run and retrieve configuration from defaults if not
    set in conf files.
    These settings are then updated with command line options with
    supersedes_config_with_cmd_line_options().

    Order of priority for the origin of an option is then (lowest to highest):
        * DEFAULT_CONF
        * Env. Var for MPD host, port and password
        * configuration file (overrides previous)
        * command line options (overrides previous)
    """

    def __init__(self, options=None):
        self.log = logging.getLogger('sima')
        # options settings priority:
        # defauts < env. var. < conf. file < command line
        self.conf_file = options.get('conf_file')
        self.config = configparser.ConfigParser(inline_comment_prefixes='#')
        self.config.read_dict(DEFAULT_CONF)
        # update DEFAULT_CONF with env. var.
        self.use_envar()
        self.startopt = options

        ## INIT CALLS
        self.init_config()
        self.supersedes_config_with_cmd_line_options()
        # Controls files access
        self.control_facc()
        # set dbfile
        self.config['sima']['db_file'] = join(self.config['sima']['var_dir'], 'sima.db')

        # Create directories
        data_dir = self.config['sima']['var_dir']
        if not isdir(data_dir):
            self.log.trace('Creating "{}"'.format(data_dir))
            makedirs(data_dir)
            chmod(data_dir, 0o700)

    def control_facc(self):
        """Controls file access.
        This is relevant only for file provided through the configuration file
        since files provided on the command line are already checked with
        argparse.
        """
        ok = True
        for op, ftochk in [('logfile', self.config.get('log', 'logfile')),
                           ('pidfile', self.config.get('daemon', 'pidfile')),]:
            if not ftochk:
                continue
            if isdir(ftochk):
                self.log.critical('Need a file not a directory: "%s"', ftochk)
                ok = False
            if not exists(ftochk):
                # Is parent directory writable then
                filedir = dirname(ftochk)
                if not access(filedir, W_OK):
                    self.log.critical('no write access to "%s" (%s)', filedir, op)
                    ok = False
            else:
                if not access(ftochk, W_OK):
                    self.log.critical('no write access to "%s" (%s)', ftochk, op)
                    ok = False
        if not ok:
            if exists(self.conf_file):
                self.log.warning('Try to check the configuration file: %s', self.conf_file)
            sys.exit(2)

    def control_mod(self):
        """
        Controls conf file permissions.
        """
        mode = S_IMODE(stat(self.conf_file)[ST_MODE])
        self.log.debug('file permission is: %o', mode)
        if mode & S_IRWXO or mode & S_IRWXG:
            self.log.warning('File is readable by "other" and/or' +
                             ' "group" (actual permission %o octal).' %
                             mode)
            self.log.warning('Consider setting permissions' +
                             ' to 600 octal.')

    def supersedes_config_with_cmd_line_options(self):
        """Updates defaults settings with command line options"""
        for sec in self.config.sections():
            for opt in self.config.options(sec):
                if opt in list(self.startopt.keys()):
                    self.config.set(sec, opt, str(self.startopt.get(opt)))

    def use_envar(self):
        """Use MPD en.var. to set defaults"""
        mpd_host, mpd_port, passwd = utils.get_mpd_environ()
        if mpd_host:
            self.log.info('Env. variable MPD_HOST set to "%s"', mpd_host)
            self.config['MPD'].update(host=mpd_host)
        if passwd:
            self.log.info('Env. variable MPD_HOST contains password.')
            self.config['MPD'].update(password=passwd)
        if mpd_port:
            self.log.info('Env. variable MPD_PORT set to "%s".', mpd_port)
            self.config['MPD'].update(port=mpd_port)

    def init_config(self):
        """
        Use XDG directory standard if exists
        else use "HOME/(.config|.local/share)/sima/"
        http://standards.freedesktop.org/basedir-spec/basedir-spec-0.6.html
        """

        homedir = environ.get('HOME')

        if environ.get('XDG_DATA_HOME'):
            data_dir = join(environ.get('XDG_DATA_HOME'), DIRNAME)
        elif homedir and isdir(homedir) and homedir not in ['/']:
            data_dir = join(homedir, '.local', 'share', DIRNAME)
        else:
            self.log.critical('Can\'t find a suitable location for data folder (XDG_DATA_HOME)')
            self.log.critical('Please use "--var-dir" to set a proper location')
            sys.exit(1)

        if self.startopt.get('conf_file'):
            # No need to handle conf file location
            pass
        elif environ.get('XDG_CONFIG_HOME'):
            conf_dir = join(environ.get('XDG_CONFIG_HOME'), DIRNAME)
        elif homedir and isdir(homedir) and homedir not in ['/']:
            conf_dir = join(homedir, '.config', DIRNAME)
            self.conf_file = join(conf_dir, CONF_FILE)
        else:
            self.log.critical('Can\'t find a suitable location for config folder (XDG_CONFIG_HOME)')
            self.log.critical('Please use "--config" to locate the conf file')
            sys.exit(1)

        ## Sima sqlite DB
        self.config['sima']['var_dir'] = join(data_dir)

        # If no conf file present, uses defaults
        if not isfile(self.conf_file):
            return

        self.log.info('Loading configuration from:  %s', self.conf_file)
        self.control_mod()

        try:
            self.config.read(self.conf_file)
        except Error as err:
            self.log.error(err)
            sys.exit(1)

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
