# -*- coding: utf-8 -*-

import unittest

from sima.lib.meta import Meta, Artist, MetaContainer, is_uuid4
from sima.lib.meta import MetaException, SEPARATOR

VALID = '110e8100-e29b-41d1-a716-116655250000'

class TestMetaObject(unittest.TestCase):

    def test_uuid_integrity(self):
        wrong = VALID +'a'
        self.assertFalse(is_uuid4(wrong))
        #  test UUID4 format validation
        self.assertFalse(is_uuid4(VALID.replace('4', '3')))
        self.assertFalse(is_uuid4(VALID.replace('a', 'z')))

    def test_init(self):
        for args in [
                {'mbid':VALID},
                {'name': None},
                {'name': 42},
                ]:
            with self.assertRaises(MetaException,
                                   msg='{} does not raise an except.'.format(args)):
                Meta(**args)

    def test_equality(self):
        a = Meta(mbid=VALID, name='a')
        b = Meta(mbid=VALID, name='b')
        c = Meta(mbid=VALID.upper(), name='c')
        self.assertEqual(a, b)
        self.assertEqual(a, c)

    def test_hash(self):
        a = Meta(mbid=VALID, name='a')
        b = Meta(mbid=VALID, name='b')
        c = Meta(mbid=VALID, name='c')
        self.assertTrue(len({a, b, c}) == 1)
        self.assertTrue(a in [c, b])
        self.assertTrue(a in {c, b})
        # mbid is immutable
        self.assertRaises(AttributeError, a.__setattr__, 'mbid', VALID)

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
        art03 = Meta(name='Aphex Twin',
                           mbid='322942a1-6f70-4f48-866e-238cb2308fbd')

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

        self.assertTrue(hash(art00) != hash(art03),
                        'wrong: hash({!r}) == hash({!r})'.format(art00, art03))

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
        artist = {'artist': SEPARATOR.join(['Original Name', 'Featuring Nane', 'Feature…']),
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
        self.assertTrue(art.name == 'Original Name', art.name)

    def test_empty_name(self):
        for args in [
                {'mbid':VALID},
                {'name': None},
                {},
                ]:
            with self.assertRaises(MetaException,
                                   msg='{} does not raise an except.'.format(args)):
                Artist(**args)

class TestMetaContainers(unittest.TestCase):

    def  test_init(self):
        a = Meta(mbid=VALID, name='a')
        b = Meta(mbid=VALID, name='b')
        c = Meta(mbid=VALID.replace('11', '22'), name='b')
        # redondant with Meta test_comparison, but anyway
        cont = MetaContainer([a, b, c])
        self.assertTrue(len(cont) == 2)
        self.assertTrue(a in cont)
        self.assertTrue(b in cont)
        self.assertTrue(Meta(name='a') in cont)

    def test_intersection_difference(self):
        # Now set works as expected with composite (name/mbid) collections of Meta
        # cf Meta test_union
        # >>> len(MetaContainer([Artist(name='Name'), Artist(name='Name', mbid=<UUID4>)]) == 1
        # but
        # >>> len({Artist(name='Name'), Artist(name='Name', mbid=<UUID4>}) == 2
        art00 = Meta(name='Aphex Twin', mbid='f22942a1-6f70-4f48-866e-238cb2308fbd')
        art01 = Meta(name='Aphex Twin', mbid=None)
        self.assertTrue(MetaContainer([art00]) & MetaContainer([art01]))
        self.assertFalse(MetaContainer([art01]) - MetaContainer([art01]))
        art01._Meta__mbid = art00.mbid
        self.assertTrue(MetaContainer([art00]) & MetaContainer([art01]))
        self.assertFalse(MetaContainer([art01]) - MetaContainer([art01]))
        art01._Meta__mbid = art00.mbid.replace('229', '330')
        self.assertFalse(MetaContainer([art00]) & MetaContainer([art01]))

# vim: ai ts=4 sw=4 sts=4 expandtab
