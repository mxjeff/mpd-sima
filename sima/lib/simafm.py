# -*- coding: utf-8 -*-

# Copyright (c) 2009, 2010, 2011, 2012, 2013, 2014 Jack Kaliko <kaliko@azylum.org>
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
Consume Last.fm web service
"""

__version__ = '0.5.1'
__author__ = 'Jack Kaliko'


from datetime import datetime, timedelta

from requests import Session, Request, Timeout, ConnectionError

from sima import LFM
from sima.lib.meta import Artist

from sima.lib.http import CacheController
from sima.utils.utils import WSError, WSNotFound, WSTimeout, WSHTTPError
from sima.utils.utils import getws, Throttle
if len(LFM.get('apikey')) == 43:  # simple hack allowing imp.reload
    getws(LFM)

# Some definitions
WAIT_BETWEEN_REQUESTS = timedelta(0, 2)
SOCKET_TIMEOUT = 6


class SimaFM:
    """Last.fm http client
    """
    root_url = 'http://{host}/{version}/'.format(**LFM)
    ratelimit = None
    name = 'Last.fm'
    cache = {}

    def __init__(self, cache=True):
        self.controller = CacheController(self.cache)
        self.artist = None

    def _fetch(self, payload):
        """
        Prepare http request
        Use cached elements or proceed http request
        """
        req = Request('GET', SimaFM.root_url, params=payload,
                      ).prepare()
        if self.cache:
            cached_response = self.controller.cached_request(req.url, req.headers)
            if cached_response:
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
        #self.__class__.ratelimit = resp.headers.get('x-ratelimit-remaining', None)
        if resp.status_code is not 200:
            raise WSHTTPError('{0.status_code}: {0.reason}'.format(resp))
        ans = resp.json()
        self._controls_answer(ans)
        if self.cache:
            self.controller.cache_response(resp.request, resp)
        return ans

    def _controls_answer(self, ans):
        """Controls answer.
        """
        if 'error' in ans:
            code = ans.get('error')
            mess = ans.get('message')
            if code == 6:
                raise WSNotFound('{0}: "{1}"'.format(mess, self.artist))
            raise WSError(mess)
        return True

    def _forge_payload(self, artist, method='similar', track=None):
        """Build payload
        """
        payloads = dict({'similar': {'method':'artist.getsimilar',},
                        'top': {'method':'artist.gettoptracks',},
                        'track': {'method':'track.getsimilar',},
                        'info': {'method':'artist.getinfo',},
                        })
        payload = payloads.get(method)
        payload.update(api_key=LFM.get('apikey'), format='json')
        if not isinstance(artist, Artist):
            raise TypeError('"{0!r}" not an Artist object'.format(artist))
        self.artist = artist
        if artist.mbid:
            payload.update(mbid='{0}'.format(artist.mbid))
        else:
            payload.update(artist=artist.name,
                           autocorrect=1)
        payload.update(results=100)
        if method == 'track':
            payload.update(track=track)
        return payload

    def get_similar(self, artist=None):
        """Fetch similar artists
        """
        payload = self._forge_payload(artist)
        # Construct URL
        ans = self._fetch(payload)
        # Artist might be found be return no 'artist' list…
        # cf. "Mulatu Astatqe" vs. "Mulatu Astatqé" with autocorrect=0
        # json format is broken IMHO, xml is more consistent IIRC
        # Here what we got:
        # >>> {"similarartists":{"#text":"\n","artist":"Mulatu Astatqe"}}
        # autocorrect=1 should fix it, checking anyway.
        simarts = ans.get('similarartists').get('artist')
        if not isinstance(simarts, list):
            raise WSError('Artist found but no similarities returned')
        for art in ans.get('similarartists').get('artist'):
            yield Artist(name=art.get('name'), mbid=art.get('mbid', None))


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
