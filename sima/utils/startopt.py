# -*- coding: utf-8 -*-

# Copyright (c) 2009-2015, 2021 kaliko <kaliko@azylum.org>
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

from argparse import ArgumentParser, RawDescriptionHelpFormatter

from .utils import Wfile, Rfile, Wdir

DESCRIPTION = """
MPD_sima automagicaly queue new tracks in MPD playlist.

Command line options override their equivalent in configuration file.
If a positional arguments is provided MPD_sima execute the command and returns.
"""


def clean_dict(to_clean):
    """Remove items which values are set to None/False"""
    for k in list(to_clean.keys()):
        if not to_clean.get(k):
            to_clean.pop(k)

# OPTIONS LIST
# pop out 'sw' value before creating Parser object.
# PAY ATTENTION:
#   If an option has to override its dual in conf file, the destination
#   identifier "dest" is to be named after that option in the conf file.
#   The supersedes_config_with_cmd_line_options method in ConfMan() (config.py)
#   is looking for command line option names identical to config file option
#   name it is meant to override.
OPTS = [
    {
        'sw': ['-l', '--log'],
        'type': str,
        'dest': 'logfile',
        'action': Wfile,
        'metavar': 'LOG',
        'help': 'file to log message to, default is stdout/stderr'},
    {
        'sw': ['-v', '--log-level'],
        'type': str,
        'dest': 'verbosity',
        'choices': ['debug', 'info', 'warning', 'error'],
        'help': 'log messages verbosity, default is info'},
    {
        'sw': ['-p', '--pid'],
        'dest': 'pidfile',
        'action': Wfile,
        'metavar': 'FILE',
        'help': 'file to save PID to, default is not to store pid'},
    {
        'sw': ['-d', '--daemon'],
        'dest': 'daemon',
        'action': 'store_true',
        'help': 'daemonize process'},
    {
        'sw': ['-S', '--host'],
        'dest': 'host',
        'help': 'host MPD in running on (IP or FQDN)'},
    {
        'sw': ['-P', '--port'],
        'type': int,
        'dest': 'port',
        'help': 'port MPD in listening on'},
    {
        'sw': ['-c', '--config'],
        'dest': 'conf_file',
        'action': Rfile,
        'metavar': 'CONFIG',
        'help': 'configuration file to load'},
    {
        'sw': ['--var-dir', '--var_dir'],
        'dest': 'var_dir',
        'action': Wdir,
        'help': 'directory to store var content (ie. database, cache)'},
]
# Commands
CMDS = [
        {'config-test': [{}], 'help': 'Test configuration (MPD connection and Tags plugin only)'},
        {'create-db': [{}], 'help': 'Create the database'},
        {'generate-config': [{}], 'help': 'Generate a configuration file to stdout'},
        {'purge-history': [{}], 'help': 'Remove play history'},
        {'bl-view': [{}], 'help': 'List blocklist IDs'},
        {'bl-add-artist': [
            {'name': 'artist', 'type': str, 'nargs': '?',
             'help': 'If artist is provided use it else use currently playing value'}
            ], 'help': 'Add artist to the blocklist'},
        {'bl-add-album': [
            {'name': 'album', 'type': str, 'nargs': '?',
             'help': 'If album is provided use it else use currently playing value'}
         ], 'help': 'Add album to the blocklist'},
        {'bl-add-track': [
            {'name': 'track', 'type': str, 'nargs': '?',
             'help': 'If track is provided use it else use currently playing value'}
         ], 'help': 'Add track to the blocklist'},
        {'bl-delete': [
            {'name': 'id', 'type': int, 'nargs': '?',
             'help': 'blocklist ID to suppress (use bl-view to list IDs)'}
         ], 'help': 'Remove entries from the blocklist'},
]


class StartOpt:
    """Command line management.
    """

    def __init__(self, script_info,):
        self.parser = None
        self.info = dict(script_info)
        self.options = {}
        self.main()

    def declare_opts(self):
        """
        Declare options in ArgumentParser object.
        """
        self.parser = ArgumentParser(description=DESCRIPTION,
                                     prog=self.info.get('prog'),
                                     epilog='Happy Listening',
                                     formatter_class=RawDescriptionHelpFormatter,
                                     )
        self.parser.add_argument('--version', action='version',
                        version='%(prog)s {version}'.format(**self.info))
        # Add all options declare in OPTS
        for opt in OPTS:
            opt_names = opt.pop('sw')
            self.parser.add_argument(*opt_names, **opt)
        # Add sub commands
        spa = self.parser.add_subparsers(
                title=f'{self.info["prog"]} commands as positional arguments',
                description=f"""Use them after optionnal arguments.\n"{self.info["prog"]} command -h" for more info.""",
                metavar='', dest='command')
        for cmd in CMDS:
            helpmsg = cmd.pop('help')
            cmd, args = cmd.popitem()
            _ = spa.add_parser(cmd, description=helpmsg, help=helpmsg)
            for arg in args:
                name = arg.pop('name', None)
                if name:
                    _.add_argument(name, **arg)

    def main(self):
        """
        Look for env. var and parse command line.
        """
        self.declare_opts()
        options = vars(self.parser.parse_args())
        # Set log file to os.devnull in daemon mode to avoid logging to
        # std(out|err).
        # TODO: Probably useless. To be checked
        #if options.__dict__.get('daemon', False) and \
        #        not options.__dict__.get('logfile', False):
        #    options.__dict__['logfile'] = devnull
        self.options.update(options)
        clean_dict(self.options)


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
