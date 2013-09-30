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

"""
SimaStr

Special unicode() subclass to perform fuzzy match on specific strings with
known noise.

Artist names often contain a leading 'The ' which might, or might not be
present. Some other noise sources in artist name are 'and' words :
    'and'/'&'/'n'/'N'.

The SimaStr() object removes these words and compute equality on "stripped"
strings.

>>> from simastr import SimaStr
>>> art0 = SimaStr('The Desert Sessions & PJ Harvey')
>>> art1 = SimaStr('Desert Sessions And PJ Harvey')
>>> art0 == art1
>>> True
>>> art0 == 'Desert Sessions And PJ Harvey'
>>> True
>>>

Current stripped word patterns (usually English followed by French andx
Spanish alternatives)
    leading (case-insensitive):
            "the","le","la","les","el","los"
    middle:
            "[Aa]nd","&","[Nn]'?","[Ee]t"
    trailing:
            combination of "[- !?\.]+" "\(? ?[Ll]ive ?\)?"


Possibility to access to stripped string :

>>> art0 = SimaStr('The Desert Sessions & PJ Harvey')
>>> art.stripped
>>> print (art0, art0.stripped)
>>> ('The Desert Sessions & PJ Harvey', 'Desert Sessions PJ Harvey')

TODO:
    * Have a look to difflib.SequenceMatcher to find possible improvements
    * Find a way to allow users patterns.
"""

__author__ = 'Jack Kaliko'
__version__ = '0.3'

# IMPORTS
from re import (compile, U, I)


class SimaStr(str):
    """
    Specific string object for artist names and song titles.
    Here follows some class variables for regex to run on strings.
    """
    regexp_dict = dict()

    # Leading patterns: The Le Les
    # case-insensitive matching for this RE
    regexp_dict.update({'lead': '(the|l[ae][s]?|los|el)'})

    # Middle patterns: And & Et N
    regexp_dict.update({'mid': '(And|&|and|[Nn]\'?|et)'})

    # Trailing patterns: ! ? live
    # TODO: add "concert" key word
    #       add "Live at <somewhere>"
    regexp_dict.update({'trail': '([- !?\.]|\(? ?[Ll]ive ?\)?)'})

    reg_lead = compile('^(?P<lead>%(lead)s )(?P<root0>.*)$' % regexp_dict, I | U)
    reg_midl = compile('^(?P<root0>.*)(?P<mid> %(mid)s )(?P<root1>.*)' % regexp_dict, U)
    reg_trail = compile('^(?P<root0>.*?)(?P<trail>%(trail)s+$)' % regexp_dict, U)

    def __init__(self, fuzzstr):
        """
        """
        str().__init__(fuzzstr)
        self.orig = str(fuzzstr)
        self.stripped = str(fuzzstr.strip())
        # fuzzy computation
        self._get_root()

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

    def __hash__(self):
        return hash(self.stripped)

    def __eq__(self, other):
        if not isinstance(other, SimaStr):
            return hash(self) == hash(SimaStr(other))
        return hash(self) == hash(other)

    def __ne__(self, other):
        if not isinstance(other, SimaStr):
            return hash(self) != hash(SimaStr(other))
        return hash(self) != hash(other)


# Script starts here
if __name__ == "__main__":
    import time
    print(SimaStr('Kétanoue'))
    #from leven import levenshtein_ratio
    CASES_LIST = list([
        dict({
                    'got': 'Guns N\' Roses (live)!! !',
                'look for': 'Guns And Roses'}),
        dict({
                     'got': 'Jesus & Mary Chains',
                'look for': 'The Jesus and Mary Chains - live'}),
        dict({
                         'got': 'Desert sessions',
                    'look for': 'The Desert Sessions'}),
        dict({
                         'got': 'Têtes Raides',
                    'look for': 'Les Têtes Raides'}),
        dict({
                         'got': 'Noir Désir',
                    'look for': 'Noir Désir'}),
        dict({
                         'got': 'No Future',
                    'look for': 'Future'})])

    for case in CASES_LIST[:]:
        str0 = case.get('got')
        str1 = case.get('look for')
        fz_str0 = SimaStr(str0)
        fz_str1 = SimaStr(str1)
        print(fz_str0, '\n', fz_str1)
        print(fz_str0.stripped == fz_str1.stripped)
        #print levenshtein_ratio(fz_str0.lower(), fz_str1.lower())
        time.sleep(1)

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
