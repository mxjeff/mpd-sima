# -*- coding: utf-8 -*-
# Public Domain
#
# Copyright 2007, 2009 Sander Marechal <s.marechal@jejik.com>
# http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
#
# Copyright 2010, 2011 Jack Kaliko <efrim@azylum.org>
# https://gitorious.org/python-daemon
#
#  This file is part of MPD_sima
#
#  MPD_sima is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MPD_sima is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MPD_sima.  If not, see <http://www.gnu.org/licenses/>.

import atexit
import os
import sys
import time
from signal import signal, SIGTERM, SIGHUP, SIGUSR1


class Daemon(object):
    """
    A generic daemon class.

    Usage: subclass the Daemon class and override the run() method

        Daemon([pidfile[, stdin[, stdout[, stderr]]]])

            pidfile : file to write pid to (default no pid file writen)
            stdin   : standard input file descriptor (default to /dev/null)
            stdout  : standard output file descriptor (default to /dev/null)
            stderr  : standard error file descriptorr (default to /dev/null)
    """
    version = '0.6'

    def __init__(self, pidfile,
            stdin = os.devnull,
            stdout = os.devnull,
            stderr = os.devnull):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile
        self.umask = 0

    def daemonize(self):
        """
        Do the UNIX double-fork magic.
        see W. Richard Stevens, "Advanced Programming in the Unix Environment"
        for details (ISBN 0201563177)

        Short explanation:
            Unix processes belong to "process group" which in turn lies within a
            "session".  A session can have a controlling tty.
            Forking twice allows to detach the session from a possible tty.
            The process lives then within the init process.
        """
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError as e:
            sys.stderr.write('fork #1 failed: {0.errno:d} ({0.strerror})\n'.format(e))
            sys.exit(1)

        # Decouple from parent environment
        os.chdir('/')
        os.setsid()
        self.umask = os.umask(0)

        # Do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError as e:
            sys.stderr.write('fork #2 failed: {0.errno:d} ({0.strerror})\n'.format(e))
            sys.exit(1)

        self.write_pid()
        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        # TODO: binary or txt mode?
        si = open(self.stdin,  mode='rb')
        so = open(self.stdout, mode='ab+')
        se = open(self.stderr, mode='ab+', buffering=0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        atexit.register(self.shutdown)
        self.signal_management()

    def write_pid(self):
        # write pidfile
        if not self.pidfile:
            return
        pid = str(os.getpid())
        try:
            os.umask(self.umask)
            open(self.pidfile, 'w').write('%s\n' % pid)
        except Exception as wpid_err:
            sys.stderr.write('Error trying to write pid file: {}\n'.format(wpid_err))
            sys.exit(1)
        os.umask(0)
        atexit.register(self.delpid)

    def signal_management(self):
        """Declare signal handlers
        """
        signal(SIGTERM, self.exit_handler)
        signal(SIGHUP, self.hup_handler)
        signal(SIGUSR1, self.hup_handler)

    def exit_handler(self, signum, frame):
        sys.exit(1)

    def hup_handler(self, signum, frame):
        """SIGHUP handler"""
        pass

    def delpid(self):
        """Remove PID file"""
        try:
            os.unlink(self.pidfile)
        except OSError as err:
            message = 'Error trying to remove PID file: {}\n'
            sys.stderr.write(message.format(err))

    def start(self):
        """
        Start the daemon
        """
        # Check for a pidfile to see if the daemon already runs
        try:
            pf = open(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if pid:
            message = 'pidfile {0.pidfile} already exist. Daemon already running?\n'
            sys.stderr.write(message.format(self))
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        self.run()

    def foreground(self):
        """
        Foreground/debug mode
        """
        self.write_pid()
        atexit.register(self.shutdown)
        self.run()

    def stop(self):
        """
        Stop the daemon
        """
        # Get the pid from the pidfile
        try:
            pf = open(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if not pid:
            message = 'pidfile {0.pidfile} does not exist. Is the Daemon running?\n'
            sys.stderr.write(message.format(self))
            return  # not an error in a restart

        # Try killing the daemon process
        try:
            os.kill(pid, SIGTERM)
            time.sleep(0.1)
        except OSError as err:
            if err.errno == 3:
                if os.path.exists(self.pidfile):
                    message = "Daemon's not running? removing pid file {0.pidfile}.\n"
                    sys.stderr.write(message.format(self))
                    os.remove(self.pidfile)
            else:
                sys.stderr.write(err.strerror)
                sys.exit(1)

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()

    def shutdown(self):
        """
        You should override this method when you subclass Daemon. It will be
        called when the process is being stopped.
        Pay attention:
        Daemon() uses atexit to call Daemon().shutdown(), as a consequence
        shutdown and any other functions registered via this module are not
        called when the program is killed by an un-handled/unknown signal.
        This is the reason of Daemon().signal_management() existence.
        """

    def run(self):
        """
        You should override this method when you subclass Daemon. It will be
        called after the process has been daemonized by start() or restart().
        """

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
