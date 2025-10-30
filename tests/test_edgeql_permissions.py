#
# This source file is part of the EdgeDB open source project.
#
# Copyright 2017-present MagicStack Inc. and the EdgeDB authors.
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

import os.path

import edgedb

from edb.testbase import server as tb
from edb.testbase import http as tb_http


class TestEdgeQLPermissions(tb.QueryTestCase):
    '''Tests for permissions.'''

    SCHEMA = os.path.join(os.path.dirname(__file__), 'schemas',
                          'cards.esdl')

    SETUP = '''
    CREATE FUNCTION is_game_admin() -> bool using(global GameAdmin);
    CREATE FUNCTION is_game_admin_nested() -> bool using(is_game_admin());

    CREATE FUNCTION is_game_admin_inlined_simple() -> bool {
        using(global GameAdmin);
        set is_inlined := true;
    };
    CREATE FUNCTION is_game_admin_inline_inner() -> bool {
        using(is_game_admin_inlined_simple())
    };
    CREATE FUNCTION is_game_admin_inline_outer() -> bool {
        using(is_game_admin());
        set is_inlined := true;
    };
    CREATE FUNCTION is_game_admin_inline_both() -> bool {
        using(is_game_admin_inlined_simple());
        set is_inlined := true;
    };

    CREATE REQUIRED GLOBAL some_flag -> int64 { set default := 0 };
    CREATE FUNCTION with_global() -> tuple<int64, bool> using (
        (global some_flag, global GameAdmin)
    );

    CREATE FUNCTION with_func_arg(n: int64) -> tuple<int64, bool> using (
        (n, global GameAdmin)
    );
    '''

    async def test_edgeql_permissions_errors_01(self):
        async with self.assertRaisesRegexTx(
            edgedb.QueryError,
            r"'GameAdmin' exists, but is a permission, not a global",
        ):
            await self.con.execute('''
                set global GameAdmin := {};
            ''')

    async def test_edgeql_permissions_basic_01(self):
        await self.assert_query_result(
            'select global GameAdmin',
            # Tests run as superuser
            [True],
        )

    async def test_edgeql_permissions_basic_02(self):
        # Permission within functions
        function_names = [
            'is_game_admin',
            'is_game_admin_nested',
            'is_game_admin_inlined_simple',
            'is_game_admin_inline_inner',
            'is_game_admin_inline_outer',
            'is_game_admin_inline_both',
        ]
        for function_name in function_names:
            await self.assert_query_result(
                f'select {function_name}();',
                # Tests run as superuser
                [True],
            )

    async def test_edgeql_permissions_basic_03(self):
        # Permission within function that also uses global
        await self.con.execute('''
            set global some_flag := 1;
        ''')
        await self.assert_query_result(
            f'select with_global();',
            # Tests run as superuser
            [(1, True)],
        )

    async def test_edgeql_permissions_basic_04(self):
        # Permission within function that also has an argument
        await self.assert_query_result(
            f'select with_func_arg(1);',
            # Tests run as superuser
            [(1, True)],
        )
        await self.assert_query_result(
            f'select with_func_arg(<int64>$param);',
            # Tests run as superuser
            [(1, True)],
            variables={
                'param': 1,
            },
        )

    async def test_edgeql_permissions_basic_05(self):
        await self.con.execute('''
            CREATE TYPE T {
                create property foo -> bool;
            };
            INSERT T;
        ''')

        async with self.assertRaisesRegexTx(
            edgedb.UnsupportedFeatureError,
            # We want to rule out it saying "functions that reference
            # globals" instead of "globals". str on our exceptions
            # puts ANSI control sequence garbage in, though, so we
            # can't just match the start of the string. Match anything
            # without spaces.
            '(?m)^[^ ]*globals may not be used when converting/populating '
            'data in migrations'
        ):
            await self.con.execute('''
                ALTER TYPE T ALTER PROPERTY foo
                SET REQUIRED USING (global GameAdmin)
            ''')

    async def test_edgeql_permissions_basic_06(self):
        await self.con.execute('''
            CREATE TYPE T;
            INSERT T;
        ''')
        await self.con.execute('''
            ALTER TYPE T {
                CREATE REQUIRED PROPERTY foo -> bool {
                    SET default := (global GameAdmin)
                }
            };
        ''')

    async def test_edgeql_permissions_basic_07(self):
        await self.con.execute('''
            CREATE TYPE T;
            INSERT T;
        ''')
        await self.con.execute('''
            ALTER TYPE T {
                CREATE REQUIRED PROPERTY foo -> bool {
                    SET default := (is_game_admin())
                }
            };
        ''')


