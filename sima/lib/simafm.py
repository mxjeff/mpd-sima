# -*- coding: utf-8 -*-

# Copyright (c) 2009, 2010, 2011, 2012, 2013 Jack Kaliko <kaliko@azylum.org>
# Copyright (c) 2010 Eric Casteleijn <thisfred@gmail.com> (Throttle decorator)
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
Consume last.fm web service

"""

__version__ = '0.3.1'
__author__ = 'Jack Kaliko'


import urllib.request, urllib.error, urllib.parse

from datetime import datetime, timedelta
from http.client import BadStatusLine
from socket import timeout as SocketTimeOut
from time import sleep
from xml.etree.cElementTree import ElementTree

from sima import LFM
from sima.utils.utils import getws
getws(LFM)

# Some definitions
WAIT_BETWEEN_REQUESTS = timedelta(0, 0.4)
LFM_ERRORS = dict({'2': 'Invalid service -This service does not exist',
    '3': 'Invalid Method - No method with that name in this package',
    '4': 'Authentication Failed - You do not have permissions to access the service',
    '5': "'Invalid format - This service doesn't exist in that format",
    '6': 'Invalid parameters - Your request is missing a required parameter',
    '7': 'Invalid resource specified',
    '9': 'Invalid session key - Please re-authenticate',
    '10': 'Invalid API key - You must be granted a valid key by last.fm',
    '11': 'Service Offline - This service is temporarily offline. Try again later.',
    '12': 'Subscription Error - The user needs to be subscribed in order to do that',
    '13': 'Invalid method signature supplied',
    '26': 'Suspended API key - Access for your account has been suspended, please contact Last.fm',
    })


class XmlFMError(Exception):  # Errors
    """
    Exception raised for errors in the input.
    """

    def __init__(self, expression):
        self.expression = expression

    def __str__(self):
        return repr(self.expression)


class EncodingError(XmlFMError):
    """Raised when string is not unicode"""
    pass


class XmlFMHTTPError(XmlFMError):
    """Raised when failed to connect server"""

    def __init__(self, expression):
        if hasattr(expression, 'code'):
            self.expression = 'error %d: %s' % (expression.code,
                expression.msg)
        else:
            self.expression = 'error: %s' % expression


class XmlFMNotFound(XmlFMError):
    """Raised when no artist is found"""

    def __init__(self, message=None):
        if not message:
            message = 'Artist probably not found (http error 400)'
        self.expression = (message)


class XmlFMMissingArtist(XmlFMError):
    """Raised when no artist name provided"""

    def __init__(self, message=None):
        if not message:
            message = 'Missing artist name.'
        self.expression = (message)


class XmlFMTimeOut(XmlFMError):
    """Raised when urlopen times out"""

    def __init__(self, message=None):
        if not message:
            message = 'Connection to last.fm web services times out!'
        self.expression = (message)


class Throttle():
    def __init__(self, wait):
        self.wait = wait
        self.last_called = datetime.now()

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            while self.last_called + self.wait > datetime.now():
                #print('waiting…')
                sleep(0.1)
            result = func(*args, **kwargs)
            self.last_called = datetime.now()
            return result
        return wrapper


class AudioScrobblerCache():
    def __init__(self, elem, last):
        self.elemtree = elem
        self.requestdate = last

    def created(self):
        return self.requestdate

    def gettree(self):
        return self.elemtree


class SimaFM():
    """
    """
    root_url = 'http://{host}/{version}/'.format(**LFM)
    request = dict({'similar': '?method=artist.getsimilar&artist=%s&' +\
                                'api_key={apikey}'.format(**LFM),
                    'top': '?method=artist.gettoptracks&artist=%s&' +\
                                'api_key={apikey}'.format(**LFM),
                    'track': '?method=track.getsimilar&artist=%s' +\
                            '&track=%s' + 'api_key={apikey}'.format(**LFM),
                    'info': '?method=artist.getinfo&artist=%s' +\
                            'api_key={apikey}'.format(**LFM),
                    })
    cache = dict({})
    timestamp = datetime.utcnow()
    count = 0

    def __init__(self, artist=None, cache=True):
        self._url = None
        #SimaFM.count += 1
        self.current_element = None
        self.caching = cache
        self.purge_cache()

    def _is_in_cache(self):
        """Controls presence of url in cache.
        """
        if self._url in SimaFM.cache:
            #print('already fetch {0}'.format(self.artist))
            return True
        return False

    def _fetch(self):
        """Use cached elements or proceed http request"""
        if self._is_in_cache():
            self.current_element = SimaFM.cache.get(self._url).gettree()
            return
        self._fetch_lfm()

    @Throttle(WAIT_BETWEEN_REQUESTS)
    def _fetch_lfm(self):
        """Get artists, fetch xml from last.fm"""
        try:
            fd = urllib.request.urlopen(url=self._url,
                    timeout=15)
        except SocketTimeOut:
            raise XmlFMTimeOut()
        except BadStatusLine as err:
            raise XmlFMHTTPError(err)
        except urllib.error.URLError as err:
            if hasattr(err, 'reason'):
                # URLError, failed to reach server
                raise XmlFMError(repr(err.reason))
            if hasattr(err, 'code'):
                # HTTPError, the server couldn't fulfill the request
                if err.code == 400:
                    raise XmlFMNotFound()
                raise XmlFMHTTPError(err)
            raise XmlFMError(err)
        headers = dict(fd.getheaders())
        content_type = headers.get('Content-Type').split(';')
        if content_type[0] != "text/xml":
            raise XmlFMError('None XML returned from the server')
        if content_type[1].strip() != "charset=utf-8":
            raise XmlFMError('XML not UTF-8 encoded!')
        try:
            self.current_element = ElementTree(file=fd)
        except SocketTimeOut:
            raise XmlFMTimeOut()
        finally:
            fd.close()
        self._controls_lfm_answer()
        if self.caching:
            SimaFM.cache[self._url] = AudioScrobblerCache(self.current_element,
                    datetime.utcnow())

    def _controls_lfm_answer(self):
        """Controls last.fm answer.
        """
        status = self.current_element.getroot().attrib.get('status')
        if status == 'ok':
            return True
        if status == 'failed':
            error = self.current_element.find('error').attrib.get('code')
            errormsg = self.current_element.findtext('error')
            #if error in LFM_ERRORS.keys():
            #    print LFM_ERRORS.get(error)
            raise XmlFMNotFound(errormsg)

    def _controls_artist(self, artist):
        """
        """
        self.artist = artist
        if not self.artist:
            raise XmlFMMissingArtist('Missing artist name calling SimaFM.get_<method>()')
        if not isinstance(self.artist, str):
            raise EncodingError('"%s" not unicode object' % self.artist)
        # last.fm is UTF-8 encoded URL
        self.artist_utf8 = self.artist.encode('UTF-8')

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
        url = SimaFM.root_url + SimaFM.request.get('similar')
        self._url = url % (urllib.parse.quote(self.artist_utf8, safe=''))
        self._fetch()
        # TODO: controls name encoding
        elem = self.current_element
        for art in elem.getiterator(tag='artist'):
            yield str(art.findtext('name')), 100 * float(art.findtext('match'))

    def get_toptracks(self, artist=None):
        """
        """
        self._controls_artist(artist)
        # Construct URL
        url = SimaFM.root_url + SimaFM.request.get('top')
        self._url = url % (urllib.parse.quote(self.artist_utf8, safe=''))
        self._fetch()
        # TODO: controls name encoding
        elem = self.current_element
        for track in elem.getiterator(tag='track'):
            yield str(track.findtext('name')), int(track.attrib.get('rank'))

    def get_similartracks(self, track=None, artist=None):
        """
        """
        # Construct URL
        url = SimaFM.root_url + SimaFM.request.get('track')
        self._url = url % (urllib.parse.quote(artist.encode('UTF-8'), safe=''),
                           urllib.parse.quote(track.encode('UTF-8'), safe=''))
        self._fetch()
        elem = self.current_element
        for trk in elem.getiterator(tag='track'):
            yield (str(trk.findtext('artist/name')),
                   str(trk.findtext('name')),
                   100 * float(trk.findtext('match')))

    def get_mbid(self, artist=None):
        """
        """
        self._controls_artist(artist)
        # Construct URL
        url = SimaFM.root_url + SimaFM.request.get('info')
        self._url = url % (urllib.parse.quote(self.artist_utf8, safe=''))
        self._fetch()
        # TODO: controls name encoding
        elem = self.current_element
        return str(elem.find('artist').findtext('mbid'))


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
