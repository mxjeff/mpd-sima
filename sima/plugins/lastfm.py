# -*- coding: utf-8 -*-
"""
Fetching similar artists from last.fm web services
"""

# standart library import
import random

from collections import deque
from hashlib import md5

# third parties componants

# local import
from ..lib.plugin import Plugin
from ..lib.simafm import SimaFM, XmlFMHTTPError, XmlFMNotFound, XmlFMError
from ..lib.track import Track


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
            cls._cache.get('asearch').update({hashedlst:list(results)})
        random.shuffle(results)
        return results
    return wrapper


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
        # TODO: call cleanup once its dict instance are used somewhere XXX
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
        """
        artist = tracks[0].artist
        black_list = self.player.queue + self.to_add
        not_in_hist = list(set(tracks) - set(self.get_history(artist=artist)))
        if not not_in_hist:
            self.log.debug('All tracks already played for "{}"'.format(artist))
        random.shuffle(not_in_hist)
        candidate = [ trk for trk in not_in_hist if trk not in black_list ]
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
        history = deque(self.history)
        history.popleft()
        ret_extra = list()
        depth = 0
        current = self.player.current
        extra_arts = list()
        while depth < int(self.plugin_conf.get('depth')):
            trk = history.popleft()
            if trk.artist in [trk.artist for trk in extra_arts]:
                continue
            extra_arts.append(trk)
            depth += 1
            if len(history) == 0:
                break
        self.log.info('EXTRA ARTS: {}'.format(
            '/'.join([trk.artist for trk in extra_arts])))
        for artist in extra_arts:
            self.log.debug('Looking for artist similar to "{0.artist}" as well'.format(artist))
            similar = self.lfm_similar_artists(artist=artist)
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

    def _track(self):
        """Get some tracks for track queue mode
        """
        artists = self.get_local_similar_artists()
        nbtracks_target = int(self.plugin_conf.get('track_to_add'))
        for artist in artists:
            self.log.debug('Trying to find titles to add for "{}"'.format(
                           artist))
            found = self.player.find_track(artist)
            # find tracks not in history
            self.filter_track(found)
            if len(self.to_add) == nbtracks_target:
                break
        if not self.to_add:
            self.log.debug('Found no unplayed tracks, is your ' +
                             'history getting too large?')
            return None
        for track in self.to_add:
            self.log.info('last.fm candidate: {0!s}'.format(track))

    def _album(self):
        """Get albums for album queue mode
        """
        #artists = self.get_local_similar_artists()
        pass

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
        return candidates

    def callback_player_database(self):
        self._flush_cache()

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