class TestHttpPermissions(tb_http.EdgeQLTestCase):

    SCHEMA = os.path.join(
        os.path.dirname(__file__), 'schemas', 'cards.esdl'
    )

    # EdgeQL/HTTP queries cannot run in a transaction
    TRANSACTION_ISOLATION = False

    SETUP = '''
    CREATE FUNCTION is_game_admin() -> bool using(global GameAdmin);
    CREATE FUNCTION is_game_admin_nested() -> bool using(is_game_admin());

    CREATE FUNCTION is_game_admin_inlined_simple() -> bool {
        using(global GameAdmin);
        set is_inlined := true;
    };
    CREATE FUNCTION is_game_admin_inline_inner() -> bool {
        using(is_game_admin_inlined_simple());
    };
    CREATE FUNCTION is_game_admin_inline_outer() -> bool {
        using(is_game_admin());
        set is_inlined := true;
    };
    CREATE FUNCTION is_game_admin_inline_both() -> bool {
        using(is_game_admin_inlined_simple());
        set is_inlined := true;
    };

    CREATE REQUIRED GLOBAL some_flag -> int64 { set default := 0 };
    CREATE FUNCTION with_global() -> tuple<int64, bool> using (
        (global some_flag, global GameAdmin)
    );

    CREATE FUNCTION with_func_arg(n: int64) -> tuple<int64, bool> using (
        (n, global GameAdmin)
    );
    '''

    def test_http_permissions_errors_01(self):
        for use_http_post in [True, False]:
            with self.assertRaisesRegex(
                edgedb.InternalServerError,
                r"RuntimeError: Permission cannot be passed as globals: "
                r"'default::GameAdmin'",
            ):
                self.assert_edgeql_query_result(
                    'select global GameAdmin;',
                    # Tests run as superuser
                    [True,],
                    use_http_post=use_http_post,
                    globals={
                        'default::GameAdmin': True,
                    },
                )

    def test_http_permissions_01(self):
        for use_http_post in [True, False]:
            self.assert_edgeql_query_result(
                'select global GameAdmin;',
                # Tests run as superuser
                [True,],
                use_http_post=use_http_post,
                globals={
                    'default::some_flag': 1,
                },
            )

    def test_http_permissions_02(self):
        # Permission within functions
        function_names = [
            'is_game_admin',
            'is_game_admin_nested',
            'is_game_admin_inlined_simple',
            'is_game_admin_inline_inner',
            'is_game_admin_inline_outer',
            'is_game_admin_inline_both',
        ]
        for use_http_post in [True, False]:
            for function_name in function_names:
                with self.annotate(function_name=function_name):
                    self.assert_edgeql_query_result(
                        f'select {function_name}();',
                        # Tests run as superuser
                        [True,],
                        use_http_post=use_http_post,
                    )

    def test_http_permissions_03(self):
        # Permission within function that also uses global
        for use_http_post in [True, False]:
            self.assert_edgeql_query_result(
                f'select with_global();',
                # Tests run as superuser
                [(True, True)],
                use_http_post=use_http_post,
                globals={
                    'default::some_flag': 1,
                },
            )

    def test_http_permissions_04(self):
        # Permission within function that also has an argument
        for use_http_post in [True, False]:
            self.assert_edgeql_query_result(
                f'select with_func_arg(1);',
                # Tests run as superuser
                [(1, True)],
                use_http_post=use_http_post,
            )
            self.assert_edgeql_query_result(
                f'select with_func_arg(<int64>$param);',
                # Tests run as superuser
                [(1, True)],
                use_http_post=use_http_post,
                variables={
                    'param': 1,
                },
            )

    def test_http_permissions_05(self):
        # Permission within function that also has an argument
        for use_http_post in [True, False]:
            self.assert_edgeql_query_result(
                f'select global sys::current_role',
                # Tests run as superuser
                ['admin'],
                use_http_post=use_http_post,
            )
