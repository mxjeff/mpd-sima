# -*- coding: utf-8 -*-

# Copyright (c) 2009 Evan Fosmark
# Copyright (c) 2014 Jack Kaliko <kaliko@azylum.org>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#

# https://github.com/dmfrey/FileLock
"""
Plain file lock to une in context:
    >>> with FileLock('/path/to/file/to/write'):
    >>>     # a lock file is maintain within the scope of this context:
    >>>     # /path/to/file/to/write.lock
    >>>     ... # process file writing
"""

import errno
import os
import time

class FileLockException(Exception):
    """FileLock Exception"""
    pass

class FileLock:
    """ A plain file lock whit context-manager"""

    def __init__(self, file_name, timeout=10, delay=.05):
        """
        Setup file lock.
        Setup timeout and the delay.
        """
        self.filedsc = None
        self.is_locked = False
        dirname = os.path.dirname(file_name)
        self.lockfile = os.path.join(dirname, '{0}.lock'.format(file_name))
        self.file_name = file_name
        self.timeout = timeout
        self.delay = delay

    def acquire(self):
        """Acquire the lock, if possible.
        """
        start_time = time.time()
        while True:
            try:
                self.filedsc = os.open(self.lockfile,
                                       os.O_CREAT|os.O_EXCL|os.O_RDWR)
                break
            except OSError as err:
                if err.errno != errno.EEXIST:
                    raise
                if (time.time() - start_time) >= self.timeout:
                    raise FileLockException('Timeout occured.')
                time.sleep(self.delay)
        self.is_locked = True

    def release(self):
        """Release the lock.
        """
        if self.is_locked:
            os.close(self.filedsc)
            os.unlink(self.lockfile)
            self.is_locked = False

    def __enter__(self):
        """start of the with statement.
        """
        if not self.is_locked:
            self.acquire()
        return self

    def __exit__(self, type, value, traceback):
        """end of the with statement
        """
        if self.is_locked:
            self.release()

    def __del__(self):
        """Cleanup
        """
        self.release()
