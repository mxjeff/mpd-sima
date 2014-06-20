# -*- coding: utf-8 -*-
# Copyright (c) 2009, 2010, 2013, 2014 Jack Kaliko <kaliko@azylum.org>
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
Logging facility for sima.
"""

# standard library import
import logging
import sys


LOG_FORMATS = {
        logging.DEBUG: '[{process}]{filename: >11}:{lineno: <3} {levelname: <7}: {message}',
        logging.INFO:  '{levelname: <7}: {message}',
        #logging.DEBUG: '{asctime} {filename}:{lineno}({funcName}) '
                                 #'{levelname}: {message}',
        }
DATE_FMT = "%Y-%m-%d %H:%M:%S"


class LevelFilter(logging.Filter):# Logging facility
    """
    Enable logging between two log level by filtering everything < level.
    """

    def __init__(self, filt_level):
        logging.Filter.__init__(self)
        self.level = filt_level

    def filter(self, record):
        """Defines loglevel"""
        return record.levelno <= self.level


def set_logger(level='info', logfile=None):
    """
    logger:
        level: in debug, info, warning,…
        logfile: file to log to

    """
    name = 'sima'
    user_log_level = getattr(logging, level.upper())
    if user_log_level > logging.DEBUG:
        log_format = LOG_FORMATS.get(logging.INFO)
    else:
        log_format = LOG_FORMATS.get(logging.DEBUG)
    logg = logging.getLogger(name)
    formatter = logging.Formatter(log_format, DATE_FMT, '{')
    logg.setLevel(user_log_level)
    filehdl = False
    if logg.handlers:
        for hdl in logg.handlers:
            hdl.setFormatter(formatter)
            if isinstance(hdl, logging.FileHandler):
                filehdl = True
            else:
                logg.removeHandler(hdl)

    if logfile:
        if filehdl:
            logg.handlers = []
        # Add timestamp for file handler
        log_format = '{0} {1}'.format('{asctime}', log_format)
        formatter = logging.Formatter(log_format, DATE_FMT, '{')
        # create file handler
        fileh = logging.FileHandler(logfile)
        #fileh.setLevel(user_log_level)
        fileh.setFormatter(formatter)
        logg.addHandler(fileh)
    else:
        if filehdl:
            logg.info('Not changing logging handlers, only updating formatter')
            return
        # create console handler with a specified log level (STDOUT)
        couth = logging.StreamHandler(sys.stdout)
        #couth.setLevel(user_log_level)
        couth.addFilter(LevelFilter(logging.WARNING))

        # create console handler with warning log level (STDERR)
        cerrh = logging.StreamHandler(sys.stderr)
        #cerrh.setLevel(logging.WARNING)
        cerrh.setLevel(logging.ERROR)

        # add formatter to the handlers
        cerrh.setFormatter(formatter)
        couth.setFormatter(formatter)

        # add the handlers to SIMA_LOGGER
        logg.addHandler(couth)
        logg.addHandler(cerrh)

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
