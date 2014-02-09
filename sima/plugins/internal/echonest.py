# -*- coding: utf-8 -*-
"""
Fetching similar artists from echonest web services
"""

# standard library import

# third parties components

# local import
from ...lib.simaecho import SimaEch
from ...lib.webservice import WebService


class EchoNest(WebService):
    """last.fm similar artists
    """

    def __init__(self, daemon):
        WebService.__init__(self, daemon)
        self.ws = SimaEch

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
