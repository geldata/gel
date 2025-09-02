import pytest
import base64
from edb.testbase import server as tb
from gel.errors import InvalidValueError
import json

class TestEdgeQLBitwiseBytesFunctions(tb.QueryTestCase):
    
    async def _test_binary(self, query, expected):
        # Test binary format using raw connection
        result = await self.con.query_single(query)
        assert result == expected
    
    async def _test_json(self, query, expected):
        # Test JSON format using JSON protocol
        result = await self.con._fetchall_json(query)
        parsed = json.loads(result)
        assert parsed[0] == expected

    async def test_bytes_and(self):
        # Test basic AND operation
        await self._test_binary(
            r'''SELECT bytes_and(b'\xFF\x00', b'\x0F\x0F')''',
            b'\x0F\x00'
        )
        await self._test_json(
            r'''SELECT bytes_and(b'\xFF\x00', b'\x0F\x0F')''',
            'DwA='
        )

        # Test with zeros
        await self._test_binary(
            r'''SELECT bytes_and(b'\x00\x00', b'\xFF\xFF')''',
            b'\x00\x00'
        )

        # Test with all ones
        await self._test_binary(
            r'''SELECT bytes_and(b'\xFF\xFF', b'\xFF\xFF')''',
            b'\xFF\xFF'
        )

        # Test error on different lengths
        async with self.assertRaisesRegexTx(
            InvalidValueError,
            "bytes_and: bytes must be of equal length"
        ):
            await self.con.query(
                r'''SELECT bytes_and(b'\xFF', b'\xFF\xFF')'''
            )

    async def test_bytes_or(self):
        # Test basic OR operation
        await self._test_binary(
            r'''SELECT bytes_or(b'\xF0\x00', b'\x0F\x0F')''',
            b'\xFF\x0F'
        )
        await self._test_json(
            r'''SELECT bytes_or(b'\xF0\x00', b'\x0F\x0F')''',
            '/w8='
        )

        # Test with zeros
        await self._test_binary(
            r'''SELECT bytes_or(b'\x00\x00', b'\x00\x00')''',
            b'\x00\x00'
        )

        # Test with all ones
        await self._test_binary(
            r'''SELECT bytes_or(b'\xFF\xFF', b'\x00\x00')''',
            b'\xFF\xFF'
        )

        # Test error on different lengths
        async with self.assertRaisesRegexTx(
            InvalidValueError,
            "bytes_or: bytes must be of equal length"
        ):
            await self.con.query(
                r'''SELECT bytes_or(b'\xFF', b'\xFF\xFF')'''
            )

    async def test_bytes_xor(self):
        # Test basic XOR operation
        await self._test_binary(
            r'''SELECT bytes_xor(b'\xFF\x00', b'\x0F\x0F')''',
            b'\xF0\x0F'
        )
        await self._test_json(
            r'''SELECT bytes_xor(b'\xFF\x00', b'\x0F\x0F')''',
            '8A8='
        )

        # Test with zeros
        await self._test_binary(
            r'''SELECT bytes_xor(b'\xFF\xFF', b'\x00\x00')''',
            b'\xFF\xFF'
        )

        # Test with same values (should be zero)
        await self._test_binary(
            r'''SELECT bytes_xor(b'\xFF\xFF', b'\xFF\xFF')''',
            b'\x00\x00'
        )

        # Test error on different lengths
        async with self.assertRaisesRegexTx(
            InvalidValueError,
            "bytes_xor: bytes must be of equal length"
        ):
            await self.con.query(
                r'''SELECT bytes_xor(b'\xFF', b'\xFF\xFF')'''
            )

    async def test_bytes_not(self):
        # Test basic NOT operation
        await self._test_binary(
            r'''SELECT bytes_not(b'\xFF\x00')''',
            b'\x00\xFF'
        )
        await self._test_json(
            r'''SELECT bytes_not(b'\xFF\x00')''',
            'AP8='
        )

        # Test with all zeros
        await self._test_binary(
            r'''SELECT bytes_not(b'\x00\x00')''',
            b'\xFF\xFF'
        )

        # Test with all ones
        await self._test_binary(
            r'''SELECT bytes_not(b'\xFF\xFF')''',
            b'\x00\x00'
        )

    async def test_bytes_overlap(self):
        # Test overlapping bytes
        await self._test_binary(
            r'''SELECT bytes_overlap(b'\xFF\x00', b'\xFF\xFF')''',
            True
        )

        # Test non-overlapping bytes
        await self._test_binary(
            r'''SELECT bytes_overlap(b'\xF0\x00', b'\x0F\x00')''',
            False
        )

        # Test with zeros
        await self._test_binary(
            r'''SELECT bytes_overlap(b'\x00\x00', b'\xFF\xFF')''',
            False
        )

        # Test with all ones
        await self._test_binary(
            r'''SELECT bytes_overlap(b'\xFF\xFF', b'\xFF\xFF')''',
            True
        )

        # Test error on different lengths
        async with self.assertRaisesRegexTx(
            InvalidValueError,
            r"bytes_overlap\(\): bytes must be of equal length"
        ):
            await self.con.query(
                r'''SELECT bytes_overlap(b'\xFF', b'\xFF\xFF')'''
            )

    async def test_bytes_combinations(self):
        # Test combining multiple operations
        await self._test_binary(
            r'''SELECT bytes_and(
                bytes_or(b'\xF0\x00', b'\x0F\x0F'),
                bytes_xor(b'\xFF\x00', b'\x0F\x0F')
            )''',
            b'\xF0\x0F'
        )

        # Test with NOT operations
        await self._test_binary(
            r'''SELECT bytes_and(
                bytes_not(b'\x00\xFF'),
                b'\xFF\x00'
            )''',
            b'\xFF\x00'
        )

        # Test overlap with combined operations
        await self._test_binary(
            r'''SELECT bytes_overlap(
                bytes_and(b'\xFF\x00', b'\x0F\x0F'),
                bytes_or(b'\xF0\x00', b'\x0F\x0F')
            )''',
            True
        )