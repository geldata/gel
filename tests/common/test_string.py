#
# This source file is part of the EdgeDB open source project.
#
# Copyright 2018-present MagicStack Inc. and the EdgeDB authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import unittest

import edb.common.string as string

class StringTests(unittest.TestCase):
    unescaped_escaped_strings = [
        ('', ''),
        ('abc', 'abc'),
        ('\b', '\\b'),
        ('\f', '\\f'),
        ('\n', '\\n'),
        ('\r', '\\r'),
        ('\t', '\\t'),
        ('\'', '\\\''),
        ('\"', '\\\"'),
        ('\\', '\\\\'),
        ('\\b', '\\\\b'),
        ('\\f', '\\\\f'),
        ('\\n', '\\\\n'),
        ('\\r', '\\\\r'),
        ('\\t', '\\\\t'),
        ('\\\'', '\\\\\\\''),
        ('\\\"', '\\\\\\\"'),
        ('\\\\', '\\\\\\\\'),
        ('abc"efg\nhij\'klm\\nop', 'abc\\"efg\\nhij\\\'klm\\\\nop'),
    ]

    def test_escape_string(self):
        for unescaped, escaped in StringTests.unescaped_escaped_strings:
            self.assertEqual(string.escape_string(unescaped), escaped)

    def test_unescape_string(self):
        for unescaped, escaped in StringTests.unescaped_escaped_strings:
            self.assertEqual(string.unescape_string(escaped), unescaped)
