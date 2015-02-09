# -*- coding: utf-8 -*-
#
# Copyright (c) 2010, 2011, 2013, 2014, 2015 Jack Kaliko <kaliko@azylum.org>
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
"""generic tools and utilities for sima
"""
# pylint: disable=C0111

import logging
import traceback
import sys

from argparse import ArgumentError, Action
from base64 import b64decode as push
from codecs import getencoder
from datetime import datetime
from os import environ, access, getcwd, W_OK, R_OK
from os.path import dirname, isabs, join, normpath, exists, isdir, isfile
from time import sleep


def getws(dic):
    """
    Decode Obfuscated api key.
    Only preventing API keys harvesting over the network
    https://developer.echonest.com/forums/thread/105
    """
    aka = push(bytes(dic.get('apikey') + '=', 'utf-8'))
    aka = getencoder('rot-13')(str((aka), 'utf-8'))[0]
    dic.update({'apikey':aka})

def get_mpd_environ():
    """
    Retrieve MPD env. var.
    """
    passwd = host = None
    mpd_host_env = environ.get('MPD_HOST')
    if mpd_host_env:
        # If password is set:
        # mpd_host_env = ['pass', 'host'] because MPD_HOST=pass@host
        mpd_host_env = mpd_host_env.split('@')
        mpd_host_env.reverse()
        host = mpd_host_env[0]
        if len(mpd_host_env) > 1 and mpd_host_env[1]:
            passwd = mpd_host_env[1]
    return (host, environ.get('MPD_PORT', None), passwd)

def normalize_path(path):
    """Get absolute path
    """
    if not isabs(path):
        return normpath(join(getcwd(), path))
    return path

def exception_log():
    """Log unknown exceptions"""
    log = logging.getLogger(__name__)
    log.error('Unhandled Exception!!!')
    log.error(''.join(traceback.format_exc()))
    log.info('Please report the previous message'
             ' along with some log entries right before the crash.')
    log.info('thanks for your help :)')
    log.info('Quiting now!')
    sys.exit(1)


class SigHup(Exception):
    """SIGHUP raises this Exception"""
    pass

# ArgParse Callbacks
class Obsolete(Action):
    # pylint: disable=R0903
    """Deal with obsolete arguments
    """
    def __call__(self, parser, namespace, values, option_string=None):
        raise ArgumentError(self, 'obsolete argument')

class FileAction(Action):
    """Generic class to inherit from for ArgParse action on file/dir
    """
    # pylint: disable=R0903
    def __call__(self, parser, namespace, values, option_string=None):
        self._file = normalize_path(values)
        self._dir = dirname(self._file)
        self.parser = parser
        self.checks()
        setattr(namespace, self.dest, self._file)

    def checks(self):
        """control method
        """
        pass

class Wfile(FileAction):
    # pylint: disable=R0903
    """Is file writable
    """
    def checks(self):
        if isdir(self._file):
            self.parser.error('need a file not a directory: {}'.format(self._file))
        if not exists(self._dir):
            #raise ArgumentError(self, '"{0}" does not exist'.format(self._dir))
            self.parser.error('directory does not exist: {0}'.format(self._dir))
        if not exists(self._file):
            # Is parent directory writable then
            if not access(self._dir, W_OK):
                self.parser.error('no write access to "{0}"'.format(self._dir))
        else:
            if not access(self._file, W_OK):
                self.parser.error('no write access to "{0}"'.format(self._file))

class Rfile(FileAction):
    # pylint: disable=R0903
    """Is file readable
    """
    def checks(self):
        if not exists(self._file):
            self.parser.error('file does not exist: {0}'.format(self._file))
        if not isfile(self._file):
            self.parser.error('not a file: {0}'.format(self._file))
        if not access(self._file, R_OK):
            self.parser.error('no read access to "{0}"'.format(self._file))

class Wdir(FileAction):
    # pylint: disable=R0903
    """Is directory writable
    """
    def checks(self):
        if not exists(self._file):
            self.parser.error('directory does not exist: {0}'.format(self._file))
        if not isdir(self._file):
            self.parser.error('not a directory: {0}'.format(self._file))
        if not access(self._file, W_OK):
            self.parser.error('no write access to "{0}"'.format(self._file))

class Throttle:
    """throttle decorator"""
    def __init__(self, wait):
        self.wait = wait
        self.last_called = datetime.now()

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            while self.last_called + self.wait > datetime.now():
                sleep(0.1)
            result = func(*args, **kwargs)
            self.last_called = datetime.now()
            return result
        return wrapper

# http client exceptions (for webservices)

class WSError(Exception):
    pass

class WSNotFound(WSError):
    pass

class WSTimeout(WSError):
    pass

class WSHTTPError(WSError):
    pass


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
