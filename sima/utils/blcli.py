# -*- coding: utf-8 -*-
# Copyright (c) 2021 kaliko <kaliko@azylum.org>
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
import atexit
import sys

# local import
from ..mpdclient import MPD, Artist, Album
from ..lib.simadb import SimaDB


class BLCli(MPD):

    def __init__(self, conf, options):
        super().__init__(conf)
        self.options = options
        self.sdb = SimaDB(db_path=conf.get('sima', 'db_file'))
        atexit.register(self.disconnect)
        cmd = options.get('command', None)
        if not cmd or not cmd.startswith('bl-'):
            return
        getattr(self, cmd.replace('-', '_'))()

    def bl_view(self):
        blocklist = self.sdb.view_bl()
        for entry in ['artist', 'album', 'title']:
            header = False
            for blitem in blocklist:
                val = blitem.get(entry, '')
                mbid = blitem.get(f'musicbrainz_{entry}', '')
                if val or mbid:
                    if not header:
                        header = True
                        self.log.info(f'{entry.capitalize()}'
                                      '(id name musicbranzID):')
                    self.log.info(f'{blitem["id"]} "{val}"\t\t{mbid}')

    def bl_add_artist(self):
        artist = self.options.get('artist', None)
        self.connect()
        if not artist:  # artist not provided
            self.log.debug('current track: %r', self.current)
            if not self.current:
                self.log.error('No current song, cannot proceed')
                return
            if not self.current.artist:
                self.log.error('No artist for the current song: %r',
                               self.current)
                return
            self.log.info('Using "%s" (from current track)', self.current.artist)
            artist = self.current.Artist
        else:  # artist provided
            self.log.debug('Looking for %r', artist)
            search = self.search_artist(Artist(name=artist))
            if not search:
                self.log.warning('Artist not found: "%s"', artist)
                return
            self.log.info('Found artist in library: %s', search)
            artist = search
        if self.sdb.get_bl_artist(artist, add=False):
            self.log.info('Already in blocklist')
            return
        self.log.info('Add artist to blocklist "%s"', artist.name)
        self.sdb.get_bl_artist(artist)

    def bl_add_album(self):
        album = self.options.get('album', None)
        self.connect()
        if not album:  # album not provided
            self.log.debug('current track: %r', self.current)
            if not self.current:
                self.log.error('No current song, cannot proceed')
                return
            if not self.current.album:
                self.log.error('No album for the current song: %r',
                               self.current)
                return
            if not self.current.artist:
                self.log.error('No artist for the current song: %r',
                               self.current)
                return
            self.log.info('Using "%s" (from current track)', self.current.album)
            album = Album(self.current.album, mbid=self.current.musicbrainz_albumid,
                          artist=self.current.Artist)
        else:  # album provided
            self.log.debug('Looking for %r', album)
            album = Album(album)
            tracks = self.find(f'(album == "{album.name_sz}")',
                               'window', (0, 1))
            if not tracks:
                self.log.warning('Album not found: "%s"', album)
                return
            track = tracks[0]
            album = Album(name=track.album, mbid=track.musicbrainz_albumid)
            self.log.info('Found album in library: %s (by "%s")',
                          album, track.Artist.albumartist)
        if self.sdb.get_bl_album(album, add=False):
            self.log.info('Already in blocklist')
            return
        self.log.info('Add album to blocklist "%s"', album)
        self.sdb.get_bl_album(album)

    def bl_add_track(self):
        track = self.options.get('track', None)
        self.connect()
        if not track:  # track not provided
            self.log.debug('current track: %r', self.current)
            if not self.current:
                self.log.error('No current song, cannot proceed')
                return
            if not self.current.title:
                self.log.error('No title for the current song: %r',
                               self.current)
                return
            self.log.info('Using "%s" (from current track)', self.current.title)
            track = self.current
        else:  # track provided
            self.log.debug('Looking for %r', track)
            track_sz = track.replace("'", r"\'")
            tracks = self.find(f'(title == "{track_sz}")')
            if not tracks:
                self.log.warning('Track not found: "%s"', track)
                return
            if len(tracks) > 1:
                artists = {t.artist for t in tracks}
                if len(artists) > 1:
                    self.log.error('Found various artists for this title: %s',
                                   artists)
                    return
            track = tracks[0]
        if self.sdb.get_bl_track(track, add=False):
            self.log.info('Already in blocklist')
            return
        self.log.info('Add track to blocklist "%s"', track)
        self.sdb.get_bl_track(track)

    def bl_delete(self):
        blid = self.options.get('id', None)
        blocklist = self.sdb.view_bl()
        if blid not in [bl['id'] for bl in blocklist]:
            self.log.error('Blocklist ID not found: %s', blid)
        self.sdb._remove_blocklist_id(blid)

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab fileencoding=utf8
