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
Consume EchoNest web service
"""

__version__ = '0.5.0'
__author__ = 'Jack Kaliko'


from datetime import datetime, timedelta

from requests import get, Request, Timeout, ConnectionError

from sima import LFM
from sima.lib.meta import Artist
from sima.utils.utils import WSError, WSNotFound, WSTimeout, WSHTTPError
from sima.utils.utils import getws, Throttle, Cache, purge_cache
if len(LFM.get('apikey')) == 43:  # simple hack allowing imp.reload
    getws(LFM)

# Some definitions
WAIT_BETWEEN_REQUESTS = timedelta(0, 1)
SOCKET_TIMEOUT = 6


class SimaFM():
    """
    """
    root_url = 'http://{host}/{version}/'.format(**LFM)
    cache = {}
    timestamp = datetime.utcnow()
    name = 'Last.fm'
    ratelimit = None

    def __init__(self, cache=True):
        self.artist = None
        self._url = self.__class__.root_url
        self.current_element = None
        self.caching = cache
        purge_cache(self.__class__)

    def _fetch(self, payload):
        """Use cached elements or proceed http request"""
        url = Request('GET', self._url, params=payload,).prepare().url
        if url in SimaFM.cache:
            self.current_element = SimaFM.cache.get(url).elem
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
        req = get(self._url, params=payload,
                            timeout=SOCKET_TIMEOUT)
        #self.__class__.ratelimit = req.headers.get('x-ratelimit-remaining', None)
        if req.status_code is not 200:
            raise WSHTTPError(req.status_code)
        self.current_element = req.json()
        self._controls_answer()
        if self.caching:
            SimaFM.cache.update({req.url:
                                 Cache(self.current_element)})

    def _controls_answer(self):
        """Controls answer.
        """
        if 'error' in self.current_element:
            code = self.current_element.get('error')
            mess = self.current_element.get('message')
            if code == 6:
                raise WSNotFound('{0}: "{1}"'.format(mess, self.artist))
            raise WSError(mess)
        return True

    def _forge_payload(self, artist, method='similar', track=None):
        """
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
           payload.update(artist=artist.name)
        payload.update(results=100)
        if method == 'track':
            payload.update(track=track)
        return payload

    def get_similar(self, artist=None):
        """
        """
        payload = self._forge_payload(artist)
        # Construct URL
        self._fetch(payload)
        for art in self.current_element.get('similarartists').get('artist'):
            yield Artist(name=art.get('name'), mbid=art.get('mbid', None))


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
