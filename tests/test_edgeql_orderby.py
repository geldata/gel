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


from __future__ import annotations

import os
from edb.testbase import server as tb


class TestEdgeQLOrderBy(tb.QueryTestCase):

    # Use the standard cards test schema so `User` exists.
    SCHEMA = os.path.join(os.path.dirname(__file__), 'schemas', 'cards.esdl')
    SETUP = os.path.join(
        os.path.dirname(__file__), 'schemas', 'cards_setup.edgeql'
    )

    async def test_edgeql_orderby_id_warns_without_empty(self):
        # Ordering by .id with no EMPTY FIRST/LAST should emit a warning
        query = r"""
            SELECT User ORDER BY .id LIMIT 1;
        """
        with self.con.capture_warnings() as warnings:
            await self.con._fetchall_json(query)
        # Expect at least one warning message about ORDER BY .id without EMPTY
        self.assertTrue(
            any(
                'ORDER BY .id without EMPTY FIRST/LAST' in str(w)
                for w in warnings
            ),
            f"Expected ORDER BY .id warning, got: {[str(w) for w in warnings]}",
        )

    async def test_edgeql_orderby_id_empty_last_no_warning(self):
        # With EMPTY LAST specified there should be no warning
        query = r"""
            SELECT User ORDER BY .id EMPTY LAST LIMIT 1;
        """
        with self.con.capture_warnings() as warnings:
            await self.con._fetchall_json(query)
        self.assertFalse(
            any(
                'ORDER BY .id without EMPTY FIRST/LAST' in str(w)
                for w in warnings
            ),
            f"Did not expect a warning for ORDER BY .id EMPTY LAST, got: {[str(w) for w in warnings]}",
        )

    async def test_edgeql_orderby_non_id_no_warning(self):
        # Ordering by a non-id property should not warn
        query = r"""
            SELECT User ORDER BY .name LIMIT 1;
        """
        with self.con.capture_warnings() as warnings:
            await self.con._fetchall_json(query)
        self.assertFalse(
            any(
                'ORDER BY .id without EMPTY FIRST/LAST' in str(w)
                for w in warnings
            ),
            f"Did not expect a warning for non-id ordering, got: {[str(w) for w in warnings]}",
        )

    async def test_edgeql_orderby_user_id_warns(self):
        # Qualified path to id should also warn
        query = r"""
            SELECT User ORDER BY User.id LIMIT 1;
        """
        with self.con.capture_warnings() as warnings:
            await self.con._fetchall_json(query)
        self.assertTrue(
            any(
                'ORDER BY .id without EMPTY FIRST/LAST' in str(w)
                for w in warnings
            ),
            f"Expected ORDER BY .id warning for qualified path, got: {[str(w) for w in warnings]}",
        )

    async def test_edgeql_orderby_with_module_id_warns(self):
        # Using WITH module default and qualified id
        query = r"""
            WITH MODULE default
            SELECT User ORDER BY User.id LIMIT 1;
        """
        with self.con.capture_warnings() as warnings:
            await self.con._fetchall_json(query)
        self.assertTrue(
            any(
                'ORDER BY .id without EMPTY FIRST/LAST' in str(w)
                for w in warnings
            ),
            f"Expected ORDER BY .id warning with WITH MODULE, got: {[str(w) for w in warnings]}",
        )
