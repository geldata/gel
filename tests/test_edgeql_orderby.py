# This source file is part of the EdgeDB open source project.
#
# Tests for compiler warnings related to ORDER BY .id without EMPTY FIRST/LAST

from __future__ import annotations

from edb.testbase.server import ConnectedTestCase


class TestEdgeQLOrderBy(ConnectedTestCase):

    async def test_edgeql_orderby_id_warns_without_empty(self):
        # Ordering by .id with no EMPTY FIRST/LAST should emit a warning
        query = r"""
            SELECT User ORDER BY .id LIMIT 1;
        """
        with self.con.capture_warnings() as warnings:
            await self.con._fetchall_json(query)
        # Expect at least one warning mentioning ORDER BY .id and suggesting
        # adding EMPTY LAST
        self.assertTrue(
            any(
                ('ORDER BY .id' in str(w) and 'empty last' in (w.hint or '').lower())
                for w in warnings
            ),
            f"Expected ORDER BY .id empty-last warning, got: {[str(w) for w in warnings]}",
        )

    async def test_edgeql_orderby_id_empty_last_no_warning(self):
        # With EMPTY LAST specified there should be no warning
        query = r"""
            SELECT User ORDER BY .id EMPTY LAST LIMIT 1;
        """
        with self.con.capture_warnings() as warnings:
            await self.con._fetchall_json(query)
        self.assertFalse(
            any('ORDER BY .id' in str(w) for w in warnings),
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
            any('ORDER BY .id' in str(w) for w in warnings),
            f"Did not expect a warning for non-id ordering, got: {[str(w) for w in warnings]}",
        )
