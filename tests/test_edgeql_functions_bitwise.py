import pytest
from edb.testbase import server as tb

class TestEdgeQLBitwiseBytes(tb.QueryTestCase):
    
    async def test_bytes_and(self):
        await self.assert_query_result(
            '''SELECT bytes_and(b'\xff\x00', b'\x0f\x0f')''',
            [b'\x0f\x00'],
        )
        
        # Test error on different lengths
        async with self.assertRaisesRegexTx(
            "bytes_and.: byte strings must be of equal length"
        ):
            await self.con.query('''
                SELECT bytes_and(b'\xff', b'\x0f\x0f')
            ''')

    async def test_bytes_or(self):
        await self.assert_query_result(
            '''SELECT bytes_or(b'\xf0\x00', b'\x0f\x0f')''',
            [b'\xff\x0f'],
        )
        
        # Test error on different lengths
        async with self.assertRaisesRegexTx(
            "bytes_or.: byte strings must be of equal length"
        ):
            await self.con.query('''
                SELECT bytes_or(b'\xff', b'\x0f\x0f')
            ''')

    async def test_bytes_xor(self):
        await self.assert_query_result(
            '''SELECT bytes_xor(b'\xff\x00', b'\x0f\x0f')''',
            [b'\xf0\x0f'],
        )
        
        # Test error on different lengths
        async with self.assertRaisesRegexTx(
            "bytes_xor.: byte strings must be of equal length"
        ):
            await self.con.query('''
                SELECT bytes_xor(b'\xff', b'\x0f\x0f')
            ''')

    async def test_bytes_not(self):
        await self.assert_query_result(
            '''SELECT bytes_not(b'\xff\x00')''',
            [b'\x00\xff'],
        )

        await self.assert_query_result(
            '''SELECT bytes_not(b'\x0f\x0f')''',
            [b'\xf0\xf0'],
        )

    async def test_bytes_overlap(self):
        # Test case with no overlap
        await self.assert_query_result(
            '''SELECT bytes_overlap(b'\xf0\x00', b'\x0f\x00')''',
            [False],
        )

        # Test case with overlap
        await self.assert_query_result(
            '''SELECT bytes_overlap(b'\xff\xff', b'\x0f\x0f')''',
            [True],
        )

        # Test error on different lengths
        async with self.assertRaisesRegexTx(
            "bytes_overlap.: byte strings must be of equal length"
        ):
            await self.con.query('''
                SELECT bytes_overlap(b'\xff', b'\x0f\x0f')
            ''')