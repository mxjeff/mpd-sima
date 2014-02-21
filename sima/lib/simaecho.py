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

__version__ = '0.0.2'
__author__ = 'Jack Kaliko'


from datetime import timedelta

from requests import Session, Request, Timeout, ConnectionError

from sima import ECH
from sima.lib.meta import Artist
from sima.lib.track import Track
from sima.lib.http import CacheController
from sima.utils.utils import WSError, WSNotFound, WSTimeout, WSHTTPError
from sima.utils.utils import getws, Throttle
if len(ECH.get('apikey')) == 23:  # simple hack allowing imp.reload
    getws(ECH)

# Some definitions
WAIT_BETWEEN_REQUESTS = timedelta(0, 2)
SOCKET_TIMEOUT = 6


class SimaEch:
    """EchoNest http client
    """
    root_url = 'http://{host}/api/{version}'.format(**ECH)
    ratelimit = None
    name = 'EchoNest'
    cache = False
    stats = {'304':0, 'cached':0, 'minrl':'120'}

    def __init__(self):
        self.controller = CacheController(self.cache)

    def _fetch(self, ressource, payload):
        """
        Prepare http request
        Use cached elements or proceed http request
        """
        req = Request('GET', ressource, params=payload,
                      ).prepare()
        if self.cache:
            cached_response = self.controller.cached_request(req.url, req.headers)
            if cached_response:
                SimaEch.stat.update(cached=SimaEch.stat.get('cached')+1)
                return cached_response.json()
        try:
            return self._fetch_ws(req)
        except Timeout:
            raise WSTimeout('Failed to reach server within {0}s'.format(
                               SOCKET_TIMEOUT))
        except ConnectionError as err:
            raise WSError(err)

    @Throttle(WAIT_BETWEEN_REQUESTS)
    def _fetch_ws(self, prepreq):
        """fetch from web service"""
        sess = Session()
        resp = sess.send(prepreq, timeout=SOCKET_TIMEOUT)
        if resp.status_code == 304:
            SimaEch.stats.update({'304':SimaEch.stats.get('304')+1})
            resp = self.controller.update_cached_response(prepreq, resp)
        elif resp.status_code != 200:
            raise WSHTTPError('{0.status_code}: {0.reason}'.format(resp))
        ans = resp.json()
        self._controls_answer(ans)
        SimaEch.ratelimit = resp.headers.get('x-ratelimit-remaining', None)
        minrl = min(SimaEch.ratelimit, SimaEch.stats.get('minrl'))
        SimaEch.stats.update(minrl=minrl)
        if self.cache:
            self.controller.cache_response(resp.request, resp)
        return ans

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
            payload.update(
                    id='musicbrainz:artist:{0}'.format(artist.mbid))
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
        return payload

    def get_similar(self, artist=None):
        """Fetch similar artists
        """
        payload = self._forge_payload(artist)
        # Construct URL
        ressource = '{0}/artist/similar'.format(SimaEch.root_url)
        ans = self._fetch(ressource, payload)
        for art in ans.get('response').get('artists'):
            mbid = None
            if 'foreign_ids' in art:
                for frgnid in art.get('foreign_ids'):
                    if frgnid.get('catalog') == 'musicbrainz':
                        mbid = frgnid.get('foreign_id'
                                          ).lstrip('musicbrainz:artist:')
            yield Artist(mbid=mbid, name=art.get('name'))

    def get_toptrack(self, artist=None):
        """Fetch artist top tracks
        """
        payload = self._forge_payload(artist, top=True)
        # Construct URL
        ressource = '{0}/song/search'.format(SimaEch.root_url)
        ans = self._fetch(ressource, payload)
        titles = list()
        art = {
                'artist': artist.name,
                'musicbrainz_artistid': artist.mbid,
                }
        for song in ans.get('response').get('songs'):
            title = song.get('title')
            if title not in titles:
                titles.append(title)
                yield Track(title=title, **art)


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
