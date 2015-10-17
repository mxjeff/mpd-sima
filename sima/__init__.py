# -*- coding: utf-8 -*-
"""WebServices API credentials and ressources
"""
from datetime import timedelta

LFM = {'apikey': 'NG4xcDlxcXJwMjk4MTZycTgwM3E3b3I5MTEzb240cG8',
       'host':'ws.audioscrobbler.com',
       'version': '2.0',}

ECH = {'apikey': 'WlRKQkhTS0JHWFVDUEZZRFA',
       'host': 'developer.echonest.com',
       'version': 'v4',}

WAIT_BETWEEN_REQUESTS = timedelta(days=0, seconds=2)
SOCKET_TIMEOUT = 6

# vim: ai ts=4 sw=4 sts=4 expandtab
