# -*- coding: utf-8 -*-
# Copyright (c) 2009, 2010, 2013, 2014, 2015 Jack Kaliko <kaliko@azylum.org>
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

DEBUG = logging.DEBUG
INFO = logging.INFO
ERROR = logging.ERROR
LOG_FORMATS = {
        DEBUG: '[{process}]{filename: >11}:{lineno: <3} {levelname: <7}: {message}',
        INFO:  '{levelname: <7}: {message}',
        #logging.DEBUG: '{asctime} {filename}:{lineno}({funcName}) '
                                 #'{levelname}: {message}',
        }
DATE_FMT = "%Y-%m-%d %H:%M:%S"


class LevelFilter(logging.Filter):
    """
    Enable logging between two log level by filtering everything < level.
    """
    def filter(self, record):
        """Defines loglevel"""
        return record.levelno <= ERROR


def set_logger(level='info', logfile=None):
    """
    logger:
        level: in debug, info, warning,…
        logfile: file to log to

    """
    name = 'sima'
    user_log_level = getattr(logging, level.upper())
    if user_log_level > DEBUG:
        log_format = LOG_FORMATS.get(INFO)
    else:
        log_format = LOG_FORMATS.get(DEBUG)
    logger = logging.getLogger(name)
    formatter = logging.Formatter(log_format, DATE_FMT, '{')
    logger.setLevel(user_log_level)
    filehdl = False
    if logger.handlers:
        for hdl in logger.handlers:
            hdl.setFormatter(formatter)
            if isinstance(hdl, logging.FileHandler):
                filehdl = True
            else:
                logger.removeHandler(hdl)

    if logfile:
        if filehdl:
            logger.handlers = []
        # Add timestamp for file handler
        log_format = '{0} {1}'.format('{asctime}', log_format)
        formatter = logging.Formatter(log_format, DATE_FMT, '{')
        # create file handler
        fileh = logging.FileHandler(logfile)
        fileh.setFormatter(formatter)
        logger.addHandler(fileh)
    else:
        if filehdl:
            logger.info('Not changing logging handlers, only updating formatter')
            return
        # create console handler with a specified log level (STDOUT)
        couth = logging.StreamHandler(sys.stdout)
        couth.addFilter(LevelFilter())

        # create console handler with warning log level (STDERR)
        cerrh = logging.StreamHandler()
        cerrh.setLevel(ERROR)

        # add formatter to the handlers
        cerrh.setFormatter(formatter)
        couth.setFormatter(formatter)

        # add the handlers to SIMA_LOGGER
        logger.addHandler(couth)
        #logger.addHandler(cerrh)  # Already added creating the handler‽ Still have to figure it out.

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
