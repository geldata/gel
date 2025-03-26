#
# This source file is part of the EdgeDB open source project.
#
# Copyright 2019-present MagicStack Inc. and the EdgeDB authors.
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

import asyncio

import edgedb

from edb.testbase import server as tb


class TestServerParamConversions(tb.QueryTestCase):

    SETUP = '''
        create function simple_to_str(val: str) -> str
        {
            using (val);
        };
        create function simple_to_str(val: int64) -> str
        {
            set server_param_conversions := '{"val": "cast_int64_to_str"}';
            using sql expression;
        };

        create function simple_from_array(val: str) -> str
        {
            using (val)
        };
        create function simple_from_array(val: array<str>) -> str
        {
            set server_param_conversions := '{"val": ["join_str_array", " "]}';
            using sql expression;
        };

        create function multi_to_str(a: str, b: str) -> tuple<str, str>
        {
            using ((a, b))
        };
        create function multi_to_str(a: int64, b: int64) -> tuple<str, str>
        {
            set server_param_conversions := (
                '{"a": "cast_int64_to_str", "b": "cast_int64_to_str"}'
            );
            using sql expression;
        };

        create function multi_to_str_and_float(a: str, b: float64) -> tuple<str, float64>
        {
            using ((a, b))
        };
        create function multi_to_str_and_float(a: int64, b: int64) -> tuple<str, float64>
        {
            set server_param_conversions := (
                '{"a": "cast_int64_to_str", "b": "cast_int64_to_float64"}'
            );
            using sql expression;
        };
    '''

    async def test_server_param_conversions_simple_01(self):
        await self.assert_query_result(
            'select simple_to_str(<str>$0)',
            ["hello"],
            variables=("hello",),
        )

        await self.assert_query_result(
            'select simple_to_str(<int64>$0)',
            ["123"],
            variables=(123,),
        )

        await self.assert_query_result(
            'select simple_from_array(<str>$0)',
            ["hello"],
            variables=("hello",),
        )
        await self.assert_query_result(
            'select simple_from_array(<array<str>>$0)',
            ["hello world"],
            variables=(["hello", "world"],),
        )

    async def test_server_param_conversions_simple_02(self):
        # Test that multiple calls to the same function works

        # Server param conversion call and normal call in same query
        await self.assert_query_result(
            '''
            select (
                simple_to_str(<int64>$0),
                simple_to_str(<str>$1),
            )
            ''',
            [("123", "hello")],
            variables=(123, "hello"),
        )

        # Same function with the same argument
        await self.assert_query_result(
            '''
            select (
                simple_to_str(<int64>$0),
                simple_to_str(<int64>$0),
                simple_to_str(<int64>$0),
            )
            ''',
            [("123", "123", "123")],
            variables=(123,),
        )
        await self.assert_query_result(
            '''
            with
                x := simple_to_str(<int64>$0),
                y := simple_to_str(<int64>$0),
                z := simple_to_str(<int64>$0),
            select (x, y, z)
            ''',
            [("123", "123", "123")],
            variables=(123,),
        )

        # Same function with different argument
        await self.assert_query_result(
            '''
            select (
                simple_to_str(<int64>$0),
                simple_to_str(<int64>$1),
                simple_to_str(<int64>$2),
            )
            ''',
            [("123", "456", "789")],
            variables=(123, 456, 789),
        )

        await self.assert_query_result(
            '''
            with
                x := simple_to_str(<int64>$0),
                y := simple_to_str(<int64>$1),
                z := simple_to_str(<int64>$2),
            select (x, y, z)
            ''',
            [("123", "456", "789")],
            variables=(123, 456, 789),
        )

        # Check that order of args is maintained
        await self.assert_query_result(
            '''
            with
                x := simple_to_str(<int64>$2),
                y := simple_to_str(<int64>$1),
                z := simple_to_str(<int64>$0),
            select (x, y, z)
            ''',
            [("789", "456", "123")],
            variables=(123, 456, 789),
        )

        # Check parameters with str names
        await self.assert_query_result(
            '''
            with
                x := simple_to_str(<int64>$foo),
                y := simple_to_str(<int64>$bar),
                z := simple_to_str(<int64>$baz),
            select (x, y, z)
            ''',
            [("123", "456", "789")],
            variables={'foo': 123, 'bar': 456, 'baz': 789},
        )

    async def test_server_param_conversions_simple_03(self):
        # tests some errors?
        pass

    async def test_server_param_conversions_multi_01(self):
        # A function with the same conversion multiple times
        await self.assert_query_result(
            'select multi_to_str(<str>$0, <str>$1)',
            [("hello", "world")],
            variables=("hello", "world"),
        )

        await self.assert_query_result(
            'select multi_to_str(<int64>$0, <int64>$1)',
            [("123", "456")],
            variables=(123, 456),
        )

    async def test_server_param_conversions_multi_02(self):
        # A function with some different conversions
        await self.assert_query_result(
            'select multi_to_str_and_float(<str>$0, <float64>$1)',
            [("hello", 1.5)],
            variables=("hello", 1.5),
        )

        await self.assert_query_result(
            'select multi_to_str_and_float(<int64>$0, <int64>$1)',
            [("1", 2.0)],
            variables=(1, 2),
        )

    async def test_server_param_conversions_multi_03(self):
        # Check that function called only if all param conversions applied
        pass
