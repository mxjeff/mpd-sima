# -*- coding: utf-8 -*-

import unittest

from sima.lib.meta import Meta, Artist, is_uuid4
from sima.lib.meta import WrongUUID4, MetaException

VALID = '110E8100-E29B-41D1-A716-116655250000'

class TestMetaObject(unittest.TestCase):

    def test_uuid_integrity(self):
        Meta(mbid=VALID, name='test')
        Meta(mbid=VALID.lower(), name='test')
        wrong = VALID +'a'
        self.assertRaises(WrongUUID4, is_uuid4, wrong)
        #  test UUID4 format validation
        self.assertRaises(WrongUUID4, is_uuid4, VALID.replace('4', '3'))
        self.assertRaises(WrongUUID4, is_uuid4, VALID.replace('A', 'Z'))

    def test_init(self):
        for args in [
                {'mbid':VALID},
                {'name': None},
                {},
                ]:
            with self.assertRaises(MetaException,
                                   msg='{} does not raise an except.'.format(args)):
                Meta(**args)

    def test_equality(self):
        a = Meta(mbid=VALID, name='a')
        b = Meta(mbid=VALID, name='b')
        self.assertEqual(a, b)

    def test_hash(self):
        a = Meta(mbid=VALID, name='a')
        b = Meta(mbid=VALID, name='b')
        c = Meta(mbid=VALID, name='c')
        self.assertTrue(len({a,b,c}) == 1)
        self.assertTrue(a in [c, b])
        self.assertTrue(a in {c, b})
        # mbid is immutable
        self.assertRaises(AttributeError, a.__setattr__, 'mbid', VALID)

    def test_identity(self):
        a = Meta(mbid=VALID, name='a')
        b = Meta(mbid=VALID, name='a')
        self.assertTrue(a is not b)

    def test_aliases(self):
        art0 = Meta(name='Silver Mt. Zion')
        art0.add_alias('A Silver Mt. Zion')
        art0.add_alias(art0)

        # Controls 'Silver Mt. Zion' is not in aliases
        self.assertTrue('Silver Mt. Zion' not in art0.aliases)

        # test equality str with Obj.__aliases
        self.assertTrue(art0 == 'A Silver Mt. Zion')
        self.assertTrue('A Silver Mt. Zion' == art0)
        # test equality Obj.__name with OgjBis.__aliases
        self.assertTrue(art0 == Meta(name='A Silver Mt. Zion'))

    def test_union(self):
        art00 = Meta(name='Aphex Twin',
                           mbid='f22942a1-6f70-4f48-866e-238cb2308fbd')
        art02 = Meta(name='Some Other Name not even close, avoid fuzzy match',
                           mbid='f22942a1-6f70-4f48-866e-238cb2308fbd')

        self.assertTrue(len({art00, art02}) == 1)
        art00._Meta__name = art02._Meta__name = 'Aphex Twin'
        self.assertTrue(len({art00, art02}) == 1)

        # >>> len({Artist(name='Name'), Artist(name='Name', mbid=<UUID4>)}) == 2
        art00._Meta__mbid = None
        self.assertTrue(len({art00, art02}) == 2,
                        'wrong: hash({!r}) == hash({!r})'.format(art00, art02))
        # equivalent: self.assertTrue(hash(art00) != hash(art02))

        # >>> len({Artist(name='Name'), Artist(name='Name')}) == 1
        art00._Meta__mbid = art02._Meta__mbid = None
        # equivalent: self.assertTrue(hash(art00) == hash(art02))
        self.assertTrue(len({art00, art02}) == 1,
                        'wrong: hash({!r}) != hash({!r})'.format(art00, art02))

    def test_comparison(self):
        art00 = Meta(name='Aphex Twin',
                     mbid='f22942a1-6f70-4f48-866e-238cb2308fbd')
        art01 = Meta(name='Aphex Twin',)
        art02 = Meta(name='Some Other Name not even close, avoid fuzzy match',
                     mbid='f22942a1-6f70-4f48-866e-238cb2308fbd')
        art10 = Meta(name='Aphex Twin',
                     mbid='d22942a1-6f70-4f48-866e-238cb2308fbd')
        # testing name/mbid == name/None
        self.assertTrue(art00 == art01, 'wrong: %r != %r' % (art00, art01))
        # testing name/mbid == other_name/mbid
        self.assertTrue(art00 == art02, 'wrong: %r != %r' % (art00, art02))
        #  testing name/mbid != name/other_mbid
        self.assertTrue(art00 != art10, 'wrong: %r == %r' % (art00, art10))
        # Testing name/None == name/None
        art10._Meta__mbid = None
        self.assertTrue(art01 == art10, 'wrong: %r != %r' % (art00, art01))


class TestArtistObject(unittest.TestCase):

    def test_init(self):
        artist = {'artist': ['Name featuring', 'Feature'],
                  'albumartist': 'Name',
                  'musicbrainz_artistid': VALID,
                  'musicbrainz_albumartistid': VALID.replace('11', '22'),
                  }
        art = Artist(**artist)
        self.assertTrue(art.name == 'Name')
        self.assertTrue(art.mbid == VALID.replace('11', '22'))
        artist.pop('musicbrainz_albumartistid')
        art = Artist(**artist)
        self.assertTrue(art.mbid == VALID)
        artist.pop('albumartist')
        art = Artist(**artist)

# vim: ai ts=4 sw=4 sts=4 expandtab
