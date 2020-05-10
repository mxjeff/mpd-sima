# -*- coding: utf-8 -*-
# Copyright (c) 2009-2020 kaliko <kaliko@azylum.org>
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

# standard library import
from difflib import get_close_matches
from functools import wraps
from itertools import dropwhile

# external module
from musicpd import MPDClient, MPDError


# local import
from .lib.meta import Artist, Album
from .lib.track import Track
from .lib.simastr import SimaStr
from .utils.leven import levenshtein_ratio


class PlayerError(Exception):
    """Fatal error in poller."""


# Some decorators
def bl_artist(func):
    def wrapper(*args, **kwargs):
        cls = args[0]
        if not cls.database:
            return func(*args, **kwargs)
        result = func(*args, **kwargs)
        if not result:
            return
        names = list()
        for art in result.names:
            if cls.database.get_bl_artist(art, add_not=True):
                cls.log.debug('Blacklisted "%s"', art)
                continue
            names.append(art)
        if not names:
            return
        resp = Artist(name=names.pop(), mbid=result.mbid)
        for name in names:
            resp.add_alias(name)
        return resp
    return wrapper

def tracks_wrapper(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        ret = func(*args, **kwargs)
        if isinstance(ret, dict):
            return Track(**ret)
        elif isinstance(ret, list):
            return [Track(**t) for t in ret]
    return wrapper
# / decorators

def blacklist(artist=False, album=False, track=False):
    #pylint: disable=C0111,W0212
    field = (album, track)
    def decorated(func):
        def wrapper(*args, **kwargs):
            if not args[0].database:
                return func(*args, **kwargs)
            cls = args[0]
            boolgen = (bl for bl in field)
            bl_fun = (cls.database.get_bl_album,
                      cls.database.get_bl_track,)
            #bl_getter = next(fn for fn, bl in zip(bl_fun, boolgen) if bl is True)
            bl_getter = next(dropwhile(lambda _: not next(boolgen), bl_fun))
            #cls.log.debug('using {0} as bl filter'.format(bl_getter.__name__))
            results = list()
            for elem in func(*args, **kwargs):
                if bl_getter(elem, add_not=True):
                    #cls.log.debug('Blacklisted "{0}"'.format(elem))
                    continue
                if track and cls.database.get_bl_album(elem, add_not=True):
                    # filter album as well in track mode
                    # (artist have already been)
                    cls.log.debug('Blacklisted alb. "{0.album}"'.format(elem))
                    continue
                results.append(elem)
            return results
        return wrapper
    return decorated


class MPD(MPDClient):
    """
    Player instance inheriting from MPDClient (python-musicpd).

    Some methods are overridden to format objects as sima.lib.Track for
    instance, other are calling parent class directly through super().
    cf. MPD.__getattr__

    .. note::

        * find methods are looking for exact match of the object provided attributes in MPD music library
        * search methods are looking for exact match + fuzzy match.
    """
    needed_cmds = ['status', 'stats', 'add', 'find',
                   'search', 'currentsong', 'ping']
    database = None

    def __init__(self, daemon):
        super().__init__()
        self.use_mbid = True
        self.daemon = daemon
        self.log = daemon.log
        self.config = self.daemon.config['MPD']
        self._cache = None

    # ######### Overriding MPDClient ###########
    def __getattr__(self, cmd):
        """Wrapper around MPDClient calls for abstract overriding"""
        track_wrapped = {
                         'currentsong',
                         'find',
                         'playlistinfo',
                         }
        if cmd in track_wrapped:
            return tracks_wrapper(super().__getattr__(cmd))
        return super().__getattr__(cmd)

    def disconnect(self):
        """Overriding explicitly MPDClient.disconnect()"""
        if self._sock:
            super().disconnect()

    def connect(self):
        """Overriding explicitly MPDClient.connect()"""
        # host, port, password
        host = self.config.get('host')
        port = self.config.get('port')
        password = self.config.get('password', fallback=None)
        self.disconnect()
        try:
            super().connect(host, port)
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
                self.password(password)
            except (MPDError, IOError) as err:
                raise PlayerError("Could not connect to '%s': %s", (host, err))
        # Controls we have sufficient rights
        available_cmd = self.commands()
        for cmd in MPD.needed_cmds:
            if cmd not in available_cmd:
                self.disconnect()
                raise PlayerError('Could connect to "%s", '
                                  'but command "%s" not available' %
                                  (host, cmd))
        # Controls use of MusicBrainzIdentifier
        # TODO: Use config instead of Artist object attibute?
        if self.use_mbid:
            tt = self.tagtypes()
            if 'MUSICBRAINZ_ARTISTID' not in tt:
                self.log.warning('Use of MusicBrainzIdentifier is set but MPD is '
                                 'not providing related metadata')
                self.log.info(tt)
                self.log.warning('Disabling MusicBrainzIdentifier')
                self.use_mbid = False
            else:
                self.log.debug('Available metadata: %s', tt)  # pylint: disable=no-member
        else:
            self.log.warning('Use of MusicBrainzIdentifier disabled!')
            self.log.info('Consider using MusicBrainzIdentifier for your music library')
        self._reset_cache()
    # ######### / Overriding MPDClient #########

    def _reset_cache(self):
        """
        Both flushes and instantiates _cache
        """
        if isinstance(self._cache, dict):
            self.log.info('Player: Flushing cache!')
        else:
            self.log.info('Player: Initialising cache!')
        self._cache = {'artists': frozenset(),
                       'nombid_artists': frozenset()}
        self._cache['artists'] = frozenset(filter(None, self.list('artist')))
        if Artist.use_mbid:
            self._cache['nombid_artists'] = frozenset(filter(None, self.list('artist', 'musicbrainz_artistid', '')))

    def _skipped_track(self, previous):
        if (self.state == 'stop'
                or not hasattr(previous, 'id')
                or not hasattr(self.current, 'id')):
            return False
        return self.current.id != previous.id  # pylint: disable=no-member

    def monitor(self):
        """OLD socket Idler
        Monitor player for change
        Returns a list a events among:

            * database  player media library has changed
            * playlist  playlist modified
            * options   player options changed: repeat mode, etc…
            * player    player state changed: paused, stopped, skip track…
            * skipped   current track skipped
        """
        curr = self.current
        try:
            ret = self.idle('database', 'playlist', 'player', 'options')
        except (MPDError, IOError) as err:
            raise PlayerError("Couldn't init idle: %s" % err)
        if self._skipped_track(curr):
            ret.append('skipped')
        if 'database' in ret:
            self._flush_cache()
        return ret

    def clean(self):
        """Clean blocking event (idle) and pending commands
        """
        if 'idle' in self._pending:
            self.noidle()
        elif self._pending:
            self.log.warning('pending commands: %s', self._pending)

    def add(self, payload):
        """Overriding MPD's add method to accept Track objects"""
        if isinstance(payload, Track):
            super().__getattr__('add')(payload.file)
        elif isinstance(payload, list):
            for tr in payload:  # TODO: use send command here
                self.add(tr)
        else:
            self.log.error('Cannot add %s', payload)

    # ######### Properties #####################
    @property
    def current(self):
        return self.currentsong()

    @property
    def playlist(self):
        """
        Override deprecated MPD playlist command
        """
        return self.playlistinfo()

    @property
    def playmode(self):
        plm = {'repeat': None, 'single': None,
               'random': None, 'consume': None, }
        for key, val in self.status().items():
            if key in plm.keys():
                plm.update({key: bool(int(val))})
        return plm

    @property
    def queue(self):
        plst = self.playlist
        curr_position = int(self.current.pos)
        plst.reverse()
        return [trk for trk in plst if int(trk.pos) > curr_position]

    @property
    def state(self):
        """Returns (play|stop|pause)"""
        return str(self.status().get('state'))
    # ######### / Properties ###################

# #### find_tracks ####
    def find_album(self, artist, album_name):
        self.log.warning('update call to find_album→find_tracks(<Album object>)')
        return self.find_tracks(Album(name=album_name, artist=artist))

    def find_track(self, *args, **kwargs):
        self.log.warning('update call to find_track→find_tracks')
        return self.find_tracks(*args, **kwargs)

    def find_tracks(self, what):
        """Find tracks for a specific artist or album
            >>> player.find_tracks(Artist('Nirvana'))
            >>> player.find_tracks(Album('In Utero', artist=(Artist('Nirvana'))

        :param Artist,Album what: Artist or Album to fetch track from

        Returns a list of :py:obj:Track objects
        """
        if isinstance(what, Artist):
            return self._find_art(what)
        elif isinstance(what, Album):
            return self._find_alb(what)
        elif isinstance(what, str):
            return self.find_tracks(Artist(name=what))

    def _find_art(self, artist):
        tracks = set()
        if self.use_mbid and artist.mbid:
            tracks |= set(self.find('musicbrainz_artistid', artist.mbid))
        for name in artist.names:
            tracks |= set(self.find('artist', name))
        return list(tracks)

    def _find_alb(self, album):
        if album.mbid and self.use_mbid:
            filt = f'(MUSICBRAINZ_ALBUMID == {album.mbid})'
            return self.find(filt)
        # Now look for album with no MusicBrainzIdentifier
        if album.artist.mbid and self.use_mbid:  # Use album artist MBID if possible
            filt = f"((MUSICBRAINZ_ALBUMARTISTID == '{album.artist.mbid}') AND (album == '{album!s}'))"
            return self.find(filt)
        tracks = []
        # Falls back to albumartist/album name
        filt = f"((albumartist == '{album.artist!s}') AND (album == '{album!s}'))"
        tracks = self.find(filt)
        # Falls back to artist/album name
        if not tracks:
            filt = f"((artist == '{album.artist!s}') AND (album == '{album!s}'))"
            tracks = self.find(filt)
        return tracks
# #### / find_tracks ##

# #### Search Methods #####
    @bl_artist
    def search_artist(self, artist):
        """
        Search artists based on a fuzzy search in the media library
            >>> art = Artist(name='the beatles', mbid=<UUID4>) # mbid optional
            >>> bea = player.search_artist(art)c
            >>> print(bea.names)
            >>> ['The Beatles', 'Beatles', 'the beatles']

        Returns an Artist object
        TODO: Re-use find method here!!!
        """
        found = False
        if artist.mbid:
            # look for exact search w/ musicbrainz_artistid
            exact_m = self.list('artist', 'musicbrainz_artistid', artist.mbid)
            if exact_m:
                _ = [artist.add_alias(name) for name in exact_m]
                found = True
        # then complete with fuzzy search on artist with no musicbrainz_artistid
        if artist.mbid:
            # we already performed a lookup on artists with mbid set
            # search through remaining artists
            artists = self._cache.get('nombid_artists')
        else:
            artists = self._cache.get('artists')
        match = get_close_matches(artist.name, artists, 50, 0.73)
        if not match and not found:
            return None
        if len(match) > 1:
            self.log.debug('found close match for "%s": %s', artist, '/'.join(match))
        # Does not perform fuzzy matching on short and single word strings
        # Only lowercased comparison
        if ' ' not in artist.name and len(artist.name) < 8:
            for close_art in match:
                # Regular lowered string comparison
                if artist.name.lower() == close_art.lower():
                    artist.add_alias(close_art)
                    return artist
                else:
                    return None
        for fuzz_art in match:
            # Regular lowered string comparison
            if artist.name.lower() == fuzz_art.lower():
                found = True
                artist.add_alias(fuzz_art)
                if artist.name != fuzz_art:
                    self.log.debug('"%s" matches "%s".', fuzz_art, artist)
                continue
            # SimaStr string __eq__ (not regular string comparison here)
            if SimaStr(artist.name) == fuzz_art:
                found = True
                artist.add_alias(fuzz_art)
                self.log.info('"%s" quite probably matches "%s" (SimaStr)',
                              fuzz_art, artist)
        if found:
            if artist.aliases:
                self.log.debug('Found: %s', '/'.join(list(artist.names)[:4]))
            return artist

    @blacklist(track=True)
    def search_track(self, artist, title):
        """Fuzzy search of title by an artist
        """
        # Retrieve all tracks from artist
        all_tracks = self.find_tracks(artist)
        # Get all titles (filter missing titles set to 'None')
        all_artist_titles = frozenset([tr.title for tr in all_tracks
                                       if tr.title is not None])
        match = get_close_matches(title, all_artist_titles, 50, 0.78)
        if not match:
            return []
        for mtitle in match:
            leven = levenshtein_ratio(title.lower(), mtitle.lower())
            if leven == 1:
                pass
            elif leven >= 0.79:  # PARAM
                self.log.debug('title: "%s" should match "%s" (lr=%1.3f)',
                               mtitle, title, leven)
            else:
                self.log.debug('title: "%s" does not match "%s" (lr=%1.3f)',
                               mtitle, title, leven)
                return []
            return self.find('artist', artist, 'title', mtitle)

    @blacklist(album=True)
    def search_albums(self, artist):
        """
        Fetch all albums for "AlbumArtist"  == artist
        Then look for albums for "artist" == artist and try to filters
        multi-artists albums

        NB: Running "client.list('album', 'artist', name)" MPD returns any album
            containing at least a track with "artist" == name
        TODO: Use MusicBrainzID here cf. #30 @gitlab
        """
        albums = []
        for name in artist.names:
            if artist.aliases:
                self.log.debug('Searching album for aliase: "%s"', name)
            kwalbart = {'albumartist': name, 'artist': name}
            for album in self.list('album', 'albumartist', name):
                if album and album not in albums:
                    albums.append(Album(name=album, **kwalbart))
            for album in self.list('album', 'artist', name):
                album_trks = [trk for trk in self.find('album', album)]
                if 'Various Artists' in [tr.albumartist for tr in album_trks]:
                    self.log.debug('Discarding %s ("Various Artists" set)', album)
                    continue
                arts = {trk.artist for trk in album_trks}
                # Avoid selecting album where artist is credited for a single
                # track of the album
                if len(set(arts)) < 2:  # TODO: better heuristic, use a ratio instead
                    if album not in albums:
                        albums.append(Album(name=album, **kwalbart))
                elif album and album not in albums:
                    self.log.debug('"{0}" probably not an album of "{1}"'.format(
                        album, artist) + '({0})'.format('/'.join(arts)))
        return albums
# #### / Search Methods ###

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
