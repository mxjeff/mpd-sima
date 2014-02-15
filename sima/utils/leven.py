# -*- coding: utf-8 -*-
# Copyright (c) 2009, 2010, 2013 Jack Kaliko <kaliko@azylum.org>
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
"""Computes levenshtein distance/ratio"""

def levenshtein(a_st, b_st):
    """Computes the Levenshtein distance between two strings."""
    n_a, m_b = len(a_st), len(b_st)
    if n_a > m_b:
        # Make sure n <= m, to use O(min(n_a,m_b)) space
        a_st, b_st = b_st, a_st
        n_a, m_b = m_b, n_a

    current = list(range(n_a+1))
    for i in range(1, m_b+1):
        previous, current = current, [i]+[0]*n_a
        for j in range(1, n_a+1):
            add, delete = previous[j] + 1, current[j-1] + 1
            change = previous[j-1]
            if a_st[j-1] != b_st[i-1]:
                change = change + 1
            current[j] = min(add, delete, change)

    return current[n_a]

def levenshtein_ratio(string, strong):
    """
    Compute levenshtein ratio.
        Ratio = levenshtein distance / lenght of longer string
    The longer string length is the upper bound of levenshtein distance.
    """
    lev_dist = levenshtein(string, strong)
    max_len = max(len(string), len(strong))
    ratio = 1 - (float(lev_dist) / float(max_len))
    return ratio


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
