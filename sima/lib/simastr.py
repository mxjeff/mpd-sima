# -*- coding: utf-8 -*-
#
# Copyright (c) 2009, 2010, 2013 Jack Kaliko <kaliko@azylum.org>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as
#  published by the Free Software Foundation; either version 3 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful, but
#  WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with this program.
#  If not, see <http://www.gnu.org/licenses/>.
#

r"""
SimaStr

Special unicode() subclass to perform fuzzy match on specific strings with
known noise.

 * SimaStr() object removes specific patterns from the string
 * Diacritic are removed
 * Equality test is done on lower-cased string
 * Equality test is not an exact comparison, the levenshtein edition distance
   between stripped and filtered strings is used

>>> from simastr import SimaStr
>>> art0 = SimaStr('The Desert Sessions & PJ Harvey')
>>> art1 = SimaStr('Desert Sessions And PJ Harvey')
>>> art0 == art1
>>> True
>>> art0 == 'Desert Sessions And PJ Harvey'
>>> True
>>> # diacritic filter + levenshtein  example
>>> art0 = sima.lib.simastr.SimaStr('Hubert Félix Thiéphaine')
>>> art1 = sima.lib.simastr.SimaStr('Hubert-Felix Thiephaine')
>>> art0 == art1
>>> True
>>>

Current stripped word patterns (usually English followed by French and
Spanish alternatives)
    leading (case-insensitive):
            "the","le","la","les","el","los"
    middle:
            "[Aa]nd","&","[Nn]'?","[Ee]t"
    trailing:
            combination of "[- !?\.]+" "\(? ?[Ll]ive ?\)?"


Possibility to access to stripped string:

>>> art0 = SimaStr('The Desert Sessions & PJ Harvey')
>>> print (art0, art0.stripped)
>>> ('The Desert Sessions & PJ Harvey', 'Desert Sessions PJ Harvey')

TODO:
    * Have a look to difflib.SequenceMatcher to find possible improvements
    * Find a way to allow users patterns.
"""

__author__ = 'Jack Kaliko'
__version__ = '0.4'

# IMPORTS
import unicodedata
from re import compile as re_compile, U, I

from ..utils.leven import levenshtein_ratio


class SimaStr(str):
    """
    Specific string object for artist names and song titles.
    Here follows some class variables for regex to run on strings.
    """
    diafilter = True
    leven_ratio = 0.82
    regexp_dict = dict()

    # Leading patterns: The Le Les
    # case-insensitive matching for this RE
    regexp_dict.update({'lead': '(the|l[ae][s]?|los|el)'})

    # Middle patterns: And & Et N
    regexp_dict.update({'mid': '(And|&|and|[Nn]\'?|et)'})

    # Trailing patterns: ! ? live
    # TODO: add "concert" key word
    #       add "Live at <somewhere>"
    regexp_dict.update({'trail': r'([- !?\.]|\(? ?[Ll]ive ?\)?)'})

    reg_lead = re_compile('^(?P<lead>%(lead)s )(?P<root0>.*)$' % regexp_dict, I | U)
    reg_midl = re_compile('^(?P<root0>.*)(?P<mid> %(mid)s )(?P<root1>.*)' % regexp_dict, U)
    reg_trail = re_compile('^(?P<root0>.*?)(?P<trail>%(trail)s+$)' % regexp_dict, U)

    def __init__(self, fuzzstr):
        """
        """
        self.orig = str(fuzzstr)
        self.stripped = str(fuzzstr.strip())
        # fuzzy computation
        self._get_root()
        if self.__class__.diafilter:
            self.remove_diacritics()

    def __new__(cls, fuzzstr):
        return super(SimaStr, cls).__new__(cls, fuzzstr)

    def _get_root(self):
        """
        Remove all patterns in string.
        """
        sea = SimaStr.reg_lead.search(self.stripped)
        if sea:
            #print sea.groupdict()
            self.stripped = sea.group('root0')

        sea = SimaStr.reg_midl.search(self.stripped)
        if sea:
            #print sea.groupdict()
            self.stripped = str().join([sea.group('root0'), ' ',
                                        sea.group('root1')])

        sea = SimaStr.reg_trail.search(self.stripped)
        if sea:
            #print sea.groupdict()
            self.stripped = sea.group('root0')

    def remove_diacritics(self):
        """converting diacritics"""
        self.stripped = ''.join(x for x in
                                unicodedata.normalize('NFKD', self.stripped)
                                if unicodedata.category(x) != 'Mn')

    def __hash__(self):
        return hash(self.stripped)

    def __eq__(self, other):
        if not isinstance(other, SimaStr):
            other = SimaStr(other)
        levenr = levenshtein_ratio(self.stripped.lower(),
                                   other.stripped.lower())
        if hash(self) == hash(other):
            return True
        return levenr >= self.__class__.leven_ratio

    def __ne__(self, other):
        if not isinstance(other, SimaStr):
            return hash(self) != hash(SimaStr(other))
        return hash(self) != hash(other)


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
