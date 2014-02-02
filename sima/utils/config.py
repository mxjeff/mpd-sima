# -*- coding: utf-8 -*-

# Copyright (c) 2009, 2010, 2011, 2013 Jack Kaliko <kaliko@azylum.org>
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
Deal with configuration and data files.
Parse configuration file and set defaults for missing options.
"""

# IMPORTS
import configparser
import sys

from configparser import Error
from os import (makedirs, environ, stat, chmod)
from os.path import (join, isdir, isfile)
from stat import (S_IMODE, ST_MODE, S_IRWXO, S_IRWXG)

from . import utils

# DEFAULTS
DIRNAME = 'mpd_sima'
CONF_FILE = 'sima.cfg'

DEFAULT_CONF = {
        'MPD': {
            'host': "localhost",
            #'password': "",
            'port': "6600",
            },
        'sima': {
            'internal': "Crop, Lastfm, RandomFallBack",
            'contrib': "",
            'user_db': "false",
            'history_duration': "8",
            'queue_length': "1",
            },
        'daemon':{
            'daemon': "false",
            'pidfile': "",
            },
        'log': {
            'verbosity': "info",
            'logfile': "",
            },
        'echonest': {
            },
        'lastfm': {
            'dynamic': "10",
            'similarity': "15",
            'queue_mode': "track", #TODO control values
            'single_album': "false",
            'track_to_add': "1",
            'album_to_add': "1",
            'depth': "1",
            },
        'randomfallback': {
            'flavour': "sensible", # in pure, sensible, genre
            'track_to_add': "1",
            }
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

    def __init__(self, logger, options=None):
        # options settings priority:
        # defauts < conf. file < command line
        self.conf_file = options.get('conf_file')
        self.config = None
        self.defaults = dict(DEFAULT_CONF)
        self.startopt = options
        ## Sima sqlite DB
        self.db_file = None

        self.log = logger
        ## INIT CALLS
        self.use_envar()
        self.init_config()
        self.control_conf()
        self.supersedes_config_with_cmd_line_options()
        self.config['sima']['db_file'] = self.db_file

    def get_pw(self):
        try:
            self.config.getboolean('MPD', 'password')
            self.log.debug('No password set, proceeding without ' +
                           'authentication...')
            return None
        except ValueError:
            # ValueError if password not a boolean, hence an actual password.
            pwd = self.config.get('MPD', 'password')
            if not pwd:
                self.log.debug('Password set as an empty string.')
                return None
            return pwd

    def control_mod(self):
        """
        Controls conf file permissions.
        """
        mode = S_IMODE(stat(self.conf_file)[ST_MODE])
        self.log.debug('file permission is: %o' % mode)
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
            self.log.info('Env. variable MPD_HOST set to "%s"' % mpd_host)
            self.defaults['MPD']['host'] = mpd_host
        if passwd:
            self.log.info('Env. variable MPD_HOST contains password.')
            self.defaults['MPD']['password'] = passwd
        if mpd_port:
            self.log.info('Env. variable MPD_PORT set to "%s".'
                                  % mpd_port)
            self.defaults['MPD']['port'] = mpd_port

    def control_conf(self):
        """Get through options/values and set defaults if not in conf file."""
        # Control presence of obsolete settings
        for option in ['history', 'history_length', 'top_tracks']:
            if self.config.has_option('sima', option):
                self.log.warning('Obsolete setting found in conf file: "%s"'
                        % option)
        # Setting default if not specified
        for section in DEFAULT_CONF.keys():
            if section not in self.config.sections():
                self.log.debug('[%s] NOT in conf file' % section)
                self.config.add_section(section)
                for option in self.defaults[section]:
                    self.config.set(section,
                            option,
                            self.defaults[section][option])
                    self.log.debug(
                            'Setting option with default value: %s = %s' %
                            (option, self.defaults[section][option]))
            elif section in self.config.sections():
                self.log.debug('[%s] present in conf file' % section)
                for option in self.defaults[section]:
                    if self.config.has_option(section, option):
                        #self.log.debug(u'option "%s" set to "%s" in conf. file' %
                        #              (option, self.config.get(section, option)))
                        pass
                    else:
                        self.log.debug(
                                'Option "%s" missing in section "%s"' %
                                (option, section))
                        self.log.debug('=> setting default "%s" (may not suit you…)' %
                                       self.defaults[section][option])
                        self.config.set(section, option,
                                        self.defaults[section][option])

    def init_config(self):
        """
        Use XDG directory standard if exists
        else use "HOME/(.config|.local/share)/sima/"
        http://standards.freedesktop.org/basedir-spec/basedir-spec-0.6.html
        """

        homedir = environ.get('HOME')

        if environ.get('XDG_DATA_HOME'):
            data_dir = join(environ.get('XDG_DATA_HOME'), DIRNAME)
        elif self.startopt.get('var_dir'):
            # If var folder is provided via CLI set data_dir accordingly
            data_dir = join(self.startopt.get('var_dir'))
        elif (homedir and isdir(homedir) and homedir not in ['/']):
            data_dir = join(homedir, '.local', 'share', DIRNAME)
        else:
            self.log.error('Can\'t find a suitable location for data folder (XDG_DATA_HOME)')
            self.log.error('Please use "--var_dir" to set a proper location')
            sys.exit(1)

        if not isdir(data_dir):
            makedirs(data_dir)
            chmod(data_dir, 0o700)

        if self.startopt.get('conf_file'):
            # No need to handle conf file location
            pass
        elif environ.get('XDG_CONFIG_HOME'):
            conf_dir = join(environ.get('XDG_CONFIG_HOME'), DIRNAME)
        elif (homedir and isdir(homedir) and homedir not in ['/']):
            conf_dir = join(homedir, '.config', DIRNAME)
            # Create conf_dir if necessary
            if not isdir(conf_dir):
                makedirs(conf_dir)
                chmod(conf_dir, 0o700)
            self.conf_file = join(conf_dir, CONF_FILE)
        else:
            self.log.error('Can\'t find a suitable location for config folder (XDG_CONFIG_HOME)')
            self.log.error('Please use "--config" to locate the conf file')
            sys.exit(1)

        self.db_file = join(data_dir, 'sima.db')

        config = configparser.SafeConfigParser()
        # If no conf file present, uses defaults
        if not isfile(self.conf_file):
            self.config = config
            return

        self.log.info('Loading configuration from:  %s' % self.conf_file)
        self.control_mod()

        try:
            config.read(self.conf_file)
        except Error as err:
            self.log.error(err)
            sys.exit(1)

        self.config = config

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
