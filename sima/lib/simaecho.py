# -*- coding: utf-8 -*-

# Copyright (c) 2014 Jack Kaliko <kaliko@azylum.org>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#

"""
Consume EchoNest web service
"""

__version__ = '0.0.5'
__author__ = 'Jack Kaliko'



from sima import ECH
from sima.lib.meta import Artist
from sima.lib.track import Track
from sima.lib.http import HttpClient
from sima.utils.utils import WSError, WSNotFound
from sima.utils.utils import getws
if len(ECH.get('apikey')) == 23:  # simple hack allowing imp.reload
    getws(ECH)


def get_mbid(obj, foreign='foreign_ids'):
    if foreign in obj:
        for frgnid in obj.get(foreign):
            if frgnid.get('catalog') == 'musicbrainz':
                return frgnid.get('foreign_id').split(':')[2]
    return None


class SimaEch:
    """EchoNest http client
    """
    root_url = 'http://{host}/api/{version}'.format(**ECH)
    name = 'EchoNest'
    cache = False
    """HTTP cache to use, in memory or persitent.

    :param BaseCache cache: Set a cache, defaults to `False`.
    """
    stats = {'etag':0,
             'ccontrol':0,
             'minrl':120,
             'total':0}

    def __init__(self):
        self.http = HttpClient(cache=self.cache, stats=self.stats)

    def _controls_answer(self, ans):
        """Controls answer.
        """
        status = ans.get('response').get('status')
        code = status.get('code')
        if code is 0:
            return True
        if code is 5:
            raise WSNotFound('Artist not found')
        raise WSError(status.get('message'))

    def _forge_payload(self, artist, top=False):
        """Build payload
        """
        payload = {'api_key': ECH.get('apikey')}
        if not isinstance(artist, Artist):
            raise TypeError('"{0!r}" not an Artist object'.format(artist))
        if artist.mbid:
            payload.update(id='musicbrainz:artist:{0}'.format(artist.mbid))
        else:
            payload.update(name=artist.name)
        payload.update(bucket='id:musicbrainz')
        payload.update(results=100)
        if top:
            if artist.mbid:
                aid = payload.pop('id')
                payload.update(artist_id=aid)
            else:
                name = payload.pop('name')
                payload.update(artist=name)
            payload.update(results=100)
            payload.update(sort='song_hotttnesss-desc')
        # > hashing the URL into a cache key
        # return a sorted list of 2-tuple to have consistent cache
        return sorted(payload.items(), key=lambda param: param[0])

    def get_similar(self, artist):
        """Fetch similar artists

        :param sima.lib.meta.Artist artist: `Artist` to fetch similar artists from
        :returns: generator of :class:`sima.lib.meta.Artist`
        """
        payload = self._forge_payload(artist)
        # Construct URL
        ressource = '{0}/artist/similar'.format(SimaEch.root_url)
        ans = self.http(ressource, payload)
        self._controls_answer(ans.json())  # pylint: disable=no-member
        for art in ans.json().get('response').get('artists'):  # pylint: disable=no-member
            mbid = get_mbid(art)
            yield Artist(mbid=mbid, name=art.get('name'))

    def get_toptrack(self, artist):
        """Fetch artist top tracks

        :param sima.lib.meta.Artist artist: `Artist` to fetch top tracks from
        :returns: generator of :class:`sima.lib.track.Track`
        """
        payload = self._forge_payload(artist, top=True)
        # Construct URL
        ressource = '{0}/song/search'.format(SimaEch.root_url)
        ans = self.http(ressource, payload)
        self._controls_answer(ans.json())  # pylint: disable=no-member
        titles = list()
        art = {'artist': artist.name,
               'musicbrainz_artistid': artist.mbid,}
        for song in ans.json().get('response').get('songs'):  # pylint: disable=no-member
            title = song.get('title')
            if not art.get('musicbrainz_artistid'):
                art['musicbrainz_artistid'] = get_mbid(song, 'artist_foreign_ids')
            if title not in titles:
                titles.append(title)
                yield Track(title=title, **art)


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
