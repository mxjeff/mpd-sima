# -*- coding: utf-8 -*-
# Copyright (c) 2009-2021 kaliko <kaliko@azylum.org>
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
from logging import getLogger
from select import select

# external module
from musicpd import MPDClient, MPDError as PlayerError


# local import
from .lib.meta import Meta, Artist, Album
from .lib.track import Track
from .lib.simastr import SimaStr
from .utils.leven import levenshtein_ratio


# Some decorators
def bl_artist(func):
    def wrapper(*args, **kwargs):
        cls = args[0]
        if not cls.database:
            return func(*args, **kwargs)
        result = func(*args, **kwargs)
        if not result:
            return None
        for art in result.names:
            artist = Artist(name=art, mbid=result.mbid)
            if cls.database.get_bl_artist(artist, add=False):
                cls.log.debug('Artist in blocklist: %s', artist)
                return None
        return result
    return wrapper


def set_artist_mbid(func):
    def wrapper(*args, **kwargs):
        cls = args[0]
        result = func(*args, **kwargs)
        if Meta.use_mbid:
            if result and not result.mbid:
                mbid = cls._find_musicbrainz_artistid(result)
                artist = Artist(name=result.name, mbid=mbid)
                artist.add_alias(result)
                return artist
        return result
    return wrapper


