# -* coding: utf-8 -*-
"""MPD client for Sima

This client is built above python-musicpd a fork of python-mpd
"""

# standart library import
from select import select

# third parties componants
try:
    from musicpd import (MPDClient, MPDError, CommandError)
except ImportError as err:
    from sys import exit as sexit
    print('ERROR: missing python-musicpd?\n{0}'.format(err))
    sexit(1)

# local import
from .lib.player import Player
from .lib.track import Track


class PlayerError(Exception):
    """Fatal error in poller."""

class PlayerCommandError(PlayerError):
    """Command error"""

PlayerUnHandledError = MPDError

class PlayerClient(Player):
    """MPC Client
    From python-musicpd:
        _fetch_nothing  …
        _fetch_item     single str
        _fetch_object   single dict
        _fetch_list     list of str
        _fetch_playlist list of str
        _fetch_changes  list of dict
        _fetch_database list of dict
        _fetch_songs    list of dict, especially tracks
        _fetch_plugins,
    TODO: handle exception in command not going through _client_wrapper() (ie.
          find_aa, remove…)
    """
    def __init__(self, host="localhost", port="6600", password=None):
        self._host = host
        self._port = port
        self._password = password
        self._client = MPDClient()
        self._client.iterate = True

    def __getattr__(self, attr):
        command = attr
        wrapper = self._execute
        return lambda *args: wrapper(command, args)

    def _execute(self, command, args):
        self._write_command(command, args)
        return self._client_wrapper()

    def _write_command(self, command, args=[]):
        self._comm = command
        self._args = list()
        for arg in args:
            self._args.append(arg)

    def _client_wrapper(self):
        func = self._client.__getattr__(self._comm)
        try:
            ans = func(*self._args)
        # WARNING: MPDError is an ancestor class of # CommandError
        except CommandError as err:
            raise PlayerCommandError('MPD command error: %s' % err)
        except (MPDError, IOError) as err:
            raise PlayerError(err)
        return self._track_format(ans)

    def _track_format(self, ans):
        # TODO: ain't working for "sticker find" and "sticker list"
        tracks_listing = ["playlistfind", "playlistid", "playlistinfo",
                "playlistsearch", "plchanges", "listplaylistinfo", "find",
                "search", "sticker find",]
        track_obj = ['currentsong']
        unicode_obj = ["idle", "listplaylist", "list", "sticker list",
                "commands", "notcommands", "tagtypes", "urlhandlers",]
        if self._comm in tracks_listing + track_obj:
            #  pylint: disable=w0142
            if isinstance(ans, list):
                return [Track(**track) for track in ans]
            elif isinstance(ans, dict):
                return Track(**ans)
        return ans

    def __skipped_track(self, old_curr):
        if (self.state == 'stop'
            or not hasattr(old_curr, 'id')
            or not hasattr(self.current, 'id')):
            return False
        return (self.current.id != old_curr.id)  # pylint: disable=no-member

    def find_track(self, artist, title=None):
        #return getattr(self, 'find')('artist', artist, 'title', title)
        if title:
            return self.find('artist', artist, 'title', title)
        return self.find('artist', artist)

    def find_album(self, artist, album):
        """
        Special wrapper around album search:
        Album lookup is made through AlbumArtist/Album instead of Artist/Album
        """
        alb_art_search = self.find('albumartist', artist, 'album', album)
        if alb_art_search:
            return alb_art_search
        return self.find('artist', artist, 'album', album)

    def monitor(self):
        curr = self.current
        try:
            self._client.send_idle('database', 'playlist', 'player', 'options')
            select([self._client], [], [], 60)
            ret = self._client.fetch_idle()
            if self.__skipped_track(curr):
                ret.append('skipped')
            return ret
        except (MPDError, IOError) as err:
            raise PlayerError("Couldn't init idle: %s" % err)

    def remove(self, position=0):
        self._client.delete(position)

    @property
    def state(self):
        return str(self._client.status().get('state'))

    @property
    def current(self):
        return self.currentsong()

    @property
    def playlist(self):
        """
        Override deprecated MPD playlist command
        """
        return self.playlistinfo()

    def connect(self):
        self.disconnect()
        try:
            self._client.connect(self._host, self._port)

        # Catch socket errors
        except IOError as err:
            raise PlayerError('Could not connect to "%s:%s": %s' %
                              (self._host, self._port, err.strerror))

        # Catch all other possible errors
        # ConnectionError and ProtocolError are always fatal.  Others may not
        # be, but we don't know how to handle them here, so treat them as if
        # they are instead of ignoring them.
        except MPDError as err:
            raise PlayerError('Could not connect to "%s:%s": %s' %
                              (self._host, self._port, err))

        if self._password:
            try:
                self._client.password(self._password)

            # Catch errors with the password command (e.g., wrong password)
            except CommandError as err:
                raise PlayerError("Could not connect to '%s': "
                                  "password command failed: %s" %
                                  (self._host, err))

            # Catch all other possible errors
            except (MPDError, IOError) as err:
                raise PlayerError("Could not connect to '%s': "
                                  "error with password command: %s" %
                                  (self._host, err))
        # Controls we have sufficient rights for MPD_sima
        needed_cmds = ['status', 'stats', 'add', 'find', \
                       'search', 'currentsong', 'ping']

        available_cmd = self._client.commands()
        for nddcmd in needed_cmds:
            if nddcmd not in available_cmd:
                self.disconnect()
                raise PlayerError('Could connect to "%s", '
                                  'but command "%s" not available' %
                                  (self._host, nddcmd))

    def disconnect(self):
        # Try to tell MPD we're closing the connection first
        try:
            self._client.close()
        # If that fails, don't worry, just ignore it and disconnect
        except (MPDError, IOError):
            pass
        try:
            self._client.disconnect()
        # Disconnecting failed, so use a new client object instead
        # This should never happen.  If it does, something is seriously broken,
        # and the client object shouldn't be trusted to be re-used.
        except (MPDError, IOError):
            self._client = MPDClient()

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
