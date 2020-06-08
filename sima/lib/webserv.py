# -*- coding: utf-8 -*-
# Copyright (c) 2009-2020 kaliko <kaliko@azylum.org>
# Copyright (c) 2019 sacha <sachahony@gmail.com>
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
Fetching similar artists from last.fm web services
"""

# standard library import
import random

from collections import deque
from hashlib import md5

# third parties components

# local import
from .plugin import Plugin
from .track import Track
from .meta import Artist, MetaContainer
from ..utils.utils import WSError, WSNotFound, WSTimeout

def cache(func):
    """Caching decorator"""
    def wrapper(*args, **kwargs):
        #pylint: disable=W0212,C0111
        cls = args[0]
        similarities = [art.name for art in args[1]]
        hashedlst = md5(''.join(similarities).encode('utf-8')).hexdigest()
        if hashedlst in cls._cache.get('asearch'):
            cls.log.debug('cached request')
            results = cls._cache.get('asearch').get(hashedlst)
        else:
            results = func(*args, **kwargs)
            cls.log.debug('caching request')
            cls._cache.get('asearch').update({hashedlst:list(results)})
        random.shuffle(results)
        return results
    return wrapper


class WebService(Plugin):
    """similar artists webservice
    """
    # pylint: disable=bad-builtin

    def __init__(self, daemon):
        Plugin.__init__(self, daemon)
        self.daemon_conf = daemon.config
        self.sdb = daemon.sdb
        self.history = daemon.short_history
        ##
        self.to_add = list()
        self._cache = None
        self._flush_cache()
        wrapper = {'track': self._track,
                   'top': self._top,
                   'album': self._album}
        self.queue_mode = wrapper.get(self.plugin_conf.get('queue_mode'))
        self.ws = None
        self.ws_retry = 0

    def _flush_cache(self):
        """
        Both flushes and instanciates _cache
        """
        name = self.__class__.__name__
        if isinstance(self._cache, dict):
            self.log.info('%s: Flushing cache!', name)
        else:
            self.log.info('%s: Initialising cache!', name)
        self._cache = {'asearch': dict(),
                       'tsearch': dict()}

    def _cleanup_cache(self):
        """Avoid bloated cache
        """
        for _, val in self._cache.items():
            if isinstance(val, dict):
                while len(val) > 150:
                    val.popitem()

    def get_history(self, artist):
        """Constructs list of Track for already played titles for an artist.
        """
        duration = self.daemon_conf.getint('sima', 'history_duration')
        tracks_from_db = self.sdb.get_history(duration=duration, artist=artist)
        # Construct Track() objects list from database history
        played_tracks = [Track(artist=tr[-1], album=tr[1], title=tr[2],
                               file=tr[3]) for tr in tracks_from_db]
        return played_tracks

    def filter_track(self, tracks):
        """
        Extract one unplayed track from a Track object list.
            * not in history
            * not already in the queue
            * not blacklisted
        Then add to candidates in self.to_add
        """
        artist = tracks[0].artist
        # In random play mode use complete playlist to filter
        if self.player.playmode.get('random'):
            black_list = self.player.playlist + self.to_add
        else:
            black_list = self.player.queue + self.to_add
        not_in_hist = list(set(tracks) - set(self.get_history(artist=artist)))
        if self.plugin_conf.get('queue_mode') != 'top' and not not_in_hist:
            self.log.debug('All tracks already played for "%s"', artist)
        random.shuffle(not_in_hist)
        candidate = []
        for trk in [_ for _ in not_in_hist if _ not in black_list]:
            # Should use albumartist heuristic as well
            if self.plugin_conf.getboolean('single_album'):  # pylint: disable=no-member
                if (trk.album == self.player.current.album or
                        trk.album in [tr.album for tr in black_list]):
                    self.log.debug('Found unplayed track ' +
                                   'but from an album already queued: %s', trk)
                    continue
            candidate.append(trk)
        if not candidate:
            return False
        self.to_add.append(random.choice(candidate))
        return True

    def _get_artists_list_reorg(self, alist):
        """
        Move around items in artists_list in order to play first not recently
        played artists
        """
        hist = list()
        duration = self.daemon_conf.getint('sima', 'history_duration')
        for art in self.sdb.get_artists_history(alist, duration=duration):
            if art not in hist:
                hist.insert(0, art)
        reorg = [art for art in alist if art not in hist]
        reorg.extend(hist)
        return reorg

    @cache
    def get_artists_from_player(self, similarities):
        """
        Look in player library for availability of similar artists in
        similarities
        """
        dynamic = self.plugin_conf.getint('max_art') # pylint: disable=no-member
        if dynamic <= 0:
            dynamic = 100
        results = list()
        similarities.reverse()
        while (len(results) < dynamic
               and len(similarities) > 0):
            art_pop = similarities.pop()
            res = self.player.search_artist(art_pop)
            if res:
                results.append(res)
        return results

    def ws_similar_artists(self, artist):
        """
        Retrieve similar artists from WebServive.
        """
        # initialize artists deque list to construct from DB
        as_art = deque()
        as_artists = self.ws.get_similar(artist=artist)
        self.log.debug('Requesting %s for %r', self.ws.name, artist)
        try:
            [as_art.append(art) for art in as_artists]
        except WSNotFound as err:
            self.log.warning('%s: %s', self.ws.name, err)
            if artist.mbid:
                self.log.debug('Trying without MusicBrainzID')
                try:
                    return self.ws_similar_artists(Artist(name=artist.name))
                except WSNotFound as err:
                    self.log.debug('%s: %s', self.ws.name, err)
        except WSTimeout as err:
            self.log.warning('%s: %s', self.ws.name, err)
            if self.ws_retry < 3:
                self.ws_retry += 1
                self.log.warning('%s: retrying', self.ws.name)
                as_art = self.ws_similar_artists(artist)
            else:
                self.log.warning('%s: stop retrying', self.ws.name)
            self.ws_retry = 0
        except WSError as err:
            self.log.warning('%s: %s', self.ws.name, err)
        if as_art:
            self.log.debug('Fetched %d artist(s)', len(as_art))
        return as_art

    def get_recursive_similar_artist(self):
        """Check against local player for similar artists (recursive w/ history)
        """
        if not self.player.playlist:
            return []
        history = list(self.history)
        # In random play mode use complete playlist to filter
        if self.player.playmode.get('random'):
            history = self.player.playlist + history
        else:
            history = self.player.queue + history
        history = deque(history)
        last_trk = history.popleft() # remove
        extra_arts = list()
        ret_extra = list()
        depth = 0
        while depth < self.plugin_conf.getint('depth'): # pylint: disable=no-member
            if len(history) == 0:
                break
            trk = history.popleft()
            if (trk.Artist in extra_arts
                    or trk.Artist == last_trk.Artist):
                continue
            extra_arts.append(trk.Artist)
            depth += 1
        self.log.debug('EXTRA ARTS: %s', '/'.join(map(str, extra_arts)))
        for artist in extra_arts:
            self.log.debug('Looking for artist similar '
                           'to "%s" as well', artist)
            similar = self.ws_similar_artists(artist=artist)
            if not similar:
                continue
            ret_extra.extend(self.get_artists_from_player(similar))

        if last_trk.Artist in ret_extra:
            ret_extra.remove(last_trk.Artist)
        if ret_extra:
            self.log.debug('similar artist(s) found: %s',
                           ' / '.join(map(str, MetaContainer(ret_extra))))
        return ret_extra

    def get_local_similar_artists(self):
        """Check against local player for similar artists
        """
        if not self.player.playlist:
            return []
        tolookfor = self.player.playlist[-1].Artist
        self.log.info('Looking for artist similar to "%s"', tolookfor)
        self.log.debug(repr(tolookfor))
        similar = self.ws_similar_artists(tolookfor)
        if not similar:
            self.log.info('Got nothing from %s!', self.ws.name)
            return []
        self.log.info('First five similar artist(s): %s...',
                      ' / '.join(map(str, list(similar)[:5])))
        self.log.info('Looking availability in music library')
        ret = MetaContainer(self.get_artists_from_player(similar))
        if ret:
            self.log.debug('regular found in library: %s',
                           ' / '.join(map(str, ret)))
        else:
            self.log.debug('Got nothing similar from library!')
        ret_extra = None
        if len(self.history) >= 2:
            if self.plugin_conf.getint('depth') > 1: # pylint: disable=no-member
                ret_extra = self.get_recursive_similar_artist()
        if ret_extra:
            # get them reorg to pick up best element
            ret_extra = self._get_artists_list_reorg(ret_extra)
            # tries to pickup less artist from extra art
            if len(ret) < 4:
                ret_extra = MetaContainer(ret_extra)
            else:
                ret_extra = MetaContainer(ret_extra[:max(4, len(ret))//2])
            if ret_extra:
                self.log.debug('extra found in library: %s',
                               ' / '.join(map(str, ret_extra)))
            ret = ret | ret_extra
        if not ret:
            self.log.warning('Got nothing from music library.')
            return []
        # In random play mode use complete playlist to filter
        if self.player.playmode.get('random'):
            queued_artists = MetaContainer([trk.Artist for trk in self.player.playlist])
        else:
            queued_artists = MetaContainer([trk.Artist for trk in self.player.queue])
        self.log.trace('Already queued: %s', queued_artists)
        self.log.trace('Candidate: %s', ret)
        if ret & queued_artists:
            self.log.debug('Removing already queued artists: '
                           '%s', '/'.join(map(str, ret & queued_artists)))
            ret = ret - queued_artists
        current = self.player.current
        if current and current.Artist in ret:
            self.log.debug('Removing current artist: %s', current.Artist)
            ret = ret - MetaContainer([current.Artist])
        # Move around similars items to get in unplayed|not recently played
        # artist first.
        self.log.info('Got %d artists in library', len(ret))
        candidates = self._get_artists_list_reorg(list(ret))
        if candidates:
            self.log.info(' / '.join(map(str, candidates)))
        return candidates

    def _get_album_history(self, artist):
        """Retrieve album history"""
        albums_list = set()
        for trk in self.get_history(artist=artist.name):
            if not trk.album:
                continue
            albums_list.add(trk.album)
        return albums_list

    def find_album(self, artists):
        """Find albums to queue.
        """
        self.to_add = list()
        nb_album_add = 0
        target_album_to_add = self.plugin_conf.getint('album_to_add')  # pylint: disable=no-member
        for artist in artists:
            self.log.info('Looking for an album to add for "%s"...' % artist)
            albums = self.player.search_albums(artist)
            if not albums:
                continue
            self.log.debug('Albums candidate: %s', albums)
            albums_hist = self._get_album_history(artist)
            albums_not_in_hist = [a for a in albums if a.name not in albums_hist]
            # Get to next artist if there are no unplayed albums
            if not albums_not_in_hist:
                self.log.info('No unplayed album found for "%s"' % artist)
                continue
            album_to_queue = []
            random.shuffle(albums_not_in_hist)
            for album in albums_not_in_hist:
                # Controls the album found is not already queued
                if album in {t.album for t in self.player.queue}:
                    self.log.debug('"%s" already queued, skipping!', album)
                    continue
                # In random play mode use complete playlist to filter
                if self.player.playmode.get('random'):
                    if album in {t.album for t in self.player.playlist}:
                        self.log.debug('"%s" already in playlist, skipping!', album)
                        continue
                album_to_queue = album
            if not album_to_queue:
                self.log.info('No album found for "%s"', artist)
                continue
            self.log.info('%s album candidate: %s - %s', self.ws.name,
                          artist, album_to_queue)
            nb_album_add += 1
            candidates = self.player.find_tracks(album)
            if self.plugin_conf.getboolean('shuffle_album'):
                random.shuffle(candidates)
            # this allows to select a maximum number of track from the album
            # a value of 0 (default) means keep all
            nbtracks = self.plugin_conf.getint('track_to_add_from_album')
            if nbtracks > 0:
                candidates = candidates[0:nbtracks]
            self.to_add.extend(candidates)
            if nb_album_add == target_album_to_add:
                return True

    def find_top(self, artists):
        """
        find top tracks for artists in artists list.
        """
        self.to_add = list()
        nbtracks_target = self.plugin_conf.getint('track_to_add') # pylint: disable=no-member
        for artist in artists:
            if len(self.to_add) == nbtracks_target:
                return
            self.log.info('Looking for a top track for %s', artist)
            titles = deque()
            try:
                titles = [t for t in self.ws.get_toptrack(artist)]
            except WSError as err:
                self.log.warning('%s: %s', self.ws.name, err)
                continue
            for trk in titles:
                found = self.player.search_track(artist, trk.title)
                if found:
                    random.shuffle(found)
                    if self.filter_track(found):
                        break

    def _track(self):
        """Get some tracks for track queue mode
        """
        artists = self.get_local_similar_artists()
        nbtracks_target = self.plugin_conf.getint('track_to_add')  # pylint: disable=no-member
        for artist in artists:
            self.log.debug('Trying to find titles to add for "%r"', artist)
            found = self.player.find_tracks(artist)
            random.shuffle(found)
            if not found:
                self.log.debug('Found nothing to queue for %s', artist)
                continue
            # find tracks not in history for artist
            self.filter_track(found)
            if len(self.to_add) == nbtracks_target:
                break
        if not self.to_add:
            self.log.debug('Found no tracks to queue!')
            return None
        for track in self.to_add:
            self.log.info('%s candidates: %s', track, self.ws.name)

    def _album(self):
        """Get albums for album queue mode
        """
        artists = self.get_local_similar_artists()
        self.find_album(artists)

    def _top(self):
        """Get some tracks for top track queue mode
        """
        artists = self.get_local_similar_artists()
        self.find_top(artists)
        for track in self.to_add:
            self.log.info('%s candidates: %s', self.ws.name, track)

    def callback_need_track(self):
        self._cleanup_cache()
        if len(self.player.playlist) == 0:
            self.log.info('No last track, cannot queue')
            return None
        if not self.player.playlist[-1].artist:
            self.log.warning('No artist set for the last track in queue')
            self.log.debug(repr(self.player.current))
            return None
        self.queue_mode()
        msg = ' '.join(['{0}: {1:>3d}'.format(k, v) for
                        k, v in sorted(self.ws.stats.items())])
        self.log.debug('http stats: ' + msg)
        candidates = self.to_add
        self.to_add = list()
        if self.plugin_conf.get('queue_mode') != 'album':
            random.shuffle(candidates)
        return candidates

    def callback_player_database(self):
        self._flush_cache()

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
