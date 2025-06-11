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

import json

import edgedb

from edb.testbase import server as tb


class TestServerPermissions(tb.ConnectedTestCase):

    PARALLELISM_GRANULARITY = 'system'
    TRANSACTION_ISOLATION = False

    async def test_server_permissions_role_01(self):
        # Check that superuser has permissions

        await self.con.query('''
            CREATE SUPERUSER ROLE foo {
                SET password := 'secret';
            };
            CREATE PERMISSION default::perm_a;
        ''')  # noqa

        try:
            conn = await self.connect(
                user='foo',
                password='secret',
            )

            result = await conn.query("""
                SELECT global default::perm_a;
            """)
            self.assert_data_shape(result, [True,])

        finally:
            await conn.aclose()
            await self.con.query('''
                DROP ROLE foo;
                DROP PERMISSION default::perm_a;
            ''')

    async def test_server_permissions_role_02(self):
        # Check that non-superuser has permissions

        await self.con.query('''
            CREATE ROLE foo {
                SET password := 'secret';
                SET permissions := default::perm_a;
            };
            CREATE PERMISSION default::perm_a;
            CREATE PERMISSION default::perm_b;
        ''')  # noqa

        try:
            conn = await self.connect(
                user='foo',
                password='secret',
            )

            result = await conn.query("""
                SELECT [
                    global default::perm_a,
                    global default::perm_b,
                ];
            """)
            self.assert_data_shape(result, [[True, False]])

        finally:
            await conn.aclose()
            await self.con.query('''
                DROP ROLE foo;
                DROP PERMISSION default::perm_a;
                DROP PERMISSION default::perm_b;
            ''')

    async def test_server_permissions_role_03(self):
        # Check that non-superuser has permissions

        await self.con.query('''
            CREATE ROLE base {
                SET password := 'secret';
                SET permissions := default::perm_a;
            };
            CREATE ROLE foo EXTENDING base {
                SET password := 'secret';
                SET permissions := default::perm_b;
            };
            CREATE PERMISSION default::perm_a;
            CREATE PERMISSION default::perm_b;
            CREATE PERMISSION default::perm_c;
        ''')  # noqa

        try:
            conn = await self.connect(
                user='foo',
                password='secret',
            )

            result = await conn.query("""
                SELECT [
                    global default::perm_a,
                    global default::perm_b,
                    global default::perm_c,
                ];
            """)
            self.assert_data_shape(result, [[True, True, False,]])

        finally:
            await conn.aclose()
            await self.con.query('''
                DROP ROLE foo;
                DROP ROLE base;
                DROP PERMISSION default::perm_a;
                DROP PERMISSION default::perm_b;
                DROP PERMISSION default::perm_c;
            ''')

    async def test_server_permissions_role_04(self):
        # Check that permissions are updated for existing connections

        await self.con.query('''
            CREATE ROLE foo {
                SET password := 'secret';
                SET permissions := default::perm_a;
            };
            CREATE PERMISSION default::perm_a;
            CREATE PERMISSION default::perm_b;
        ''')  # noqa

        try:
            conn = await self.connect(
                user='foo',
                password='secret',
            )

            result = await conn.query("""
                SELECT [
                    global default::perm_a,
                    global default::perm_b,
                ];
            """)
            self.assert_data_shape(result, [[True, False,]])

            await self.con.query('''
                ALTER ROLE foo {
                    SET permissions := default::perm_b;
                };
            ''')  # noqa

            result = await conn.query("""
                SELECT [
                    global default::perm_a,
                    global default::perm_b,
                ];
            """)
            self.assert_data_shape(result, [[False, True,]])

        finally:
            await conn.aclose()
            await self.con.query('''
                DROP ROLE foo;
                DROP PERMISSION default::perm_a;
                DROP PERMISSION default::perm_b;
            ''')

    async def test_server_permissions_role_05(self):
        # Check that non-superuser has permissions

        await self.con.query('''
            CREATE ROLE base {
                SET password := 'secret';
                SET permissions := default::perm_a;
            };
            CREATE ROLE foo EXTENDING base {
                SET password := 'secret';
                SET permissions := default::perm_b;
            };
            CREATE ROLE bar EXTENDING foo {
                SET password := 'secret';
            };
            CREATE PERMISSION default::perm_a;
            CREATE PERMISSION default::perm_b;
            CREATE PERMISSION default::perm_c;
        ''')  # noqa

        try:
            conn = await self.connect(
                user='bar',
                password='secret',
            )

            result = await conn.query("""
                SELECT [
                    global default::perm_a,
                    global default::perm_b,
                    global default::perm_c,
                ];
            """)
            self.assert_data_shape(result, [[True, True, False,]])

        finally:
            await conn.aclose()
            await self.con.query('''
                DROP ROLE bar;
                DROP ROLE foo;
                DROP ROLE base;
                DROP PERMISSION default::perm_a;
                DROP PERMISSION default::perm_b;
                DROP PERMISSION default::perm_c;
            ''')

    async def test_server_permissions_access_policy_01(self):
        # Check permission access policy works
        # with superuser

        await self.con.query('''
            CREATE SUPERUSER ROLE foo {
                SET password := 'secret';
            };
            CREATE PERMISSION default::perm_a;
            CREATE TYPE Widget {
                CREATE PROPERTY n -> int64;
                CREATE ACCESS POLICY readable
                    ALLOW SELECT;
                CREATE ACCESS POLICY with_perm
                    ALLOW INSERT
                    USING (global default::perm_a);
            };
        ''')  # noqa

        try:
            conn = await self.connect(
                user='foo',
                password='secret',
            )

            await conn.execute("""
                INSERT Widget { n := 1 };
            """)

            result = json.loads(await conn.query_json("""
                SELECT Widget { n } ORDER BY .n;
            """))
            self.assert_data_shape(result, [{'n': 1}])

        finally:
            await conn.aclose()
            await self.con.query('''
                DROP ROLE foo;
                DROP TYPE default::Widget;
                DROP PERMISSION default::perm_a;
            ''')

    async def test_server_permissions_access_policy_02(self):
        # Check permission access policy works
        # with non-superuser with permission

        await self.con.query('''
            CREATE ROLE foo {
                SET password := 'secret';
                SET permissions := default::perm_a;
            };
            CREATE PERMISSION default::perm_a;
            CREATE TYPE Widget {
                CREATE PROPERTY n -> int64;
                CREATE ACCESS POLICY readable
                    ALLOW SELECT;
                CREATE ACCESS POLICY with_perm
                    ALLOW INSERT
                    USING (global default::perm_a);
            };
        ''')  # noqa

        try:
            conn = await self.connect(
                user='foo',
                password='secret',
            )

            await conn.execute("""
                INSERT Widget { n := 1 };
            """)

            result = json.loads(await conn.query_json("""
                SELECT Widget { n } ORDER BY .n;
            """))
            self.assert_data_shape(result, [{'n': 1}])

        finally:
            await conn.aclose()
            await self.con.query('''
                DROP ROLE foo;
                DROP TYPE default::Widget;
                DROP PERMISSION default::perm_a;
            ''')

    async def test_server_permissions_access_policy_03(self):
        # Check permission access policy works
        # with non-superuser without permission

        await self.con.query('''
            CREATE ROLE foo {
                SET password := 'secret';
            };
            CREATE PERMISSION default::perm_a;
            CREATE TYPE Widget {
                CREATE PROPERTY n -> int64;
                CREATE ACCESS POLICY readable
                    ALLOW SELECT;
                CREATE ACCESS POLICY with_perm
                    ALLOW INSERT
                    USING (global default::perm_a);
            };
        ''')  # noqa

        try:
            conn = await self.connect(
                user='foo',
                password='secret',
            )

            with self.assertRaisesRegex(
                edgedb.AccessPolicyError,
                'access policy violation on insert of default::Widget'
            ):
                await conn.execute("""
                    INSERT Widget { n := 1 };
                """)

        finally:
            await conn.aclose()
            await self.con.query('''
                DROP ROLE foo;
                DROP TYPE default::Widget;
                DROP PERMISSION default::perm_a;
            ''')
