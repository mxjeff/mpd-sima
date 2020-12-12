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
from .lib.meta import Meta, Artist, Album
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
            return None
        names = list()
        for art in result.names:
            if cls.database.get_bl_artist(art, add_not=True):
                cls.log.debug('Blacklisted "%s"', art)
                continue
            names.append(art)
        if not names:
            return None
        resp = Artist(name=names.pop(), mbid=result.mbid)
        for name in names:
            resp.add_alias(name)
        return resp
    return wrapper


def tracks_wrapper(func):
    """Convert plain track mapping as returned by MPDClient into :py:obj:Track
    objects. This decorator accepts single track or list of tracks as input.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        ret = func(*args, **kwargs)
        if isinstance(ret, dict):
            return Track(**ret)
        return [Track(**t) for t in ret]
    return wrapper
# / decorators


def blacklist(artist=False, album=False, track=False):
    # pylint: disable=C0111,W0212
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
                    cls.log.debug('Blacklisted alb. "%s"', elem)
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

        * find methods are looking for exact match of the object provided
          attributes in MPD music library
        * search methods are looking for exact match + fuzzy match.
    """
    needed_cmds = ['status', 'stats', 'add', 'find',
                   'search', 'currentsong', 'ping']
    needed_tags = {'Artist', 'Album', 'AlbumArtist', 'Title', 'Track'}
    needed_mbid_tags = {'MUSICBRAINZ_ARTISTID', 'MUSICBRAINZ_ALBUMID',
                        'MUSICBRAINZ_ALBUMARTISTID', 'MUSICBRAINZ_TRACKID'}
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
        track_wrapped = {'currentsong', 'find', 'playlistinfo', }
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
                raise PlayerError("Could not connect to '%s': %s" % (host, err))
        # Controls we have sufficient rights
        available_cmd = self.commands()
        for cmd in MPD.needed_cmds:
            if cmd not in available_cmd:
                self.disconnect()
                raise PlayerError('Could connect to "%s", '
                                  'but command "%s" not available' %
                                  (host, cmd))
        self.tagtypes('clear')
        for tag in MPD.needed_tags:
            self.tagtypes('enable', tag)
        tt = set(map(str.lower, self.tagtypes()))
        needed_tags = set(map(str.lower, MPD.needed_tags))
        if len(needed_tags & tt) != len(MPD.needed_tags):
            self.log.warning('MPD exposes: %s', tt)
            self.log.warning('Tags needed: %s', needed_tags)
            raise PlayerError('Missing mandatory metadata!')
        for tag in MPD.needed_mbid_tags:
            self.tagtypes('enable', tag)
        # Controls use of MusicBrainzIdentifier
        if self.daemon.config.get('sima', 'musicbrainzid'):
            tt = set(self.tagtypes())
            if len(MPD.needed_mbid_tags & tt) != len(MPD.needed_mbid_tags):
                self.log.warning('Use of MusicBrainzIdentifier is set but MPD '
                                 'is not providing related metadata')
                self.log.info(tt)
                self.log.warning('Disabling MusicBrainzIdentifier')
                self.use_mbid = Meta.use_mbid = False
            else:
                self.log.debug('Available metadata: %s', tt)
                self.use_mbid = Meta.use_mbid = True
        else:
            self.log.warning('Use of MusicBrainzIdentifier disabled!')
            self.log.info('Consider using MusicBrainzIdentifier for your music library')
            self.use_mbid = Meta.use_mbid = False
        self._reset_cache()
    # ######### / Overriding MPDClient #########

    def _reset_cache(self):
        """
        Both flushes and instantiates _cache

        * artists: all artists
        * nombid_artists: artists with no mbid (set only when self.use_mbid is True)
        * artist_tracks: caching last artist tracks, used in search_track
        """
        if isinstance(self._cache, dict):
            self.log.info('Player: Flushing cache!')
        else:
            self.log.info('Player: Initialising cache!')
        self._cache = {'artists': frozenset(),
                       'nombid_artists': frozenset(),
                       'artist_tracks': {}}
        self._cache['artists'] = frozenset(filter(None, self.list('artist')))
        if self.use_mbid:
            artists = self.list('artist', "(MUSICBRAINZ_ARTISTID == '')")
            self._cache['nombid_artists'] = frozenset(filter(None, artists))

    def _skipped_track(self, previous):
        if (self.state == 'stop'
                or not hasattr(previous, 'id')
                or not hasattr(self.current, 'id')):
            return False
        return self.current.id != previous.id  # pylint: disable=no-member

    def monitor(self):
        """Monitor player for change
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
            self._reset_cache()
        return ret

    def clean(self):
        """Clean blocking event (idle) and pending commands
        """
        if 'idle' in self._pending:
            self.noidle()
        elif self._pending:
            self.log.warning('pending commands: %s', self._pending)

    def add(self, payload):
        """Overriding MPD's add method to accept Track objects

        :param Track,list payload: Either a single :py:obj:`Track` or a list of it
        """
        if isinstance(payload, Track):
            super().__getattr__('add')(payload.file)
        elif isinstance(payload, list):
            self.command_list_ok_begin()
            map(self.add, payload)
            self.command_list_end()
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
    def find_tracks(self, what):
        """Find tracks for a specific artist or album
            >>> player.find_tracks(Artist('Nirvana'))
            >>> player.find_tracks(Album('In Utero', artist=(Artist('Nirvana'))

        :param Artist,Album what: Artist or Album to fetch track from

        Returns a list of :py:obj:Track objects
        """
        if isinstance(what, Artist):
            return self._find_art(what)
        if isinstance(what, Album):
            return self._find_alb(what)
        if isinstance(what, str):
            return self.find_tracks(Artist(name=what))
        raise PlayerError('Bad input argument')

    def _find_art(self, artist):
        tracks = set()
        if artist.mbid:
            tracks |= set(self.find('musicbrainz_artistid', artist.mbid))
        for name in artist.names_sz:
            tracks |= set(self.find('artist', name))
        return list(tracks)

    def _find_alb(self, album):
        if not hasattr(album, 'artist'):
            raise PlayerError('Album object have no artist attribute')
        albums = []
        if self.use_mbid and album.mbid:
            filt = f"(MUSICBRAINZ_ALBUMID == '{album.mbid}')"
            albums = self.find(filt)
        # Now look for album with no MusicBrainzIdentifier
        if not albums and album.artist.mbid and self.use_mbid:  # Use album artist MBID if possible
            filt = f"((MUSICBRAINZ_ALBUMARTISTID == '{album.artist.mbid}') AND (album == '{album.name_sz}'))"
            albums = self.find(filt)
        if not albums:  # Falls back to (album)?artist/album name
            for artist in album.artist.names_sz:
                filt = f"((albumartist == '{artist}') AND (album == '{album.name_sz}'))"
                albums.extend(self.find(filt))
        return albums
# #### / find_tracks ##

# #### Search Methods #####
    @bl_artist
    def search_artist(self, artist):
        """
        Search artists based on a fuzzy search in the media library
            >>> art = Artist(name='the beatles', mbid=<UUID4>) # mbid optional
            >>> bea = player.search_artist(art)
            >>> print(bea.names)
            >>> ['The Beatles', 'Beatles', 'the beatles']

        :param Artist artist: Artist to look for in MPD music library

        Returns an Artist object
        """
        found = False
        if self.use_mbid and artist.mbid:
            # look for exact search w/ musicbrainz_artistid
            library = self.list('artist', f"(MUSICBRAINZ_ARTISTID == '{artist.mbid}')")
            if library:
                found = True
                self.log.trace('Found mbid "%r" in library', artist)
                # library could fetch several artist name for a single MUSICBRAINZ_ARTISTID
                if len(library) > 1:
                    self.log.debug('I got "%s" searching for %r', library, artist)
                elif len(library) == 1 and library[0] != artist.name:
                    self.log.info('Update artist name %s->%s', artist, library[0])
                    artist = Artist(name=library[0], mbid=artist.mbid)
            # Fetches remaining artists for potential match
            artists = self._cache['nombid_artists']
        else:  # not using MusicBrainzIDs
            artists = self._cache['artists']
        match = get_close_matches(artist.name, artists, 50, 0.73)
        if not match and not found:
            return None
        if len(match) > 1:
            self.log.debug('found close match for "%s": %s',
                           artist, '/'.join(match))
        # First lowercased comparison
        for close_art in match:
            # Regular lowered string comparison
            if artist.name.lower() == close_art.lower():
                artist.add_alias(close_art)
                found = True
                if artist.name != close_art:
                    self.log.debug('"%s" matches "%s".', close_art, artist)
        # Does not perform fuzzy matching on short and single word strings
        # Only lowercased comparison
        if ' ' not in artist.name and len(artist.name) < 8:
            self.log.trace('no fuzzy matching for %r', artist)
            if found:
                return artist
            return None
        # Now perform fuzzy search
        for fuzz in match:
            if fuzz in artist.names:  # Already found in lower cased comparison
                continue
            # SimaStr string __eq__ (not regular string comparison here)
            if SimaStr(artist.name) == fuzz:
                found = True
                artist.add_alias(fuzz)
                self.log.debug('"%s" quite probably matches "%s" (SimaStr)',
                               fuzz, artist)
        if found:
            if artist.aliases:
                self.log.info('Found aliases: %s', '/'.join(artist.names))
            return artist
        return None

    @blacklist(track=True)
    def search_track(self, artist, title):
        """Fuzzy search of title by an artist
        """
        cache = self._cache.get('artist_tracks').get(artist)
        # Retrieve all tracks from artist
        all_tracks = cache or self.find_tracks(artist)
        if not cache:
            self._cache['artist_tracks'] = {}  # clean up
            self._cache.get('artist_tracks')[artist] = all_tracks
        # Get all titles (filter missing titles set to 'None')
        all_artist_titles = frozenset([tr.title for tr in all_tracks
                                       if tr.title is not None])
        match = get_close_matches(title, all_artist_titles, 50, 0.78)
        tracks = []
        if not match:
            return []
        for mtitle in match:
            leven = levenshtein_ratio(title, mtitle)
            if leven == 1:
                tracks.extend([t for t in all_tracks if t.title == mtitle])
            elif leven >= 0.77:
                self.log.debug('title: "%s" should match "%s" (lr=%1.3f)',
                               mtitle, title, leven)
                tracks.extend([t for t in all_tracks if t.title == mtitle])
            else:
                self.log.debug('title: "%s" does not match "%s" (lr=%1.3f)',
                               mtitle, title, leven)
        return tracks

    @blacklist(album=True)
    def search_albums(self, artist):
        """Find potential albums for "artist"

        * Fetch all albums for "AlbumArtist" == artist
          → falls back to "Artist" == artist when no "AlbumArtist" tag is set
        * Tries to filter some mutli-artists album
          For instance an album by Artist_A may have a track by Artist_B. Then
          looking for albums for Artist_B returns wrongly this album.
        """
        # First, look for all potential albums
        self.log.debug('Searching album for "%s"', artist)
        if artist.aliases:
            self.log.debug('Searching album for %s aliases: "%s"',
                           artist, artist.aliases)
        for name_sz in artist.names_sz:
            raw_albums = self.list('album', f"( albumartist == '{name_sz}')")
            albums = [Album(a, albumartist=artist.name, artist=artist) for a in raw_albums if a]
        candidates = []
        for album in albums:
            album_trks = self.find_tracks(album)
            album_artists = {tr.albumartist for tr in album_trks if tr.albumartist}
            if album.artist.names & album_artists:
                candidates.append(album)
                continue
            if 'Various Artists' in album_artists:
                self.log.debug('Discarding %s ("Various Artists" set)', album)
                continue
            if album_artists and album.artist.name not in album_artists:
                self.log.debug('Discarding "%s", "%s" not set as albumartist', album, album.artist)
                continue
            # Attempt to detect false positive
            # Avoid selecting albums where artist is credited for a single
            # track of the album
            album_trks = self.find(f"(album == '{album.name_sz}')")
            arts = [trk.artist for trk in album_trks]  # Artists in the album
            # count artist occurences
            ratio = arts.count(album.artist.name)/len(arts)
            if ratio >= 0.8:
                candidates.append(album)
            else:
                self.log.debug('"%s" probably not an album of "%s" (ratio=%.2f)',
                               album, artist, ratio)
            continue
        return candidates
# #### / Search Methods ###

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
