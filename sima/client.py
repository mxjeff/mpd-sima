# -* coding: utf-8 -*-
"""MPD client for Sima

This client is built above python-musicpd a fork of python-mpd
"""
#  pylint: disable=C0111

# standard library import
from difflib import get_close_matches
from itertools import dropwhile
from select import select

# third parties components
try:
    from musicpd import (MPDClient, MPDError, CommandError)
except ImportError as err:
    from sys import exit as sexit
    print('ERROR: missing python-musicpd?\n{0}'.format(err))
    sexit(1)

# local import
from .lib.player import Player
from .lib.track import Track
from .lib.meta import Album
from .lib.simastr import SimaStr


class PlayerError(Exception):
    """Fatal error in poller."""

class PlayerCommandError(PlayerError):
    """Command error"""

PlayerUnHandledError = MPDError  # pylint: disable=C0103


def blacklist(artist=False, album=False, track=False):
    #pylint: disable=C0111,W0212
    field = (artist, album, track)
    def decorated(func):
        def wrapper(*args, **kwargs):
            cls = args[0]
            boolgen = (bl for bl in field)
            bl_fun = (cls.database.get_bl_artist,
                      cls.database.get_bl_album,
                      cls.database.get_bl_track,)
            #bl_getter = next(fn for fn, bl in zip(bl_fun, boolgen) if bl is True)
            bl_getter = next(dropwhile(lambda _: not next(boolgen), bl_fun))
            #cls.log.debug('using {0} as bl filter'.format(bl_getter.__name__))
            results = func(*args, **kwargs)
            for elem in results:
                if bl_getter(elem, add_not=True):
                    cls.log.info('Blacklisted: {0}'.format(elem))
                    results.remove(elem)
            return results
        return wrapper
    return decorated

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
    database = None  # sima database (history, blaclist)

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
        return (self.current.id != old_curr.id)  # pylint: disable=no-member

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

    def find_track(self, artist, title=None):
        #return getattr(self, 'find')('artist', artist, 'title', title)
        if title:
            return self.find('artist', artist, 'title', title)
        return self.find('artist', artist)

    @blacklist(artist=True)
    def fuzzy_find_artist(self, art):
        """
        Controls presence of artist in music library.
        Crosschecking artist names with SimaStr objects / difflib / levenshtein

        TODO: proceed crosschecking even when an artist matched !!!
              Not because we found "The Doors" as "The Doors" that there is no
              remaining entries as "Doors" :/
              not straight forward, need probably heavy refactoring.
        """
        matching_artists = list()
        artist = SimaStr(art)

        # Check against the actual string in artist list
        if artist.orig in self.artists:
            self.log.debug('found exact match for "%s"' % artist)
            return [artist]
        # Then proceed with fuzzy matching if got nothing
        match = get_close_matches(artist.orig, self.artists, 50, 0.73)
        if not match:
            return []
        self.log.debug('found close match for "%s": %s' %
                       (artist, '/'.join(match)))
        # Does not perform fuzzy matching on short and single word strings
        # Only lowercased comparison
        if ' ' not in artist.orig and len(artist) < 8:
            for fuzz_art in match:
                # Regular string comparison SimaStr().lower is regular string
                if artist.lower() == fuzz_art.lower():
                    matching_artists.append(fuzz_art)
                    self.log.debug('"%s" matches "%s".' % (fuzz_art, artist))
            return matching_artists
        for fuzz_art in match:
            # Regular string comparison SimaStr().lower is regular string
            if artist.lower() == fuzz_art.lower():
                matching_artists.append(fuzz_art)
                self.log.debug('"%s" matches "%s".' % (fuzz_art, artist))
                return matching_artists
            # SimaStr string __eq__ (not regular string comparison here)
            if artist == fuzz_art:
                matching_artists.append(fuzz_art)
                self.log.info('"%s" quite probably matches "%s" (SimaStr)' %
                              (fuzz_art, artist))
            else:
                self.log.debug('FZZZ: "%s" does not match "%s"' %
                               (fuzz_art, artist))
        return matching_artists

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
    def find_albums(self, artist):
        """
        Fetch all albums for "AlbumArtist"  == artist
        Filter albums returned for "artist" == artist since MPD returns any
               album containing at least a single track for artist
        """
        albums = []
        kwalbart = {'albumartist':artist, 'artist':artist}
        for album in self.list('album', 'albumartist', artist):
            if album not in albums:
                albums.append(Album(name=album, **kwalbart))
        for album in self.list('album', 'artist', artist):
            arts = set([trk.artist for trk in self.find('album', album)])
            if len(arts) < 2:  # TODO: better heuristic, use a ratio instead
                if album not in albums:
                    albums.append(Album(name=album, albumartist=artist))
            elif (album and album not in albums):
                self.log.debug('"{0}" probably not an album of "{1}"'.format(
                               album, artist) + '({0})'.format('/'.join(arts)))
        return albums

    def monitor(self):
        curr = self.current
        try:
            self._client.send_idle('database', 'playlist', 'player', 'options')
            select([self._client], [], [], 60)
            ret = self._client.fetch_idle()
            if self.__skipped_track(curr):
                ret.append('skipped')
            if 'database' in ret:
                self._flush_cache()
            return ret
        except (MPDError, IOError) as err:
            raise PlayerError("Couldn't init idle: %s" % err)

    def remove(self, position=0):
        self._client.delete(position)

    def add(self, track):
        """Overriding MPD's add method to accept add signature with a Track
        object"""
        self._client.add(track.file)

    @property
    def artists(self):
        return self._cache.get('artists')

    @property
    def state(self):
        return str(self._client.status().get('state'))

    @property
    def current(self):
        return self.currentsong()

    @property
    def queue(self):
        plst = self.playlist
        plst.reverse()
        return [ trk for trk in plst if int(trk.pos) > int(self.current.pos)]

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
