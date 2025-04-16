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

import edgedb

from edb.testbase import server as tb


class TestServerParamConversions(tb.QueryTestCase):

    SETUP = '''
        create type Result {
            create property n: int64;
            create property val: str;
        };

        create function simple_to_str(val: str) -> str
        {
            using (val);
        };
        create function simple_to_str(val: int64) -> str
        {
            set server_param_conversions := (
                '{"val": "cast_int64_to_str"}'
            );
            using sql expression;
        };

        create function simple_from_array(val: str) -> str
        {
            using (val)
        };
        create function simple_from_array(val: array<str>) -> str
        {
            set server_param_conversions := (
                '{"val": ["join_str_array", " - "]}'
            );
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

        create function multi_to_str_and_float(
            a: str, b: float64
        ) -> tuple<str, float64> {
            using ((a, b))
        };
        create function multi_to_str_and_float(
            a: int64, b: int64
        ) -> tuple<str, float64>
        {
            set server_param_conversions := (
                '{"a": "cast_int64_to_str", "b": "cast_int64_to_float64"}'
            );
            using sql expression;
        };

        create function volatile_to_str(val: str) -> str
        {
            using (val);
        };
        create function volatile_to_str(val: int64) -> str
        {
            set server_param_conversions := (
                '{"val": "cast_int64_to_str_volatile"}'
            );
            using sql expression;
        };
    '''

    async def test_server_param_conversions_simple_01(self):
        # Scalar query param
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

    async def test_server_param_conversions_simple_02(self):
        # Scalar literal
        await self.assert_query_result(
            'select simple_to_str(123)',
            ["123"],
        )

        # Check that the source value `123` from the previous query is
        # not cached
        await self.assert_query_result(
            'select simple_to_str(456)',
            ["456"],
        )

        # Check conversion works with normalized constants whose size changes
        await self.assert_query_result(
            'select ("AAAAA", simple_to_str(456), "BBBBB")',
            [("AAAAA", "456", "BBBBB")],
        )
        await self.assert_query_result(
            'select ("A", simple_to_str(456), "B")',
            [("A", "456", "B")],
        )

    async def test_server_param_conversions_simple_03(self):
        # Scalar expression
        async with self.assertRaisesRegexTx(
            edgedb.QueryError,
            "Argument 'val' must be a constant or query parameter"
        ):
            await self.assert_query_result(
                'select simple_to_str(1 + 2)',
                ["3"],
            )

    async def test_server_param_conversions_simple_04(self):
        # Scalar computed global
        await self.con.execute('''
            create global foo := 123 + 456;
        ''')

        async with self.assertRaisesRegexTx(
            edgedb.QueryError,
            "Argument 'val' must be a constant or query parameter"
        ):
            await self.assert_query_result(
                'select simple_to_str(global foo)',
                ["123"],
            )

    async def test_server_param_conversions_simple_05(self):
        # Scalar non-computed global
        await self.con.execute('''
            create global foo: int64;
        ''')
        await self.con.execute('''
            set global foo := 123;
        ''')

        async with self.assertRaisesRegexTx(
            edgedb.QueryError,
            "Argument 'val' must be a constant or query parameter"
        ):
            await self.assert_query_result(
                'select simple_to_str(global foo)',
                ["123"],
            )

    async def test_server_param_conversions_simple_06(self):
        # Scalar alias
        await self.con.execute('''
            create alias foo := 123;
        ''')

        async with self.assertRaisesRegexTx(
            edgedb.QueryError,
            "Argument 'val' must be a constant or query parameter"
        ):
            await self.assert_query_result(
                'select simple_to_str(foo)',
                ["123"],
            )

    async def test_server_param_conversions_simple_07(self):
        # Array query param
        await self.assert_query_result(
            'select simple_from_array(<str>$0)',
            ["hello"],
            variables=("hello",),
        )
        await self.assert_query_result(
            'select simple_from_array(<array<str>>$0)',
            ["hello - world - !"],
            variables=(["hello", "world", "!"],),
        )

    async def test_server_param_conversions_simple_08(self):
        # Array literal
        async with self.assertRaisesRegexTx(
            edgedb.QueryError,
            "Argument 'val' must be a query parameter"
        ):
            await self.assert_query_result(
                'select simple_from_array(["hello", "world", "!"])',
                ["hello - world - !"],
            )

    async def test_server_param_conversions_simple_09(self):
        # Array expression
        async with self.assertRaisesRegexTx(
            edgedb.QueryError,
            "Argument 'val' must be a query parameter"
        ):
            await self.assert_query_result(
                'select simple_from_array(array_agg({"hello", "world", "!"}))',
                ["hello - world - !"],
            )

    async def test_server_param_conversions_simple_10(self):
        # Array computed global
        await self.con.execute('''
            create global foo := ["hello", "world", "!"];
        ''')

        async with self.assertRaisesRegexTx(
            edgedb.QueryError,
            "Argument 'val' must be a query parameter"
        ):
            await self.assert_query_result(
                'select simple_from_array(global foo)',
                ["hello - world - !"],
            )

    async def test_server_param_conversions_simple_11(self):
        # Array non-computed global
        await self.con.execute('''
            create global foo: array<str>;
        ''')
        await self.con.execute('''
            set global foo := ["hello", "world", "!"];
        ''')

        async with self.assertRaisesRegexTx(
            edgedb.QueryError,
            "Argument 'val' must be a query parameter"
        ):
            await self.assert_query_result(
                'select simple_from_array(global foo)',
                ["hello - world - !"],
            )

    async def test_server_param_conversions_simple_12(self):
        # Array alias
        await self.con.execute('''
            create alias foo := ["hello", "world", "!"];
        ''')

        async with self.assertRaisesRegexTx(
            edgedb.QueryError,
            "Argument 'val' must be a query parameter"
        ):
            await self.assert_query_result(
                'select simple_from_array(foo)',
                ["hello - world - !"],
            )

    async def test_server_param_conversions_multi_01(self):
        # Multiple calls to the same function in a query

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

    async def test_server_param_conversions_multi_02(self):
        # Call different functions with param conversions
        await self.assert_query_result(
            '''
            with
                x := simple_to_str(<int64>$0),
                y := simple_from_array(<array<str>>$1),
            select (x, y)
            ''',
            [("123", "hello - world - !")],
            variables=(123, ["hello", "world", "!"]),
        )

    async def test_server_param_conversions_multi_03(self):
        # Param is used as both converted and non-converted
        await self.assert_query_result(
            'select (simple_to_str(<int64>$0), <int64>$0 + 1)',
            [("123", 124)],
            variables=(123,),
        )

        await self.assert_query_result(
            '''
            select (
                simple_to_str(<int64>$0),
                <int64>$0,
                simple_from_array(<array<str>>$1),
                <array<str>>$1,
            )
            ''',
            [("123", 123, "hello - world - !", ["hello", "world", "!"])],
            variables=(123, ["hello", "world", "!"]),
        )

    async def test_server_param_conversions_multi_04(self):
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

    async def test_server_param_conversions_multi_05(self):
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

    async def test_server_param_conversions_multi_06(self):
        # Can cast param and match the non-conversion version
        await self.assert_query_result(
            'select multi_to_str_and_float(<str>$0, <int64>$1)',
            [("hello", 1.0)],
            variables=("hello", 1),
        )

    async def test_server_param_conversions_multi_07(self):
        # Function called only if all param conversions applied
        async with self.assertRaisesRegexTx(
            edgedb.QueryError,
            r'function .* does not exist'
        ):
            await self.assert_query_result(
                'select multi_to_str_and_float(<int64>$0, <float64>$1)',
                [("1", 2.3)],
                variables=(1, 2.3),
            )

    async def test_server_param_conversions_globals_01(self):
        # Check that the parameters are properly encoded in the presence of
        # non-computed globals
        await self.con.execute('''
            create global curr_user: str;
        ''')

        await self.assert_query_result(
            'select simple_to_str(<int64>$0)',
            ["123"],
            variables=(123,),
        )

        await self.con.execute('''
            set global curr_user := "Bob";
        ''')

        await self.assert_query_result(
            'select simple_to_str(<int64>$0)',
            ["123"],
            variables=(123,),
        )

        await self.assert_query_result(
            '''
            select (
                global curr_user,
                simple_to_str(<int64>$0),
                <int64>$0,
            )
            ''',
            [("Bob", "123", 123)],
            variables=(123,),
        )

    async def test_server_param_conversions_globals_02(self):
        # Check that the non converted function works in a computed global.
        await self.con.execute('''
            create global foo := simple_to_str("123");
        ''')

        await self.assert_query_result(
            'select global foo',
            ["123"],
        )

    async def test_server_param_conversions_globals_03(self):
        # Check that the parameter conversion is disallowed in a computed global
        await self.con.execute('''
            create global foo := simple_to_str(123);
        ''')

        await self.assert_query_result(
            'select global foo',
            ["123"],
        )

    async def test_server_param_conversions_globals_04(self):
        # Check that the parameter conversion is disallowed in non-computed
        # global.
        await self.con.execute('''
            create global foo -> str;
        ''')
        async with self.assertRaisesRegexTx(
            edgedb.QueryError,
            r"Function 'default::simple_to_str\(val: std::str\)' "
            r"is not allowed in a config statement."
        ):
            await self.con.execute('''
                set global foo := simple_to_str(123);
            ''')

    async def test_server_param_conversions_alias_01(self):
        # Check that the parameter conversion works in an alias.
        await self.con.execute('''
            create alias foo := simple_to_str(123);
        ''')

        await self.assert_query_result(
            'select foo',
            ["123"],
        )

    async def test_server_param_conversions_pointer_01(self):
        # Param conversion is ok in a computed pointer
        await self.con.execute("""
            CREATE TYPE Foo {
                CREATE PROPERTY out := simple_to_str("123");
            };
            CREATE TYPE Bar {
                CREATE PROPERTY out := simple_to_str(456);
            };
        """)
        await self.con.execute('''
            insert Foo;
            insert Bar;
        ''')

        await self.assert_query_result(
            'select Foo.out',
            ["123"],
        )
        await self.assert_query_result(
            'select Bar.out',
            ["456"],
        )

    async def test_server_param_conversions_pointer_02(self):
        # Volatile param conversion disallowed as usual
        await self.con.execute("""
            CREATE TYPE Foo {
                CREATE PROPERTY out := volatile_to_str("123");
            };
        """)

        async with self.assertRaisesRegexTx(
            edgedb.QueryError,
            "volatile functions are not permitted in schema-defined "
            "computed expressions",
        ):
            await self.con.execute("""
                CREATE TYPE Bar {
                    CREATE PROPERTY out := volatile_to_str(456);
                };
            """)

    async def test_server_param_conversions_script_01(self):
        # Simple script
        await self.con.execute(
            '''
            insert Result { n := 1, val := simple_to_str(<int64>$0) };
            insert Result { n := 2, val := "456" };
            ''',
            123
        )

        await self.assert_query_result(
            'select Result { n, val } order by .n',
            [
                {'n': 1, 'val': "123"},
                {'n': 2, 'val': "456"},
            ],
        )

    async def test_server_param_conversions_script_02(self):
        # Script where statements share the same converted parameter
        await self.con.execute(
            '''
            insert Result { n := 1, val := simple_to_str(<int64>$0) };
            insert Result { n := 2, val := simple_to_str(<int64>$0) };
            ''',
            123
        )

        await self.assert_query_result(
            'select Result { n, val } order by .n',
            [
                {'n': 1, 'val': "123"},
                {'n': 2, 'val': "123"},
            ],
        )

    async def test_server_param_conversions_script_03(self):
        # Script with different converted parameters
        await self.con.execute(
            '''
            insert Result { n := 1, val := simple_to_str(<int64>$0) };
            insert Result { n := 2, val := simple_to_str(<int64>$1) };
            ''',
            123,
            456,
        )

        await self.assert_query_result(
            'select Result { n, val } order by .n',
            [
                {'n': 1, 'val': "123"},
                {'n': 2, 'val': "456"},
            ],
        )

    async def test_server_param_conversions_script_04(self):
        # Script where the parameter is both converted and not converted
        await self.con.execute(
            '''
            insert Result { n := 1, val := <str><int64>$0 ++ "!" };
            insert Result { n := 2, val := simple_to_str(<int64>$0) };
            ''',
            123,
        )

        await self.assert_query_result(
            'select Result { n, val } order by .n',
            [
                {'n': 1, 'val': "123!"},
                {'n': 2, 'val': "123"},
            ],
        )

    async def test_server_param_conversions_script_05(self):
        # Script where layout of blobs is different
        await self.con.execute(
            '''
            insert Result { n := 1, val := simple_to_str(123) };
            insert Result { n := 1 + 1, val := simple_to_str(456) };
            ''',
        )

        await self.assert_query_result(
            'select Result { n, val } order by .n',
            [
                {'n': 1, 'val': "123"},
                {'n': 2, 'val': "456"},
            ],
        )

    async def test_server_param_conversions_script_06(self):
        # Script with a cached query, where converted constants differ
        await self.con.execute(
            '''
            insert Result { n := 0, val := simple_to_str(0) };
            ''',
        )
        await self.con.execute(
            '''
            insert Result { n := 1, val := simple_to_str(123) };
            insert Result { n := 2, val := simple_to_str(456) };
            ''',
        )

        await self.assert_query_result(
            'select Result { n, val } order by .n',
            [
                {'n': 0, 'val': "0"},
                {'n': 1, 'val': "123"},
                {'n': 2, 'val': "456"},
            ],
        )
