# -*- coding: utf-8 -*-
# Copyright (c) 2013, 2014 Jack Kaliko <kaliko@azylum.org>
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
"""MPD client for Sima

This client is built above python-musicpd a fork of python-mpd
"""
#  pylint: disable=C0111

# standard library import
from difflib import get_close_matches
from select import select

# third parties components
try:
    from musicpd import (MPDClient, MPDError, CommandError)
except ImportError as err:
    from sys import exit as sexit
    print('ERROR: missing python-musicpd?\n{0}'.format(err))
    sexit(1)

# local import
from .lib.player import Player, blacklist
from .lib.track import Track
from .lib.meta import Album, Artist
from .utils.leven import levenshtein_ratio


class PlayerError(Exception):
    """Fatal error in poller."""

class PlayerCommandError(PlayerError):
    """Command error"""

PlayerUnHandledError = MPDError  # pylint: disable=C0103


class PlayerClient(Player):
    """MPD Client
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
          remove…)
    """
    database = None  # sima database (history, blacklist)

    def __init__(self, host="localhost", port="6600", password=None):
        super().__init__()
        self._comm = self._args = None
        self._mpd = host, port, password
        self._client = MPDClient()
        self._client.iterate = True
        self._cache = None

    def __getattr__(self, attr):
        command = attr
        wrapper = self._execute
        return lambda *args: wrapper(command, args)

    def _execute(self, command, args):
        self._write_command(command, args)
        return self._client_wrapper()

    def _write_command(self, command, args=None):
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
        """
        unicode_obj = ["idle", "listplaylist", "list", "sticker list",
                "commands", "notcommands", "tagtypes", "urlhandlers",]
        """
        # TODO: ain't working for "sticker find" and "sticker list"
        tracks_listing = ["playlistfind", "playlistid", "playlistinfo",
                "playlistsearch", "plchanges", "listplaylistinfo", "find",
                "search", "sticker find",]
        track_obj = ['currentsong']
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
        return self.current.id != old_curr.id  # pylint: disable=no-member

    def _flush_cache(self):
        """
        Both flushes and instantiates _cache
        """
        if isinstance(self._cache, dict):
            self.log.info('Player: Flushing cache!')
        else:
            self.log.info('Player: Initialising cache!')
        self._cache = {
                'artists': None,
                }
        self._cache['artists'] = frozenset(self._client.list('artist'))

    @blacklist(track=True)
    def _find_track(self, artist, title):
        #return getattr(self, 'find')('artist', artist, 'title', title)
        if title:
            return self.find('artist', artist, 'title', title)
        return self.find('artist', artist)

    def find_track(self, artist, title=None):
        tracks = list()
        if isinstance(artist, Artist):
            for name in artist.names:
                tracks.extend(self._find_track(name, title=title))
        else:
            tracks.extend(self._find_track(artist,title=title))
        return tracks

    @blacklist(track=True)
    def fuzzy_find_track(self, artist, title):
        # Retrieve all tracks from artist
        all_tracks = self.find('artist', artist)
        # Get all titles (filter missing titles set to 'None')
        all_artist_titles = frozenset([tr.title for tr in all_tracks
                                       if tr.title is not None])
        match = get_close_matches(title, all_artist_titles, 50, 0.78)
        if not match:
            return []
        for title_ in match:
            leven = levenshtein_ratio(title.lower(), title_.lower())
            if leven == 1:
                pass
            elif leven >= 0.79:  # PARAM
                self.log.debug('title: "%s" should match "%s" (lr=%1.3f)' %
                               (title_, title, leven))
            else:
                self.log.debug('title: "%s" does not match "%s" (lr=%1.3f)' %
                               (title_, title, leven))
                return []
            return self.find('artist', artist, 'title', title_)

    def find_album(self, artist, album):
        """
        Special wrapper around album search:
        Album lookup is made through AlbumArtist/Album instead of Artist/Album
        """
        alb_art_search = self.find('albumartist', artist, 'album', album)
        if alb_art_search:
            return alb_art_search
        return self.find('artist', artist, 'album', album)

    @blacklist(album=True)
    def search_albums(self, artist):
        """
        Fetch all albums for "AlbumArtist"  == artist
        Filter albums returned for "artist" == artist since MPD returns any
               album containing at least a single track for artist
        """
        albums = []
        for name in artist.aliases:
            self.log.debug('Searching album for {}'.format(name))
            kwalbart = {'albumartist':name, 'artist':name}
            for album in self.list('album', 'albumartist', artist):
                if album and album not in albums:
                    albums.append(Album(name=album, **kwalbart))
            for album in self.list('album', 'artist', artist):
                album_trks = [trk for trk in self.find('album', album)]
                if 'Various Artists' in [tr.albumartist for tr in album_trks]:
                    self.log.debug('Discarding {0} ("Various Artists" set)'.format(album))
                    continue
                arts = set([trk.artist for trk in album_trks])
                if len(set(arts)) < 2:  # TODO: better heuristic, use a ratio instead
                    if album not in albums:
                        albums.append(Album(name=album, albumartist=artist))
                elif album and album not in albums:
                    self.log.debug('"{0}" probably not an album of "{1}"'.format(
                                   album, artist) + '({0})'.format('/'.join(arts)))
        return albums

    def monitor(self):
        curr = self.current
        try:
            self.send_idle('database', 'playlist', 'player', 'options')
            select([self._client], [], [], 60)
            ret = self.fetch_idle()
            if self.__skipped_track(curr):
                ret.append('skipped')
            if 'database' in ret:
                self._flush_cache()
            return ret
        except (MPDError, IOError) as err:
            raise PlayerError("Couldn't init idle: %s" % err)

    def clean(self):
        """Clean blocking event (idle) and pending commands
        """
        if 'idle' in self._client._pending:
            self._client.noidle()
        elif self._client._pending:
            self.log.warning('pending commands: {}'.format(self._client._pending))

    def remove(self, position=0):
        self.delete(position)

    def add(self, track):
        """Overriding MPD's add method to accept add signature with a Track
        object"""
        self._client.add(track.file)

    @property
    def artists(self):
        return self._cache.get('artists')

    @property
    def state(self):
        return str(self.status().get('state'))

    @property
    def current(self):
        return self.currentsong()

    @property
    def queue(self):
        plst = self.playlist
        plst.reverse()
        return [trk for trk in plst if int(trk.pos) > int(self.current.pos)]

    @property
    def playlist(self):
        """
        Override deprecated MPD playlist command
        """
        return self.playlistinfo()

    def connect(self):
        host, port, password = self._mpd
        self.disconnect()
        try:
            self._client.connect(host, port)

        # Catch socket errors
        except IOError as err:
            raise PlayerError('Could not connect to "%s:%s": %s' %
                              (host, port, err.strerror))

        # Catch all other possible errors
        # ConnectionError and ProtocolError are always fatal.  Others may not
        # be, but we don't know how to handle them here, so treat them as if
        # they are instead of ignoring them.
        except MPDError as err:
            raise PlayerError('Could not connect to "%s:%s": %s' %
                              (host, port, err))

        if password:
            try:
                self._client.password(password)

            # Catch errors with the password command (e.g., wrong password)
            except CommandError as err:
                raise PlayerError("Could not connect to '%s': "
                                  "password command failed: %s" %
                                  (host, err))

            # Catch all other possible errors
            except (MPDError, IOError) as err:
                raise PlayerError("Could not connect to '%s': "
                                  "error with password command: %s" %
                                  (host, err))
        # Controls we have sufficient rights
        needed_cmds = ['status', 'stats', 'add', 'find', \
                       'search', 'currentsong', 'ping']

        available_cmd = self._client.commands()
        for nddcmd in needed_cmds:
            if nddcmd not in available_cmd:
                self.disconnect()
                raise PlayerError('Could connect to "%s", '
                                  'but command "%s" not available' %
                                  (host, nddcmd))
        self._flush_cache()

    def disconnect(self):
        # Try to tell MPD we're closing the connection first
        try:
            self._client.noidle()
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
