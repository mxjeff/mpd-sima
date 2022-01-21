# -*- coding: utf-8 -*-
# Copyright (c) 2013-2015, 2020-2021 kaliko <kaliko@azylum.org>
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
Plugin object to derive from
"""

import random

from .meta import Artist, MetaContainer


class Plugin:
    """
    First non-empty line of the docstring is used as description
    Rest of the docstring at your convenience.

    The lowercased plugin Name MUST be the same as the module (file name),
    for instance Plugin → plugin.py
    It eases plugins discovery and simplifies the code to handle them,
    IMHO, it's a fair trade-off.
    """

    @classmethod
    def info(cls):
        """self documenting class method
        """
        doc = f'Undocumented plugin! Fill "{cls.__name__}" docstring'
        if cls.__doc__:
            doc = cls.__doc__.strip(' \n').splitlines()[0]
        return {'name': cls.__name__,
                'doc': doc}

    def __init__(self, daemon):
        self.log = daemon.log
        self.player = daemon.player
        self.plugin_conf = None
        self.main_conf = daemon.config
        self.sdb = daemon.sdb
        self.__get_config()

    def __str__(self):
        return self.__class__.__name__

    def __get_config(self):
        """Get plugin's specific configuration from global applications's config
        """
        conf = self.main_conf
        for sec in conf.sections():  # Discovering plugin conf
            if sec == self.__class__.__name__.lower():
                self.plugin_conf = conf[sec]
                if 'priority' not in self.plugin_conf:
                    self.plugin_conf['priority'] = '80'
        if not self.plugin_conf:
            self.plugin_conf = {'priority': '80'}
        #if self.plugin_conf:
        #   self.log.debug('Got config for %s: %s', self, self.plugin_conf)

    @property
    def priority(self):
        return self.plugin_conf.get('priority')

    def start(self):
        """
        Called when the daemon().run() is called and
        right after the player has connected successfully.
        """

    def callback_player(self):
        """
        Called on player changes, stopped, paused, skipped
        """

    def callback_player_database(self):
        """
        Called on player music library changes
        """

    def callback_playlist(self):
        """
        Called on playlist changes
        Not returning data
        """

    def callback_next_song(self):
        """
        Could be use to scrobble, maintain an history…
        Not returning data,
        """

    def callback_need_track(self):
        """
        Returns a list of Track objects to add
        """

    def shutdown(self):
        """Called on application shutdown"""


class AdvancedPlugin(Plugin):
    """Object to derive from for plugins
    Exposes advanced music library look up with use of play history
    """

    # Query History
    def get_history(self):
        """Returns a Track list of already played artists."""
        duration = self.main_conf.getint('sima', 'history_duration')
        return self.sdb.fetch_history(duration=duration)

    def get_album_history(self, artist):
        """Retrieve album history"""
        duration = self.main_conf.getint('sima', 'history_duration')
        return self.sdb.fetch_albums_history(needle=artist, duration=duration)

    def get_reorg_artists_list(self, alist):
        """
        Move around items in alist in order to have first not recently
        played (or about to be played) artists.

        :param {Artist} alist: Artist objects list/container
        """
        queued_artist = MetaContainer([Artist(_.artist) for _ in
                                       self.player.queue if _.artist])
        not_queued_artist = alist - queued_artist
        duration = self.main_conf.getint('sima', 'history_duration')
        hist = []
        for art in self.sdb.fetch_artists_history(alist, duration=duration):
            if art not in hist:
                if art not in queued_artist:
                    hist.insert(0, art)
                else:
                    hist.append(art)
        # Find not recently played (not in history) & not in queue
        reorg = [art for art in not_queued_artist if art not in hist]
        reorg.extend(hist)
        return reorg
    # /Query History

    # Find not recently played/unplayed
    def album_candidate(self, artist, unplayed=True):
        """Search an album for artist

        :param Artist artist: Artist to fetch an album for
        :param bool unplayed: Fetch only unplayed album
        """
        self.log.info('Searching an album for "%s"...', artist)
        albums = self.player.search_albums(artist)
        if not albums:
            return None
        self.log.debug('Albums to choose from: %s', albums)
        albums_hist = self.get_album_history(artist)
        self.log.trace('Albums history: %s', [a.name for a in albums_hist])
        albums_not_in_hist = [a for a in albums if a.name not in albums_hist]
        # Get to next artist if there are no unplayed albums
        if not albums_not_in_hist:
            self.log.info('No unplayed album found for "%s"', artist)
            if unplayed:
                return None
        random.shuffle(albums_not_in_hist)
        albums_not_in_hist.extend(albums_hist)
        self.log.trace('Album candidates: %s', albums_not_in_hist)
        album_to_queue = []
        for album in albums_not_in_hist:
            # Controls the album found is not already queued
            if album in {t.Album.name for t in self.player.queue}:
                self.log.debug('"%s" already queued, skipping!', album)
                continue
            # In random play mode use complete playlist to filter
            # Yes indeed, some users play in random with album mode :|
            if self.player.playmode.get('random'):
                if album in {t.Album.name for t in self.player.playlist}:
                    self.log.debug('"%s" already in playlist, skipping!',
                                   album)
                    continue
            album_to_queue = album
            break
        if not album_to_queue:
            self.log.info('No album found for "%s"', artist)
            return None
        self.log.info('%s plugin chose album: %s - %s',
                      self.__class__.__name__, artist, album_to_queue)
        return album_to_queue

    def filter_track(self, tracks, chosen=None, unplayed=False):
        """
        Extract one unplayed track from a Track object list.
            * not in history
            * not already in the queue

        :param list(Track) tracks: List of tracks to chose from
        :param list(Track) chosen: List of tracks previously chosen
        :param bool unplayed: chose only unplayed (honoring history duration setting)
        :return: A Track
        :rtype: Track
        """
        artist = tracks[0].Artist
        # In random play mode use complete playlist to filter
        if self.player.playmode.get('random'):
            deny_list = self.player.playlist
        else:
            deny_list = self.player.queue
        not_in_hist = list(set(tracks) - set(self.sdb.fetch_history(artist=artist)))
        if not not_in_hist:
            self.log.debug('All tracks already played for "%s"', artist)
            if unplayed:
                return None
        random.shuffle(not_in_hist)
        candidates = []
        for trk in [_ for _ in not_in_hist if _ not in deny_list]:
            # Should use albumartist heuristic as well
            if self.plugin_conf.getboolean('single_album', False):  # pylint: disable=no-member
                albums = [tr.Album for tr in deny_list]
                albums += [tr.Album for tr in chosen]
                if (trk.Album == self.player.current.Album or
                        trk.Album in albums):
                    self.log.debug('Found unplayed track ' +
                                   'but from an album already queued: %s', trk)
                    continue
            candidates.append(trk)
        if not candidates:
            return None
        return random.choice(candidates)

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
