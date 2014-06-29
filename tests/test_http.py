# -*- coding: utf-8 -*-

import unittest
import time

from unittest.mock import Mock

from sima.lib.cache import DictCache
from sima.lib.http import CacheController

TIME_FMT = "%a, %d %b %Y %H:%M:%S GMT"


class TestCacheControlRequest(unittest.TestCase):
    url = 'http://foo.com/bar'

    def setUp(self):
        self.c = CacheController(
            DictCache(),
        )

    def req(self, headers):
        return self.c.cached_request(Mock(url=self.url, headers=headers))

    def test_cache_request_no_cache(self):
        resp = self.req({'cache-control': 'no-cache'})
        assert not resp

    def test_cache_request_pragma_no_cache(self):
        resp = self.req({'pragma': 'no-cache'})
        assert not resp

    def test_cache_request_no_store(self):
        resp = self.req({'cache-control': 'no-store'})
        assert not resp

    def test_cache_request_max_age_0(self):
        resp = self.req({'cache-control': 'max-age=0'})
        assert not resp

    def test_cache_request_not_in_cache(self):
        resp = self.req({})
        assert not resp

    def test_cache_request_fresh_max_age(self):
        now = time.strftime(TIME_FMT, time.gmtime())
        resp = Mock(headers={'cache-control': 'max-age=3600',
                             'date': now})

        cache = DictCache({self.url: resp})
        self.c.cache = cache
        r = self.req({})
        assert r == resp

    def test_cache_request_unfresh_max_age(self):
        earlier = time.time() - 3700  # epoch - 1h01m40s
        now = time.strftime(TIME_FMT, time.gmtime(earlier))
        resp = Mock(headers={'cache-control': 'max-age=3600',
                             'date': now})
        self.c.cache = DictCache({self.url: resp})
        r = self.req({})
        assert not r

    def test_cache_request_fresh_expires(self):
        later = time.time() + 86400  # GMT + 1 day
        expires = time.strftime(TIME_FMT, time.gmtime(later))
        now = time.strftime(TIME_FMT, time.gmtime())
        resp = Mock(headers={'expires': expires,
                             'date': now})
        cache = DictCache({self.url: resp})
        self.c.cache = cache
        r = self.req({})
        assert r == resp

    def test_cache_request_unfresh_expires(self):
        sooner = time.time() - 86400  # GMT - 1 day
        expires = time.strftime(TIME_FMT, time.gmtime(sooner))
        now = time.strftime(TIME_FMT, time.gmtime())
        resp = Mock(headers={'expires': expires,
                             'date': now})
        cache = DictCache({self.url: resp})
        self.c.cache = cache
        r = self.req({})
        assert not r

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab

