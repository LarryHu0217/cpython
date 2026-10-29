"""Test cases for the fnmatch module."""

import fnmatch as fnmatch_module
import ntpath
import os
import pathlib
import posixpath
import string
import unittest
import warnings
from fnmatch import fnmatch, fnmatchcase, translate, filter, filterfalse
from test.support import os_helper
from unittest import mock


IGNORECASE = os.path.normcase('P') == os.path.normcase('p')
NORMSEP = os.path.normcase('\\') == os.path.normcase('/')


class FnmatchTestCase(unittest.TestCase):

    def check_match(self, filename, pattern, should_match=True, fn=fnmatch):
        if should_match:
            self.assertTrue(fn(filename, pattern),
                         "expected %r to match pattern %r"
                         % (filename, pattern))
        else:
            self.assertFalse(fn(filename, pattern),
                         "expected %r not to match pattern %r"
                         % (filename, pattern))

    def test_fnmatch(self):
        check = self.check_match
        check('abc', 'abc')
        check('abc', '?*?')
        check('abc', '???*')
        check('abc', '*???')
        check('abc', '???')
        check('abc', '*')
        check('abc', 'ab[cd]')
        check('abc', 'ab[!de]')
        check('abc', 'ab[de]', False)
        check('a', '??', False)
        check('a', 'b', False)

        # these test that '\' is handled correctly in character sets;
        # see SF bug #409651
        check('\\', r'[\]')
        check('a', r'[!\]')
        check('\\', r'[!\]', False)

        # test that filenames with newlines in them are handled correctly.
        # http://bugs.python.org/issue6665
        check('foo\nbar', 'foo*')
        check('foo\nbar\n', 'foo*')
        check('\nfoo', 'foo*', False)
        check('\n', '*')

    def test_slow_fnmatch(self):
        check = self.check_match
        check('a' * 50, '*a*a*a*a*a*a*a*a*a*a')
        # The next "takes forever" if the regexp translation is
        # straightforward.  See bpo-40480.
        check('a' * 50 + 'b', '*a*a*a*a*a*a*a*a*a*a', False)

    def test_mix_bytes_str(self):
        self.assertRaises(TypeError, fnmatch, 'test', b'*')
        self.assertRaises(TypeError, fnmatch, b'test', '*')
        self.assertRaises(TypeError, fnmatchcase, 'test', b'*')
        self.assertRaises(TypeError, fnmatchcase, b'test', '*')

    def test_fnmatchcase(self):
        check = self.check_match
        check('abc', 'abc', True, fnmatchcase)
        check('AbC', 'abc', False, fnmatchcase)
        check('abc', 'AbC', False, fnmatchcase)
        check('AbC', 'AbC', True, fnmatchcase)

        check('usr/bin', 'usr/bin', True, fnmatchcase)
        check('usr\\bin', 'usr/bin', False, fnmatchcase)
        check('usr/bin', 'usr\\bin', False, fnmatchcase)
        check('usr\\bin', 'usr\\bin', True, fnmatchcase)

    def test_bytes(self):
        self.check_match(b'test', b'te*')
        self.check_match(b'test\xff', b'te*\xff')
        self.check_match(b'foo\nbar', b'foo*')

    def test_case(self):
        check = self.check_match
        check('abc', 'abc')
        check('AbC', 'abc', IGNORECASE)
        check('abc', 'AbC', IGNORECASE)
        check('AbC', 'AbC')

    def test_sep(self):
        check = self.check_match
        check('usr/bin', 'usr/bin')
        check('usr\\bin', 'usr/bin', NORMSEP)
        check('usr/bin', 'usr\\bin', NORMSEP)
        check('usr\\bin', 'usr\\bin')

    def test_char_set(self):
        check = self.check_match
        tescases = string.ascii_lowercase + string.digits + string.punctuation
        for c in tescases:
            check(c, '[az]', c in 'az')
            check(c, '[!az]', c not in 'az')
        # Case insensitive.
        for c in tescases:
            check(c, '[AZ]', (c in 'az') and IGNORECASE)
            check(c, '[!AZ]', (c not in 'az') or not IGNORECASE)
        for c in string.ascii_uppercase:
            check(c, '[az]', (c in 'AZ') and IGNORECASE)
            check(c, '[!az]', (c not in 'AZ') or not IGNORECASE)
        # Repeated same character.
        for c in tescases:
            check(c, '[aa]', c == 'a')
        # Special cases.
        for c in tescases:
            check(c, '[^az]', c in '^az')
            check(c, '[[az]', c in '[az')
            check(c, r'[!]]', c != ']')
        check('[', '[')
        check('[]', '[]')
        check('[!', '[!')
        check('[!]', '[!]')

    def test_range(self):
        check = self.check_match
        tescases = string.ascii_lowercase + string.digits + string.punctuation
        for c in tescases:
            check(c, '[b-d]', c in 'bcd')
            check(c, '[!b-d]', c not in 'bcd')
            check(c, '[b-dx-z]', c in 'bcdxyz')
            check(c, '[!b-dx-z]', c not in 'bcdxyz')
        # Case insensitive.
        for c in tescases:
            check(c, '[B-D]', (c in 'bcd') and IGNORECASE)
            check(c, '[!B-D]', (c not in 'bcd') or not IGNORECASE)
        for c in string.ascii_uppercase:
            check(c, '[b-d]', (c in 'BCD') and IGNORECASE)
            check(c, '[!b-d]', (c not in 'BCD') or not IGNORECASE)
        # Upper bound == lower bound.
        for c in tescases:
            check(c, '[b-b]', c == 'b')
        # Special cases.
        for c in tescases:
            check(c, '[!-#]', c not in '-#')
            check(c, '[!--.]', c not in '-.')
            check(c, '[^-`]', c in '^_`')
            if not (NORMSEP and c == '/'):
                check(c, '[[-^]', c in r'[\]^')
                check(c, r'[\-^]', c in r'\]^')
            check(c, '[b-]', c in '-b')
            check(c, '[!b-]', c not in '-b')
            check(c, '[-b]', c in '-b')
            check(c, '[!-b]', c not in '-b')
            check(c, '[-]', c in '-')
            check(c, '[!-]', c not in '-')
        # Upper bound is less that lower bound: error in RE.
        for c in tescases:
            check(c, '[d-b]', False)
            check(c, '[!d-b]', True)
            check(c, '[d-bx-z]', c in 'xyz')
            check(c, '[!d-bx-z]', c not in 'xyz')
            check(c, '[d-b^-`]', c in '^_`')
            if not (NORMSEP and c == '/'):
                check(c, '[d-b[-^]', c in r'[\]^')

    def test_sep_in_char_set(self):
        check = self.check_match
        check('/', r'[/]')
        check('\\', r'[\]')
        check('/', r'[\]', NORMSEP)
        check('\\', r'[/]', NORMSEP)
        check('[/]', r'[/]', False)
        check(r'[\\]', r'[/]', False)
        check('\\', r'[\t]')
        check('/', r'[\t]', NORMSEP)
        check('t', r'[\t]')
        check('\t', r'[\t]', False)

    def test_sep_in_range(self):
        check = self.check_match
        check('a/b', 'a[.-0]b', not NORMSEP)
        check('a\\b', 'a[.-0]b', False)
        check('a\\b', 'a[Z-^]b', not NORMSEP)
        check('a/b', 'a[Z-^]b', False)

        check('a/b', 'a[/-0]b', not NORMSEP)
        check(r'a\b', 'a[/-0]b', False)
        check('a[/-0]b', 'a[/-0]b', False)
        check(r'a[\-0]b', 'a[/-0]b', False)

        check('a/b', 'a[.-/]b')
        check(r'a\b', 'a[.-/]b', NORMSEP)
        check('a[.-/]b', 'a[.-/]b', False)
        check(r'a[.-\]b', 'a[.-/]b', False)

        check(r'a\b', r'a[\-^]b')
        check('a/b', r'a[\-^]b', NORMSEP)
        check(r'a[\-^]b', r'a[\-^]b', False)
        check('a[/-^]b', r'a[\-^]b', False)

        check(r'a\b', r'a[Z-\]b', not NORMSEP)
        check('a/b', r'a[Z-\]b', False)
        check(r'a[Z-\]b', r'a[Z-\]b', False)
        check('a[Z-/]b', r'a[Z-\]b', False)

    def test_warnings(self):
        with warnings.catch_warnings():
            warnings.simplefilter('error', Warning)
            check = self.check_match
            check('[', '[[]')
            check('&', '[a&&b]')
            check('|', '[a||b]')
            check('~', '[a~~b]')
            check(',', '[a-z+--A-Z]')
            check('.', '[a-z--/A-Z]')


class TranslateTestCase(unittest.TestCase):

    def test_translate(self):
        import re
        self.assertEqual(translate('*'), r'(?s:.*)\z')
        self.assertEqual(translate('?'), r'(?s:.)\z')
        self.assertEqual(translate('a?b*'), r'(?s:a.b.*)\z')
        self.assertEqual(translate('[abc]'), r'(?s:[abc])\z')
        self.assertEqual(translate('[]]'), r'(?s:[]])\z')
        self.assertEqual(translate('[!x]'), r'(?s:[^x])\z')
        self.assertEqual(translate('[^x]'), r'(?s:[\^x])\z')
        self.assertEqual(translate('[x'), r'(?s:\[x)\z')
        # from the docs
        self.assertEqual(translate('*.txt'), r'(?s:.*\.txt)\z')
        # squash consecutive stars
        self.assertEqual(translate('*********'), r'(?s:.*)\z')
        self.assertEqual(translate('A*********'), r'(?s:A.*)\z')
        self.assertEqual(translate('*********A'), r'(?s:.*A)\z')
        self.assertEqual(translate('A*********?[?]?'), r'(?s:A.*.[?].)\z')
        # fancy translation to prevent exponential-time match failure
        t = translate('**a*a****a')
        self.assertEqual(t, r'(?s:(?>.*?a)(?>.*?a).*a)\z')
        # and try pasting multiple translate results - it's an undocumented
        # feature that this works
        r1 = translate('**a**a**a*')
        r2 = translate('**b**b**b*')
        r3 = translate('*c*c*c*')
        fatre = "|".join([r1, r2, r3])
        self.assertTrue(re.match(fatre, 'abaccad'))
        self.assertTrue(re.match(fatre, 'abxbcab'))
        self.assertTrue(re.match(fatre, 'cbabcaxc'))
        self.assertFalse(re.match(fatre, 'dabccbad'))

    def test_translate_wildcards(self):
        for pattern, expect in [
            ('ab*', r'(?s:ab.*)\z'),
            ('ab*cd', r'(?s:ab.*cd)\z'),
            ('ab*cd*', r'(?s:ab(?>.*?cd).*)\z'),
            ('ab*cd*12', r'(?s:ab(?>.*?cd).*12)\z'),
            ('ab*cd*12*', r'(?s:ab(?>.*?cd)(?>.*?12).*)\z'),
            ('ab*cd*12*34', r'(?s:ab(?>.*?cd)(?>.*?12).*34)\z'),
            ('ab*cd*12*34*', r'(?s:ab(?>.*?cd)(?>.*?12)(?>.*?34).*)\z'),
        ]:
            with self.subTest(pattern):
                translated = translate(pattern)
                self.assertEqual(translated, expect, pattern)

        for pattern, expect in [
            ('*ab', r'(?s:.*ab)\z'),
            ('*ab*', r'(?s:(?>.*?ab).*)\z'),
            ('*ab*cd', r'(?s:(?>.*?ab).*cd)\z'),
            ('*ab*cd*', r'(?s:(?>.*?ab)(?>.*?cd).*)\z'),
            ('*ab*cd*12', r'(?s:(?>.*?ab)(?>.*?cd).*12)\z'),
            ('*ab*cd*12*', r'(?s:(?>.*?ab)(?>.*?cd)(?>.*?12).*)\z'),
            ('*ab*cd*12*34', r'(?s:(?>.*?ab)(?>.*?cd)(?>.*?12).*34)\z'),
            ('*ab*cd*12*34*', r'(?s:(?>.*?ab)(?>.*?cd)(?>.*?12)(?>.*?34).*)\z'),
        ]:
            with self.subTest(pattern):
                translated = translate(pattern)
                self.assertEqual(translated, expect, pattern)

    def test_translate_expressions(self):
        for pattern, expect in [
            ('[', r'(?s:\[)\z'),
            ('[!', r'(?s:\[!)\z'),
            ('[]', r'(?s:\[\])\z'),
            ('[abc', r'(?s:\[abc)\z'),
            ('[!abc', r'(?s:\[!abc)\z'),
            ('[abc]', r'(?s:[abc])\z'),
            ('[!abc]', r'(?s:[^abc])\z'),
            ('[!abc][!def]', r'(?s:[^abc][^def])\z'),
            # with [[
            ('[[', r'(?s:\[\[)\z'),
            ('[[a', r'(?s:\[\[a)\z'),
            ('[[]', r'(?s:[\[])\z'),
            ('[[]a', r'(?s:[\[]a)\z'),
            ('[[]]', r'(?s:[\[]\])\z'),
            ('[[]a]', r'(?s:[\[]a\])\z'),
            ('[[a]', r'(?s:[\[a])\z'),
            ('[[a]]', r'(?s:[\[a]\])\z'),
            ('[[a]b', r'(?s:[\[a]b)\z'),
            # backslashes
            ('[\\', r'(?s:\[\\)\z'),
            (r'[\]', r'(?s:[\\])\z'),
            (r'[\\]', r'(?s:[\\\\])\z'),
        ]:
            with self.subTest(pattern):
                translated = translate(pattern)
                self.assertEqual(translated, expect, pattern)

    def test_star_indices_locations(self):
        from fnmatch import _translate

        blocks = ['a^b', '***', '?', '?', '[a-z]', '[1-9]', '*', '++', '[[a']
        parts, star_indices = _translate(''.join(blocks), '*', '.')
        expect_parts = ['a', r'\^', 'b', '*',
                        '.', '.', '[a-z]', '[1-9]', '*',
                        r'\+', r'\+', r'\[', r'\[', 'a']
        self.assertListEqual(parts, expect_parts)
        self.assertListEqual(star_indices, [3, 8])


class FilterTestCase(unittest.TestCase):

    def test_filter(self):
        self.assertEqual(filter(['Python', 'Ruby', 'Perl', 'Tcl'], 'P*'),
                         ['Python', 'Perl'])
        self.assertEqual(filter([b'Python', b'Ruby', b'Perl', b'Tcl'], b'P*'),
                         [b'Python', b'Perl'])

    def test_mix_bytes_str(self):
        self.assertRaises(TypeError, filter, ['test'], b'*')
        self.assertRaises(TypeError, filter, [b'test'], '*')

    def test_case(self):
        self.assertEqual(filter(['Test.py', 'Test.rb', 'Test.PL'], '*.p*'),
                         ['Test.py', 'Test.PL'] if IGNORECASE else ['Test.py'])
        self.assertEqual(filter(['Test.py', 'Test.rb', 'Test.PL'], '*.P*'),
                         ['Test.py', 'Test.PL'] if IGNORECASE else ['Test.PL'])

    def test_sep(self):
        self.assertEqual(filter(['usr/bin', 'usr', 'usr\\lib'], 'usr/*'),
                         ['usr/bin', 'usr\\lib'] if NORMSEP else ['usr/bin'])
        self.assertEqual(filter(['usr/bin', 'usr', 'usr\\lib'], 'usr\\*'),
                         ['usr/bin', 'usr\\lib'] if NORMSEP else ['usr\\lib'])


class FilterFalseTestCase(unittest.TestCase):

    def test_filterfalse(self):
        actual = filterfalse(['Python', 'Ruby', 'Perl', 'Tcl'], 'P*')
        self.assertListEqual(actual, ['Ruby', 'Tcl'])
        actual = filterfalse([b'Python', b'Ruby', b'Perl', b'Tcl'], b'P*')
        self.assertListEqual(actual, [b'Ruby', b'Tcl'])

    def test_mix_bytes_str(self):
        self.assertRaises(TypeError, filterfalse, ['test'], b'*')
        self.assertRaises(TypeError, filterfalse, [b'test'], '*')

    def test_case(self):
        self.assertEqual(filterfalse(['Test.py', 'Test.rb', 'Test.PL'], '*.p*'),
                         ['Test.rb'] if IGNORECASE else ['Test.rb', 'Test.PL'])
        self.assertEqual(filterfalse(['Test.py', 'Test.rb', 'Test.PL'], '*.P*'),
                         ['Test.rb'] if IGNORECASE else ['Test.py', 'Test.rb',])

    def test_sep(self):
        self.assertEqual(filterfalse(['usr/bin', 'usr', 'usr\\lib'], 'usr/*'),
                         ['usr'] if NORMSEP else ['usr', 'usr\\lib'])
        self.assertEqual(filterfalse(['usr/bin', 'usr', 'usr\\lib'], 'usr\\*'),
                         ['usr'] if NORMSEP else ['usr/bin', 'usr'])