def tracks_wrapper(func):
    """Convert plain track mapping as returned by MPDClient into :py:obj:`sima.lib.track.Track`
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


class MPD(MPDClient):
    """
    Player instance inheriting from MPDClient (python-musicpd).

    Some methods are overridden to format objects as :py:obj:`sima.lib.track.Track` for
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
    MPD_supported_tags = {'Artist', 'ArtistSort', 'Album', 'AlbumSort', 'AlbumArtist',
                          'AlbumArtistSort', 'Title', 'Track', 'Name', 'Genre',
                          'Date', 'OriginalDate', 'Composer', 'Performer',
                          'Conductor', 'Work', 'Grouping', 'Disc', 'Label',
                          'MUSICBRAINZ_ARTISTID', 'MUSICBRAINZ_ALBUMID',
                          'MUSICBRAINZ_ALBUMARTISTID', 'MUSICBRAINZ_TRACKID',
                          'MUSICBRAINZ_RELEASETRACKID', 'MUSICBRAINZ_WORKID'}
    database = None

    def __init__(self, config):
        super().__init__()
        self.socket_timeout = 10
        self.use_mbid = True
        self.log = getLogger('sima')
        self.config = config
        self._cache = None

    # ######### Overriding MPDClient ###########
    def __getattr__(self, cmd):
        """Wrapper around MPDClient calls for abstract overriding"""
        track_wrapped = {'currentsong', 'find', 'playlistinfo', }
        try:
            if cmd in track_wrapped:
                return tracks_wrapper(super().__getattr__(cmd))
            return super().__getattr__(cmd)
        except OSError as err:  # socket errors
            raise PlayerError(err) from err

    def disconnect(self):
        """Overriding explicitly MPDClient.disconnect()"""
        if self._sock:
            super().disconnect()

    def connect(self):
        """Overriding explicitly MPDClient.connect()"""
        mpd_config = self.config['MPD']
        # host, port, password
        host = mpd_config.get('host')
        port = mpd_config.get('port')
        password = mpd_config.get('password', fallback=None)
        self.disconnect()
        try:
            super().connect(host, port)
        # Catch socket errors
        except OSError as err:
            raise PlayerError(f'Could not connect to "{host}:{port}": {err.strerror}'
                             ) from err
        # Catch all other possible errors
        # ConnectionError and ProtocolError are always fatal.  Others may not
        # be, but we don't know how to handle them here, so treat them as if
        # they are instead of ignoring them.
        except PlayerError as err:
            raise PlayerError(f'Could not connect to "{host}:{port}": {err}') from err
        if password:
            try:
                self.password(password)
            except OSError as err:
                raise PlayerError(f"Could not connect to '{host}': {err}") from err
        # Controls we have sufficient rights
        available_cmd = self.commands()
        for cmd in MPD.needed_cmds:
            if cmd not in available_cmd:
                self.disconnect()
                raise PlayerError(f'Could connect to "{host}", but command "{cmd}" not available')
        self.tagtypes_clear()
        for tag in MPD.needed_tags:
            self.tagtypes_enable(tag)
        ltt = set(map(str.lower, self.tagtypes()))
        needed_tags = set(map(str.lower, MPD.needed_tags))
        if len(needed_tags & ltt) != len(MPD.needed_tags):
            self.log.warning('MPD exposes: %s', ltt)
            self.log.warning('Tags needed: %s', needed_tags)
            raise PlayerError('Missing mandatory metadata!')
        for tag in MPD.needed_mbid_tags:
            self.tagtypes_enable(tag)
        # Controls use of MusicBrainzIdentifier
        if self.config.getboolean('sima', 'musicbrainzid'):
            ltt = set(self.tagtypes())
            if len(MPD.needed_mbid_tags & ltt) != len(MPD.needed_mbid_tags):
                self.log.warning('Use of MusicBrainzIdentifier is set but MPD '
                                 'is not providing related metadata')
                self.log.info(ltt)
                self.log.warning('Disabling MusicBrainzIdentifier')
                self.use_mbid = Meta.use_mbid = False
            else:
                self.log.debug('Available metadata: %s', ltt)
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
        select_timeout = 5
        try:  # noidle cmd does not go through __getattr__, need to catch OSError then
            while True:
                self.send_idle('database', 'playlist', 'player', 'options')
                _read, _, _ = select([self], [], [], select_timeout)
                if _read:  # tries to read response
                    ret = self.fetch_idle()
                    if self._skipped_track(curr):
                        ret.append('skipped')
                    if 'database' in ret:
                        self._reset_cache()
                    return ret
                #  Nothing to read, canceling idle
                self.noidle()
        except OSError as err:
            raise PlayerError(err) from err

    def clean(self):
        """Clean blocking event (idle) and pending commands
        """
        if 'idle' in self._pending:
            self.noidle()
        elif self._pending:
            self.log.warning('pending commands: %s', self._pending)

    def add(self, payload):
        """Overriding MPD's add method to accept Track objects

        :param Track,list payload: Either a single track or a list of it
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
            if key in plm:
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
            >>> player.find_tracks(Album('In Utero', artist=Artist('Nirvana'))

        :param Artist,Album what: Artist or Album to fetch track from
        :return: A list of track objects
        :rtype: list(Track)
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
        # artist blocklist
        if self.database.get_bl_artist(artist, add=False):
            self.log.info('Artist in blocklist: %s', artist)
            return []
        if artist.mbid:
            tracks |= set(self.find('musicbrainz_artistid', artist.mbid))
        for name in artist.names:
            tracks |= set(self.find('artist', name))
        # album blocklist
        albums = {Album(trk.Album.name, mbid=trk.musicbrainz_albumid)
                  for trk in tracks}
        bl_albums = {Album(a.get('album'), mbid=a.get('musicbrainz_album'))
                     for a in self.database.view_bl() if a.get('album')}
        if albums & bl_albums:
            self.log.info('Albums in blocklist for %s: %s', artist, albums & bl_albums)
            tracks = {trk for trk in tracks if trk.Album not in bl_albums}
        # track blocklist
        bl_tracks = {Track(title=t.get('title'), file=t.get('file'))
                     for t in self.database.view_bl() if t.get('title')}
        if tracks & bl_tracks:
            self.log.info('Tracks in blocklist for %s: %s',
                          artist, tracks & bl_tracks)
            tracks = {trk for trk in tracks if trk not in bl_tracks}
        return list(tracks)

    def _find_alb(self, album):
        if not hasattr(album, 'artist'):
            raise PlayerError('Album object have no artist attribute')
        if self.database.get_bl_album(album, add=False):
            self.log.info('Album in blocklist: %s', album)
            return []
        albums = []
        if album.mbid:
            filt = f"(MUSICBRAINZ_ALBUMID == '{album.mbid}')"
            albums = self.find(filt)
        # Now look for album with no MusicBrainzIdentifier
        if not albums and album.Artist.mbid:  # Use album artist MBID if possible
            filt = f"((MUSICBRAINZ_ALBUMARTISTID == '{album.Artist.mbid}') AND (album == '{album.name_sz}'))"
            albums = self.find(filt)
        if not albums:  # Falls back to (album)?artist/album name
            for artist in album.Artist.names_sz:
                filt = f"((albumartist == '{artist}') AND (album == '{album.name_sz}'))"
                albums.extend(self.find(filt))
        return albums
# #### / find_tracks ##

# #### Search Methods #####
    def _find_musicbrainz_artistid(self, artist):
        """Find MusicBrainzArtistID when possible.
        """
        if not self.use_mbid:
            return None
        mbids = None
        for name in artist.names_sz:
            filt = f'((artist == "{name}") AND (MUSICBRAINZ_ARTISTID != ""))'
            mbids = self.list('MUSICBRAINZ_ARTISTID', filt)
            if mbids:
                break
        if not mbids:
            return None
        if len(mbids) > 1:
            self.log.debug("Got multiple MBID for artist: %r", artist)
            return None
        if artist.mbid:
            if artist.mbid != mbids[0]:
                self.log('MBID discrepancy, %s found with %s (instead of %s)',
                         artist.name, mbids[0], artist.mbid)
        else:
            return mbids[0]
        return None

    @bl_artist
    @set_artist_mbid
    def search_artist(self, artist):
        """
        Search artists based on a fuzzy search in the media library
            >>> art = Artist(name='the beatles', mbid=<UUID4>) # mbid optional
            >>> bea = player.search_artist(art)
            >>> print(bea.names)
            >>> ['The Beatles', 'Beatles', 'the beatles']

        :param Artist artist: Artist to look for in MPD music library
        :return: Artist object
        :rtype: Artist
        """
        found = False
        if artist.mbid:
            # look for exact search w/ musicbrainz_artistid
            library = self.list('artist', f"(MUSICBRAINZ_ARTISTID == '{artist.mbid}')")
            if library:
                found = True
                self.log.trace('Found mbid "%r" in library', artist)
                # library could fetch several artist name for a single MUSICBRAINZ_ARTISTID
                if len(library) > 1:
                    self.log.debug('I got "%s" searching for %r', library, artist)
                    for name in library:
                        if SimaStr(artist.name) == name and name != artist.name:
                            self.log.debug('add alias for %s: %s', artist, name)
                            artist.add_alias(name)
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

    def search_albums(self, artist):
        """Find potential albums for "artist"

        * Fetch all albums for "AlbumArtist" == artist
          → falls back to "Artist" == artist when no "AlbumArtist" tag is set
        * Tries to filter some mutli-artists album
          For instance an album by Artist_A may have a track by Artist_B. Then
          looking for albums for Artist_B wrongly returns this album.
        """
        # First, look for all potential albums
        self.log.debug('Searching album for "%r"', artist)
        if artist.aliases:
            self.log.debug('Searching album for %s aliases: "%s"',
                           artist, artist.aliases)
        albums = set()
        if self.use_mbid and artist.mbid:
            mpd_filter = f"((musicbrainz_albumartistid == '{artist.mbid}') AND ( album != ''))"
            raw_album_id = self.list('musicbrainz_albumid', mpd_filter)
            for albumid in raw_album_id:
                mpd_filter = f"((musicbrainz_albumid == '{albumid}') AND ( album != ''))"
                album_name = self.list('album', mpd_filter)
                if not album_name:  # something odd here
                    continue
                albums.add(Album(album_name[0], artist=artist.name,
                                 Artist=artist, mbid=albumid))
        for name_sz in artist.names_sz:
            mpd_filter = f"((albumartist == '{name_sz}') AND ( album != ''))"
            raw_albums = self.list('album', mpd_filter)
            for alb in raw_albums:
                if alb in [a.name for a in albums]:
                    continue
                mbid = None
                if self.use_mbid:
                    _ = Album(alb)
                    mpd_filter = f"((albumartist == '{artist.name_sz}') AND ( album == '{_.name_sz}'))"
                    mbids = self.list('MUSICBRAINZ_ALBUMID', mpd_filter)
                    if mbids:
                        mbid = mbids[0]
                albums.add(Album(alb, artist=artist.name,
                                 Artist=artist, mbid=mbid))
        candidates = []
        for album in albums:
            album_trks = self.find_tracks(album)
            if not album_trks:  # find_track result can be empty, blocklist applied
                continue
            album_artists = {tr.albumartist for tr in album_trks if tr.albumartist}
            if album.Artist.names & album_artists:
                candidates.append(album)
                continue
            if self.use_mbid and artist.mbid:
                if artist.mbid == album_trks[0].musicbrainz_albumartistid:
                    candidates.append(album)
                    continue
                self.log.debug('Discarding "%s", "%r" not set as musicbrainz_albumartistid',
                               album, album.Artist)
                continue
            if 'Various Artists' in album_artists:
                self.log.debug('Discarding %s ("Various Artists" set)', album)
                continue
            if album_artists and album.Artist.name not in album_artists:
                self.log.debug('Discarding "%s", "%s" not set as albumartist', album, album.Artist)
                continue
            # Attempt to detect false positive (especially when no
            # AlbumArtist/MBIDs tag ar set)
            # Avoid selecting albums where artist is credited for a single
            # track of the album
            album_trks = self.find(f"(album == '{album.name_sz}')")
            arts = [trk.artist for trk in album_trks]  # Artists in the album
            # count artist occurences
            ratio = arts.count(album.Artist.name)/len(arts)
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
