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

from argparse import ArgumentParser, RawDescriptionHelpFormatter, SUPPRESS


from .utils import Wfile, Rfile, Wdir

DESCRIPTION = """
MPD_sima automagicaly queue new tracks in MPD playlist.

Command line options override their equivalent in configuration file.
If a positional arguments is provided MPD_sima execute the command and returns.
Commands available:
{}
"""


def clean_dict(to_clean):
    """Remove items which values are set to None/False"""
    for k in list(to_clean.keys()):
        if not to_clean.get(k):
            to_clean.pop(k)

# COMMANDS LIST
CMDS = {'config-test': 'Test configuration (MPD connection and Tags plugin only)',
        'create-db': 'Create the database',
        'generate-config': 'Generate a configuration file to stdout',
        'purge-history': 'Remove play history'
        }
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
    {  # TODO: To remove eventually in next major realese v0.18
        'sw': ['--generate-config'],
        'dest': 'generate_config',
        'action': 'store_true',
        'help': SUPPRESS},
    {
        'sw': ['--var-dir', '--var_dir'],
        'dest': 'var_dir',
        'action': Wdir,
        'help': 'directory to store var content (ie. database, cache)'},
    {  # TODO: To remove eventually in next major realese v0.18
        'sw': ['--create-db'],
        'action': 'store_true',
        'dest': 'create_db',
        'help': SUPPRESS},
    {
        'sw': ['command'],
        'nargs': '?',
        'choices': CMDS.keys(),
        'help': 'command to run (cf. description or unix manual for more)'},
]


class StartOpt:
    """Command line management.
    """

    def __init__(self, script_info,):
        self.parser = None
        self.info = dict(script_info)
        self.options = dict()
        self.main()

    def declare_opts(self):
        """
        Declare options in ArgumentParser object.
        """
        cmds = '\n'.join([f'    * {k}: {v}' for k, v in CMDS.items()])
        self.parser = ArgumentParser(description=DESCRIPTION.format(cmds),
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
