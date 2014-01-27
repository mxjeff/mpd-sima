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


import urllib.request, urllib.error, urllib.parse

from datetime import datetime, timedelta
from socket import timeout as SocketTimeOut
from time import sleep

from requests import get

from sima import ECH
from sima.lib.meta import Artist
from sima.utils.utils import getws
if len(ECH.get('apikey')) == 23:
    getws(ECH)

# Some definitions
WAIT_BETWEEN_REQUESTS = timedelta(0, 0.4)


class SimaEchoError(Exception):
    pass

class Throttle():
    def __init__(self, wait):
        self.wait = wait
        self.last_called = datetime.now()

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            while self.last_called + self.wait > datetime.now():
                sleep(0.1)
            result = func(*args, **kwargs)
            self.last_called = datetime.now()
            return result
        return wrapper


class Cache():
    def __init__(self, elem, last=None):
        self.elem = elem
        self.requestdate = last
        if not last:
            self.requestdate = datetime.utcnow()

    def created(self):
        return self.requestdate

    def get(self):
        return self.elem


class SimaFM():
    """
    """
    root_url = 'http://{host}/api/{version}'.format(**ECH)
    cache = dict({})
    timestamp = datetime.utcnow()

    def __init__(self, cache=True):
        self._ressource = None
        self._payload = {'api_key': ECH.get('apikey')}
        self.current_element = None
        self.caching = cache
        self.purge_cache()

    def _fetch(self):
        """Use cached elements or proceed http request"""
        self._req = get(self._ressource, params=self._payload, timeout=5)
        if self._req.url in SimaFM.cache:
            print('got from SimaFM cache')
            self.current_element = SimaFM.cache.get(self._req.url).get()
            return
        self._fetch_lfm()

    @Throttle(WAIT_BETWEEN_REQUESTS)
    def _fetch_lfm(self):
        """fetch from web service"""
        if self._req.status_code is not 200:
            raise SimaEchoError(self._req.status_code)
        self.current_element = self._req.json()
        self._controls_lfm_answer()
        if self.caching:
            SimaFM.cache.update({self._req.url:
                                 Cache(self.current_element)})

    def _controls_lfm_answer(self):
        """Controls last.fm answer.
        """
        status = self.current_element.get('response').get('status')
        if status.get('code') is 0:
            return True
        raise SimaEchoError(status.get('message'))

    def _controls_artist(self, artist):
        """
        """
        if not isinstance(artist, Artist):
            raise TypeError('"{0!r}" not an Artist object'.format(artist))
        self.artist = artist
        if artist.mbid:
            self._payload.update(
                    id='musicbrainz:artist:{0}'.format(artist.mbid))
        else:
           self._payload.update(name=artist.name)
        self._payload.update(bucket='id:musicbrainz')
        self._payload.update(results=30)

    def purge_cache(self, age=4):
        now = datetime.utcnow()
        if now.hour == SimaFM.timestamp.hour:
            return
        SimaFM.timestamp = datetime.utcnow()
        cache = SimaFM.cache
        delta = timedelta(hours=age)
        for url in list(cache.keys()):
            timestamp = cache.get(url).created()
            if now - timestamp > delta:
                cache.pop(url)

    def get_similar(self, artist=None):
        """
        """
        self._controls_artist(artist)
        # Construct URL
        self._ressource = '{0}/artist/similar'.format(SimaFM.root_url)
        self._fetch()
        for art in self.current_element.get('response').get('artists'):
            artist = {}
            mbid = None
            if 'foreign_ids' in art:
               for frgnid in art.get('foreign_ids'):
                   if frgnid.get('catalog') == 'musicbrainz':
                       mbid = frgnid.get('foreign_id').lstrip('musicbrainz:artist:')
            yield Artist(mbid=mbid, name=art.get('name'))


def run():
    test = SimaFM()
    for t, a, m in test.get_similartracks(artist='Nirvana', track='Smells Like Teen Spirit'):
        print(a, t, m)
    return

if __name__ == '__main__':
    try:
        run()
    except XmlFMHTTPError as conn_err:
        print("error trying to connect: %s" % conn_err)
    except XmlFMNotFound as not_found:
        print("looks like no artists were found: %s" % not_found)
    except XmlFMError as err:
        print(err)


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