class FilterPathLikeTestCase(unittest.TestCase):

    def test_pathlike_names(self):
        for factory in (pathlib.Path, os_helper.FakePath):
            for as_bytes in (False, True):
                if factory is pathlib.Path and as_bytes:
                    continue
                values = ['a.py', 'a.txt', 'b.py']
                pattern = '*.py'
                if as_bytes:
                    values = [value.encode() for value in values]
                    pattern = pattern.encode()
                first, other, last = [factory(value) for value in values]
                names = [first, other, last, first]
                for func, expected in ((filter, [first, last, first]),
                                       (filterfalse, [other])):
                    for pat in (pattern, os_helper.FakePath(pattern)):
                        with self.subTest(factory=factory, as_bytes=as_bytes,
                                          func=func, pattern=pat):
                            actual = func(names, pat)
                            self.assertEqual(actual, expected)
                            for actual_name, expected_name in zip(actual,
                                                                  expected):
                                self.assertIs(actual_name, expected_name)

    def test_pathlike_iterator(self):
        names = [os_helper.FakePath('a.py'), os_helper.FakePath('b.txt')]
        for func, expected in ((filter, names[:1]), (filterfalse, names[1:])):
            with self.subTest(func=func):
                iterator = iter(names)
                actual = func(iterator, '*.py')
                self.assertEqual(actual, expected)
                self.assertIs(actual[0], expected[0])
                self.assertEqual(list(iterator), [])

    def test_pathlike_empty(self):
        for func in (filter, filterfalse):
            for pattern in ('*', b'*'):
                with self.subTest(func=func, pattern=pattern):
                    self.assertEqual(func([], os_helper.FakePath(pattern)), [])

    def test_pathlike_mixed_types(self):
        for func in (filter, filterfalse):
            for name, pattern in (('a.py', b'*'), (b'a.py', '*')):
                with self.subTest(func=func, name=name, pattern=pattern):
                    with self.assertRaises(TypeError):
                        func([os_helper.FakePath(name)], pattern)

    def test_pathlike_invalid_fspath(self):
        for func in (filter, filterfalse):
            with self.subTest(func=func):
                with self.assertRaisesRegex(TypeError, '__fspath__'):
                    func([os_helper.FakePath(42)], '*')

    def test_pathlike_normalization(self):
        names = [os_helper.FakePath(name) for name in
                 ('DIR/A.PY', 'dir/b.py', r'dir\c.py', 'dir/d.txt')]
        for path_module, included, excluded in (
                (posixpath, [names[1]], [names[0], names[2], names[3]]),
                (ntpath, names[:3], names[3:])):
            with mock.patch.object(fnmatch_module, 'os') as mock_os:
                mock_os.path = path_module
                for func, expected in ((filter, included),
                                       (filterfalse, excluded)):
                    with self.subTest(path_module=path_module, func=func):
                        actual = func(names, os_helper.FakePath('dir/*.py'))
                        self.assertEqual(actual, expected)
                        for actual_name, expected_name in zip(actual, expected):
                            self.assertIs(actual_name, expected_name)


if __name__ == "__main__":
    unittest.main()
