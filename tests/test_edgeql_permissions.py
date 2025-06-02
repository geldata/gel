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


class TestEdgeQLPermissions(tb.QueryTestCase):
    '''Tests for permissions.'''

    SCHEMA = os.path.join(os.path.dirname(__file__), 'schemas',
                          'cards.esdl')

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
            r'''
                select global GameAdmin
            ''',
            [False],
        )
