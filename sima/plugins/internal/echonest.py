# -*- coding: utf-8 -*-
# Copyright (c) 2013, 2014 Jack Kaliko <kaliko@azylum.org>
#
#  This file is part of sima
#
#  sima is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  sima is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with sima.  If not, see <http://www.gnu.org/licenses/>.
#
#
"""
Fetching similar artists from echonest web services
"""

# standard library import

# third parties components

# local import
from ...lib.simaecho import SimaEch
from ...lib.webserv import WebService


class EchoNest(WebService):
    """last.fm similar artists
    """

    def __init__(self, daemon):
        WebService.__init__(self, daemon)
        self.ws = SimaEch

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
