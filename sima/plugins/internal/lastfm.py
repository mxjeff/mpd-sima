# -*- coding: utf-8 -*-
"""
Fetching similar artists from last.fm web services
"""

# standard library import

# third parties components

# local import
from ...lib.simafm import SimaFM
from ...lib.webservice import WebService


class Lastfm(WebService):
    """last.fm similar artists
    """

    def __init__(self, daemon):
        WebService.__init__(self, daemon)
        self.ws = SimaFM


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
