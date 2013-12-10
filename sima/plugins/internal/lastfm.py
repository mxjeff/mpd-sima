# -*- coding: utf-8 -*-
"""
Fetching similar artists from last.fm web services
"""

# standart library import
import random

from collections import deque
from itertools import dropwhile
from hashlib import md5

# third parties componants

# local import
from ...lib.plugin import Plugin
from ...lib.simafm import SimaFM, XmlFMHTTPError, XmlFMNotFound, XmlFMError
from ...lib.track import Track


def cache(func):
    """Caching decorator"""
    def wrapper(*args, **kwargs):
        #pylint: disable=W0212,C0111
        cls = args[0]
        similarities = [art + str(match) for art, match in args[1]]
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


def blacklist(artist=False, album=False, track=False):
    #pylint: disable=C0111,W0212
    field = (artist, album, track)
    def decorated(func):
        def wrapper(*args, **kwargs):
            cls = args[0]
            boolgen = (bl for bl in field)
            bl_fun = (cls._Plugin__daemon.sdb.get_bl_artist,
                      cls._Plugin__daemon.sdb.get_bl_album,
                      cls._Plugin__daemon.sdb.get_bl_track,)
            #bl_getter = next(fn for fn, bl in zip(bl_fun, boolgen) if bl is True)
            bl_getter = next(dropwhile(lambda _: not next(boolgen), bl_fun))
            cls.log.debug('using {0} as bl filter'.format(bl_getter.__name__))
            if artist:
                results = func(*args, **kwargs)
                for elem in results:
                    if bl_getter(elem, add_not=True):
                        cls.log.info('Blacklisted: {0}'.format(elem))
                        results.remove(elem)
                return results
            if track:
                for elem in args[1]:
                    if bl_getter(elem, add_not=True):
                        cls.log.info('Blacklisted: {0}'.format(elem))
                        args[1].remove(elem)
                return func(*args, **kwargs)
        return wrapper
    return decorated


class Lastfm(Plugin):
    """last.fm similar artists
    """

    def __init__(self, daemon):
        Plugin.__init__(self, daemon)
        self.daemon_conf = daemon.config
        self.sdb = daemon.sdb
        self.history = daemon.short_history
        ##
        self.to_add = list()
        self._cache = None
        self._flush_cache()
        wrapper = {
                'track': self._track,
                'top': self._top,
                'album': self._album,
                }
        self.queue_mode = wrapper.get(self.plugin_conf.get('queue_mode'))

    def _flush_cache(self):
        """
        Both flushes and instanciates _cache
        """
        if isinstance(self._cache, dict):
            self.log.info('Lastfm: Flushing cache!')
        else:
            self.log.info('Lastfm: Initialising cache!')
        self._cache = {
                'artists': None,
                'asearch': dict(),
                'tsearch': dict(),
                }
        self._cache['artists'] = frozenset(self.player.list('artist'))

    def _cleanup_cache(self):
        """Avoid bloated cache
        """
        for _ , val in self._cache.items():
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
        """
        artist = tracks[0].artist
        black_list = self.player.queue + self.to_add
        not_in_hist = list(set(tracks) - set(self.get_history(artist=artist)))
        if not not_in_hist:
            self.log.debug('All tracks already played for "{}"'.format(artist))
        random.shuffle(not_in_hist)
        #candidate = [ trk for trk in not_in_hist if trk not in black_list
                      #if not self.sdb.get_bl_track(trk, add_not=True)]
        candidate = []
        for trk in [_ for _ in not_in_hist if _ not in black_list]:
            if self.sdb.get_bl_track(trk, add_not=True):
                self.log.info('Blacklisted: {0}: '.format(trk))
                continue
            if self.sdb.get_bl_album(trk, add_not=True):
                self.log.info('Blacklisted album: {0}: '.format(trk))
                continue
            # Should use albumartist heuristic as well
            if self.plugin_conf.getboolean('single_album'):
                if (trk.album == self.player.current.album or
                    trk.album in [tr.album for tr in self.to_add]):
                    self.log.debug('Found unplayed track ' +
                               'but from an album already queued: %s' % (trk))
                    continue
            candidate.append(trk)
        if not candidate:
            self.log.debug('Unable to find title to add' +
                           ' for "%s".' % artist)
            return None
        self.to_add.append(random.choice(candidate))

    def _get_artists_list_reorg(self, alist):
        """
        Move around items in artists_list in order to play first not recently
        played artists
        """
        # TODO: move to utils as a decorator
        duration = self.daemon_conf.getint('sima', 'history_duration')
        art_in_hist = list()
        for trk in self.sdb.get_history(duration=duration,
                                        artists=alist):
            if trk[0] not in art_in_hist:
                art_in_hist.append(trk[0])
        art_in_hist.reverse()
        art_not_in_hist = [ ar for ar in alist if ar not in art_in_hist ]
        random.shuffle(art_not_in_hist)
        art_not_in_hist.extend(art_in_hist)
        self.log.debug('history ordered: {}'.format(
                       ' / '.join(art_not_in_hist)))
        return art_not_in_hist

    @blacklist(artist=True)
    @cache
    def get_artists_from_player(self, similarities):
        """
        Look in player library for availability of similar artists in
        similarities
        """
        dynamic = int(self.plugin_conf.get('dynamic'))
        if dynamic <= 0:
            dynamic = 100
        similarity = int(self.plugin_conf.get('similarity'))
        results = list()
        similarities.reverse()
        while (len(results) < dynamic
            and len(similarities) > 0):
            art_pop, match = similarities.pop()
            if match < similarity:
                break
            results.extend(self.player.fuzzy_find(art_pop))
        results and self.log.debug('Similarity: %d%%' % match) # pylint: disable=w0106
        return results

    def lfm_similar_artists(self, artist=None):
        """
        Retrieve similar artists on last.fm server.
        """
        if artist is None:
            current = self.player.current
        else:
            current = artist
        simafm = SimaFM()
        # initialize artists deque list to construct from DB
        as_art = deque()
        as_artists = simafm.get_similar(artist=current.artist)
        self.log.debug('Requesting last.fm for "{0.artist}"'.format(current))
        try:
            [as_art.append((a, m)) for a, m in as_artists]
        except XmlFMHTTPError as err:
            self.log.warning('last.fm http error: %s' % err)
        except XmlFMNotFound as err:
            self.log.warning("last.fm: %s" % err)
        except XmlFMError as err:
            self.log.warning('last.fm module error: %s' % err)
        if as_art:
            self.log.debug('Fetched %d artist(s) from last.fm' % len(as_art))
        return as_art

    def get_recursive_similar_artist(self):
        ret_extra = list()
        history = deque(self.history)
        history.popleft()
        depth = 0
        current = self.player.current
        extra_arts = list()
        while depth < int(self.plugin_conf.get('depth')):
            if len(history) == 0:
                break
            trk = history.popleft()
            if (trk.artist in [trk.artist for trk in extra_arts]
                or trk.artist == current.artist):
                continue
            extra_arts.append(trk)
            depth += 1
        self.log.info('EXTRA ARTS: {}'.format(
            '/'.join([trk.artist for trk in extra_arts])))
        for artist in extra_arts:
            self.log.debug('Looking for artist similar to "{0.artist}" as well'.format(artist))
            similar = self.lfm_similar_artists(artist=artist)
            if not similar:
                return ret_extra
            similar = sorted(similar, key=lambda sim: sim[1], reverse=True)
            ret_extra.extend(self.get_artists_from_player(similar))
            if current.artist in ret_extra:
                ret_extra.remove(current.artist)
        return ret_extra

    def get_local_similar_artists(self):
        """Check against local player for similar artists fetched from last.fm
        """
        current = self.player.current
        self.log.info('Looking for artist similar to "{0.artist}"'.format(current))
        similar = self.lfm_similar_artists()
        if not similar:
            self.log.info('Got nothing from last.fm!')
            return []
        similar = sorted(similar, key=lambda sim: sim[1], reverse=True)
        self.log.info('First five similar artist(s): {}...'.format(
                      ' / '.join([a for a, m in similar[0:5]])))
        self.log.info('Looking availability in music library')
        ret = self.get_artists_from_player(similar)
        ret_extra = None
        if len(self.history) >= 2:
            ret_extra = self.get_recursive_similar_artist()
        if not ret:
            self.log.warning('Got nothing from music library.')
            self.log.warning('Try running in debug mode to guess why...')
            return []
        if ret_extra:
            ret = list(set(ret) | set(ret_extra))
        self.log.info('Got {} artists in library'.format(len(ret)))
        self.log.info(' / '.join(ret))
        # Move around similars items to get in unplayed|not recently played
        # artist first.
        return self._get_artists_list_reorg(ret)

    def _detects_var_artists_album(self, album, artist):
        """Detects either an album is a "Various Artists" or a
        single artist release."""
        art_first_track = None
        for track in self.player.find_album(artist, album):
            if not art_first_track:  # set artist for the first track
                art_first_track = track.artist
            alb_art = track.albumartist
            #  Special heuristic used when AlbumArtist is available
            if (alb_art):
                if artist == alb_art:
                    # When album artist field is similar to the artist we're
                    # looking an album for, the album is considered good to
                    # queue
                    return False
                else:
                    self.log.debug(track)
                    self.log.debug('album art says "%s", looking for "%s",'
                                   ' not queueing this album' %
                                   (alb_art, artist))
                    return True
        return False

    def _get_album_history(self, artist=None):
        """Retrieve album history"""
        duration = self.daemon_conf.getint('sima', 'history_duration')
        albums_list = set()
        for trk in self.sdb.get_history(artist=artist, duration=duration):
            albums_list.add(trk[1])
        return albums_list

    def find_album(self, artists):
        """Find albums to queue.
        """
        self.to_add = list()
        nb_album_add = 0
        target_album_to_add = int(self.plugin_conf.get('album_to_add'))
        for artist in artists:
            self.log.info('Looking for an album to add for "%s"...' % artist)
            albums = set(self.player.find_albums(artist))
            # albums yet in history for this artist
            albums_yet_in_hist = albums & self._get_album_history(artist=artist)
            albums_not_in_hist = list(albums - albums_yet_in_hist)
            # Get to next artist if there are no unplayed albums
            if not albums_not_in_hist:
                self.log.info('No album found for "%s"' % artist)
                continue
            album_to_queue = str()
            random.shuffle(albums_not_in_hist)
            for album in albums_not_in_hist:
                tracks = self.player.find('album', album)
                if self._detects_var_artists_album(album, artist):
                    continue
                if tracks and self.sdb.get_bl_album(tracks[0], add_not=True):
                    self.log.info('Blacklisted album: "%s"' % album)
                    self.log.debug('using track: "%s"' % tracks[0])
                    continue
                # Look if one track of the album is already queued
                # Good heuristic, at least enough to guess if the whole album is
                # already queued.
                if tracks[0] in self.player.queue:
                    self.log.debug('"%s" already queued, skipping!' %
                            tracks[0].album)
                    continue
                album_to_queue = album
            if not album_to_queue:
                self.log.info('No album found for "%s"' % artist)
                continue
            self.log.info('last.fm album candidate: {0} - {1}'.format(
                           artist, album_to_queue))
            nb_album_add += 1
            self.to_add.extend(self.player.find_album(artist, album_to_queue))
            if nb_album_add == target_album_to_add:
                return True

    def _track(self):
        """Get some tracks for track queue mode
        """
        artists = self.get_local_similar_artists()
        nbtracks_target = int(self.plugin_conf.get('track_to_add'))
        for artist in artists:
            self.log.debug('Trying to find titles to add for "{}"'.format(
                           artist))
            found = self.player.find_track(artist)
            # find tracks not in history for artist
            self.filter_track(found)
            if len(self.to_add) == nbtracks_target:
                break
        if not self.to_add:
            self.log.debug('Found no tracks to queue, is your ' +
                            'history getting too large?')
            return None
        for track in self.to_add:
            self.log.info('last.fm candidate: {0!s}'.format(track))

    def _album(self):
        """Get albums for album queue mode
        """
        artists = self.get_local_similar_artists()
        self.find_album(artists)

    def _top(self):
        """Get some tracks for top track queue mode
        """
        #artists = self.get_local_similar_artists()
        pass

    def callback_need_track(self):
        self._cleanup_cache()
        if not self.player.current:
            self.log.info('Not currently playing track, cannot queue')
            return None
        self.queue_mode()
        candidates = self.to_add
        self.to_add = list()
        if self.plugin_conf.get('queue_mode') != 'album':
            random.shuffle(candidates)
        return candidates

    def callback_player_database(self):
        self._flush_cache()

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
