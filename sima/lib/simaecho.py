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

__version__ = '0.0.1'
__author__ = 'Jack Kaliko'


from datetime import datetime, timedelta

from requests import get, Request, Timeout, ConnectionError

from sima import ECH
from sima.lib.meta import Artist
from sima.utils.utils import WSError, WSNotFound, WSTimeout, WSHTTPError
from sima.utils.utils import getws, Throttle, Cache, purge_cache
if len(ECH.get('apikey')) == 23:  # simple hack allowing imp.reload
    getws(ECH)

# Some definitions
WAIT_BETWEEN_REQUESTS = timedelta(0, 1)
SOCKET_TIMEOUT = 4


class SimaEch:
    """EchoNest http client
    """
    root_url = 'http://{host}/api/{version}'.format(**ECH)
    cache = {}
    timestamp = datetime.utcnow()
    ratelimit = None
    name = 'EchoNest'

    def __init__(self, cache=True):
        self.artist = None
        self._ressource = None
        self.current_element = None
        self.caching = cache
        purge_cache(self.__class__)

    def _fetch(self, payload):
        """Use cached elements or proceed http request"""
        url = Request('GET', self._ressource, params=payload,).prepare().url
        if url in SimaEch.cache:
            self.current_element = SimaEch.cache.get(url).elem
            return
        try:
            self._fetch_ws(payload)
        except Timeout:
            raise WSTimeout('Failed to reach server within {0}s'.format(
                               SOCKET_TIMEOUT))
        except ConnectionError as err:
            raise WSError(err)

    @Throttle(WAIT_BETWEEN_REQUESTS)
    def _fetch_ws(self, payload):
        """fetch from web service"""
        req = get(self._ressource, params=payload,
                            timeout=SOCKET_TIMEOUT)
        self.__class__.ratelimit = req.headers.get('x-ratelimit-remaining', None)
        if req.status_code is not 200:
            raise WSHTTPError(req.status_code)
        self.current_element = req.json()
        self._controls_answer()
        if self.caching:
            SimaEch.cache.update({req.url:
                                 Cache(self.current_element)})

    def _controls_answer(self):
        """Controls answer.
        """
        status = self.current_element.get('response').get('status')
        code = status.get('code')
        if code is 0:
            return True
        if code is 5:
            raise WSNotFound('Artist not found: "{0}"'.format(self.artist))
        raise WSError(status.get('message'))

    def _forge_payload(self, artist):
        """Build payload
        """
        payload = {'api_key': ECH.get('apikey')}
        if not isinstance(artist, Artist):
            raise TypeError('"{0!r}" not an Artist object'.format(artist))
        self.artist = artist
        if artist.mbid:
            payload.update(
                    id='musicbrainz:artist:{0}'.format(artist.mbid))
        else:
            payload.update(name=artist.name)
        payload.update(bucket='id:musicbrainz')
        payload.update(results=100)
        return payload

    def get_similar(self, artist=None):
        """Fetch similar artists
        """
        payload = self._forge_payload(artist)
        # Construct URL
        self._ressource = '{0}/artist/similar'.format(SimaEch.root_url)
        self._fetch(payload)
        for art in self.current_element.get('response').get('artists'):
            artist = {}
            mbid = None
            if 'foreign_ids' in art:
                for frgnid in art.get('foreign_ids'):
                    if frgnid.get('catalog') == 'musicbrainz':
                        mbid = frgnid.get('foreign_id'
                                          ).lstrip('musicbrainz:artist:')
            yield Artist(mbid=mbid, name=art.get('name'))


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
