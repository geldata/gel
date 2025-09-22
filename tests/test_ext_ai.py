#
# This source file is part of the EdgeDB open source project.
#
# Copyright 2023-present MagicStack Inc. and the EdgeDB authors.
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
import pathlib
import tempfile
import unittest

import edgedb

from edb.common import assert_data_shape

from edb.schema import indexes as s_indexes
from edb.server import args
from edb.server.protocol import ai_ext
from edb.testbase import http as tb_http
from edb.testbase import server as tb_server
from edb.tools import test


class TestExtAI(tb_http.BaseHttpExtensionTest):
    EXTENSIONS = ['pgvector', 'ai']
    BACKEND_SUPERUSER = True
    TRANSACTION_ISOLATION = False
    PARALLELISM_GRANULARITY = 'suite'

    SCHEMA = pathlib.Path(__file__).parent / 'schemas' / 'ext_ai.esdl'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mock_server = tb_http.MockHttpServer()
        cls.mock_server.start()
        base_url = cls.mock_server.get_base_url().rstrip("/")

        cls.mock_server.register_route_handler(
            "POST",
            base_url,
            "/v1/embeddings",
        )(cls.mock_api_embeddings)

        async def _setup():
            await cls.con.execute(
                f"""
                CONFIGURE CURRENT DATABASE
                INSERT ext::ai::CustomProviderConfig {{
                    name := 'custom::test',
                    secret := 'very secret',
                    api_url := '{base_url}/v1',
                    api_style := ext::ai::ProviderAPIStyle.OpenAI,
                }};

                CONFIGURE CURRENT DATABASE
                    SET ext::ai::Config::indexer_naptime := <duration>'100ms';
                """,
            )

            await cls._wait_for_db_config('ext::ai::Config::providers')

        cls.loop.run_until_complete(_setup())

    @classmethod
    def tearDownClass(cls):
        cls.mock_server.stop()
        super().tearDownClass()

    @classmethod
    def get_setup_script(cls):
        res = super().get_setup_script()

        # HACK: As a debugging cycle hack, when RELOAD is true, we reload the
        # extension package from the file, so we can test without a bootstrap.
        RELOAD = False

        if RELOAD:
            root = pathlib.Path(__file__).parent.parent
            with open(root / 'edb/lib/ext/ai.edgeql') as f:
                contents = f.read()
            to_add = (
                '''
                drop extension package ai version '1.0';
                create extension ai;
            '''
                + contents
            )
            splice = '__internal_testmode := true;'
            res = res.replace(splice, splice + to_add)

        return res

    _embeddings_log: list[list[str]] = []

    @classmethod
    def mock_api_embeddings(
        cls,
        handler: tb_http.MockHttpServerHandler,
        request_details: tb_http.RequestDetails,
    ) -> tb_http.ResponseType:
        assert request_details.body is not None
        inputs: list[str] = json.loads(request_details.body)['input']
        cls._embeddings_log.append(inputs)
        # Produce a dummy embedding as the number of occurences of the first ten
        # letters of the alphabet.
        response_data = [
            {
                "object": "embedding",
                "index": 0,
                "embedding": [
                    input.count(chr(ord('a') + c))
                    for c in range(10)
                ],
            }
            for input in inputs
        ]
        return (
            json.dumps({
                "object": "list",
                "data": response_data,
            }),
            200,
        )

    async def test_ext_ai_indexing_01(self):
        # Index on non-computed pointer
        try:
            await self.con.execute(
                """
                insert Astronomy {
                    content := 'Skies on Mars are red'
                };
                insert Astronomy {
                    content := 'Skies on Earth are blue'
                };
                """,
            )

            await self.assert_query_result(
                '''
                select _ := ext::ai::to_context((select Astronomy))
                order by _
                ''',
                [
                    'Skies on Earth are blue',
                    'Skies on Mars are red',
                ],
            )

            async for tr in self.try_until_succeeds(
                ignore=(AssertionError,),
                timeout=30.0,
            ):
                async with tr:
                    await self.assert_query_result(
                        r'''
                        with
                            result := ext::ai::search(
                                Astronomy, <array<float32>>$qv)
                        select
                            result.object {
                                content,
                                distance := result.distance,
                            }
                        order by
                            result.distance asc empty last
                            then result.object.content
                        ''',
                        [
                            {
                                'content': 'Skies on Earth are blue',
                                'distance': 0.3675444679663241,
                            },
                            {
                                'content': 'Skies on Mars are red',
                                'distance': 0.4284523933505918,
                            },
                        ],
                        variables={
                            "qv": [1 for i in range(10)],
                        }
                    )

        finally:
            await self.con.execute('''
                delete Astronomy;
            ''')

    async def test_ext_ai_indexing_02(self):
        # Index on expression
        try:
            qry = '''
                with
                    result := ext::ai::search(
                        OnExpression, <array<float32>>$qv)
                select
                    result.object {
                        content,
                        content2,
                        distance := result.distance,
                    }
                order by
                    result.distance asc empty last
                    then result.object.content;
            '''
            qv = [1 for i in range(10)]

            await self.assert_query_result(
                """
                insert OnExpression {
                    content := 'Skies on Mars',
                    content2 := ' are red',
                };
                insert OnExpression {
                    content := 'Skies on Earth',
                    content2 := ' are blue',
                };
                """ + qry,
                [],
                variables=dict(qv=qv),
            )

            await self.assert_query_result(
                '''
                select _ := ext::ai::to_context((select OnExpression))
                order by _
                ''',
                [
                    'Skies on Earth are blue',
                    'Skies on Mars are red',
                ],
            )

            async for tr in self.try_until_succeeds(
                ignore=(AssertionError,),
                timeout=30.0,
            ):
                async with tr:
                    await self.assert_query_result(
                        qry,
                        [
                            {
                                'content': 'Skies on Earth',
                                'content2': ' are blue',
                                'distance': 0.3675444679663241,
                            },
                            {
                                'content': 'Skies on Mars',
                                'content2': ' are red',
                                'distance': 0.4284523933505918,
                            },
                        ],
                        variables=dict(qv=qv),
                    )

            # updating an object should make it disappear from results.
            # (the read is done in the same tx, so there is no possible
            # race where the worker picks it up before the read)
            async for tr in self.try_until_succeeds(
                ignore=(
                    edgedb.TransactionConflictError,
                    edgedb.TransactionSerializationError,
                ),
                timeout=30.0,
            ):
                async with tr:
                    await self.assert_query_result(
                        """
                        update OnExpression filter .content like '%Earth'
                        set { content2 := ' are often grey' };
                        """ + qry,
                        [
                            {
                                'content': 'Skies on Mars',
                                'content2': ' are red',
                                'distance': 0.4284523933505918,
                            },
                        ],
                        variables=dict(qv=qv),
                    )

        finally:
            await self.con.execute('''
                delete OnExpression;
            ''')

    async def test_ext_ai_indexing_03(self):
        # Index on computed pointer
        try:
            qry = '''
                with
                    result := ext::ai::search(
                        OnComputed, <array<float32>>$qv)
                select
                    result.object {
                        content,
                        content2,
                        distance := result.distance,
                    }
                order by
                    result.distance asc empty last
                    then result.object.content;
            '''
            qv = [1 for i in range(10)]

            await self.assert_query_result(
                """
                insert OnComputed {
                    content := 'Skies on Mars',
                    content2 := ' are red',
                };
                insert OnComputed {
                    content := 'Skies on Earth',
                    content2 := ' are blue',
                };
                """ + qry,
                [],
                variables=dict(qv=qv),
            )

            await self.assert_query_result(
                '''
                select _ := ext::ai::to_context((select OnComputed))
                order by _
                ''',
                [
                    'Skies on Earth are blue',
                    'Skies on Mars are red',
                ],
            )

            async for tr in self.try_until_succeeds(
                ignore=(AssertionError,),
                timeout=30.0,
            ):
                async with tr:
                    await self.assert_query_result(
                        qry,
                        [
                            {
                                'content': 'Skies on Earth',
                                'content2': ' are blue',
                                'distance': 0.3675444679663241,
                            },
                            {
                                'content': 'Skies on Mars',
                                'content2': ' are red',
                                'distance': 0.4284523933505918,
                            },
                        ],
                        variables=dict(qv=qv),
                    )

            # updating an object should make it disappear from results.
            # (the read is done in the same tx, so there is no possible
            # race where the worker picks it up before the read)
            async for tr in self.try_until_succeeds(
                ignore=(
                    edgedb.TransactionConflictError,
                    edgedb.TransactionSerializationError,
                ),
                timeout=30.0,
            ):
                async with tr:
                    await self.assert_query_result(
                        """
                        update OnComputed filter .content like '%Earth'
                        set { content2 := ' are often grey' };
                        """ + qry,
                        [
                            {
                                'content': 'Skies on Mars',
                                'content2': ' are red',
                                'distance': 0.4284523933505918,
                            },
                        ],
                        variables=dict(qv=qv),
                    )

        finally:
            await self.con.execute('''
                delete OnComputed;
            ''')

    async def test_ext_ai_indexing_04(self):
        # Inherited index
        try:
            await self.con.execute(
                """
                insert Star {
                    content := 'Skies on Mars are red'
                };
                insert Supernova {
                    content := 'Skies on Earth are blue'
                };
                """,
            )

            await self.assert_query_result(
                '''
                select _ := ext::ai::to_context((select Star))
                order by _
                ''',
                [
                    'Skies on Earth are blue',
                    'Skies on Mars are red',
                ],
            )

            async for tr in self.try_until_succeeds(
                ignore=(AssertionError,),
                timeout=30.0,
            ):
                async with tr:
                    await self.assert_query_result(
                        r'''
                        with
                            result := ext::ai::search(
                                Star, <array<float32>>$qv)
                        select
                            result.object {
                                content,
                                distance := result.distance,
                            }
                        order by
                            result.distance asc empty last
                            then result.object.content
                        ''',
                        [
                            {
                                'content': 'Skies on Earth are blue',
                                'distance': 0.3675444679663241,
                            },
                            {
                                'content': 'Skies on Mars are red',
                                'distance': 0.4284523933505918,
                            },
                        ],
                        variables={
                            "qv": [1 for i in range(10)],
                        }
                    )

        finally:
            await self.con.execute('''
                delete Star;
                delete Supernova;
            ''')

    async def _assert_index_use(self, query, *args):
        def look(obj):
            if isinstance(obj, dict) and obj.get('plan_type') == "IndexScan":
                return any(
                    prop['title'] == 'index_name'
                    and f'ai::index' in prop['value']
                    for prop in obj.get('properties', [])
                )

            if isinstance(obj, dict):
                return any([look(v) for v in obj.values()])
            elif isinstance(obj, list):
                return any(look(v) for v in obj)
            else:
                return False

        async with self._run_and_rollback():
            await self.con.query_single(
                'select _set_config("enable_seqscan", "off")'
            )
            plan = await self.con.query_json(f'analyze {query};', *args)
        if not look(json.loads(plan)):
            raise AssertionError(f'query did not use ext::ai::index index')

    async def test_ext_ai_indexing_05(self):
        # Index use
        qv = [1.0, -2.0, 3.0, -4.0, 5.0, -6.0, 7.0, -8.0, 9.0, -10.0]

        await self._assert_index_use(
            f'''
            with vector := <array<float32>>$0
            select ext::ai::search(OnExpression, vector) limit 5;
            ''',
            qv,
        )
        await self._assert_index_use(
            f'''
            with vector := <array<float32>>$0
            select ext::ai::search(OnExpression, vector).object limit 5;
            ''',
            qv,
        )
        await self._assert_index_use(
            f'''
            select ext::ai::search(OnExpression, <array<float32>>$0) limit 5;
            ''',
            qv,
        )

        await self._assert_index_use(
            f'''
            with vector := <array<float32>><json>$0
            select ext::ai::search(OnExpression, vector) limit 5;
            ''',
            json.dumps(qv),
        )
        await self._assert_index_use(
            f'''
            select ext::ai::search(OnExpression, <array<float32>><json>$0)
            limit 5;
            ''',
            json.dumps(qv),
        )

    async def test_ext_ai_indexing_06(self):
        # Index on mixed inherited types
        try:
            await self.con.execute(
                """
                insert Astronomy {
                    content := 'Skies on Venus are orange'
                };
                insert OnExpression {
                    content := 'Skies on Mars',
                    content2 := ' are red',
                };
                insert OnComputed {
                    content := 'Skies on Pluto',
                    content2 := ' are black and starry',
                };
                insert Star {
                    content := 'Skies on Earth are blue'
                };
                """,
            )

            async for tr in self.try_until_succeeds(
                ignore=(AssertionError,),
                timeout=30.0,
            ):
                async with tr:
                    await self.assert_query_result(
                        r'''
                        with
                            result := ext::ai::search(
                                Astronomy, <array<float32>>$qv)
                        select
                            result.object {
                                content,
                                distance := result.distance,
                            }
                        order by
                            result.distance asc empty last
                            then result.object.content
                        ''',
                        [
                            {
                                'content': (
                                    'Skies on Pluto'
                                ),
                                'distance': 0.3545027756320972,
                            },
                            {
                                'content': 'Skies on Earth are blue',
                                'distance': 0.3675444679663241,
                            },
                            {
                                'content': 'Skies on Mars',
                                'distance': 0.4284523933505918,
                            },
                            {
                                'content': 'Skies on Venus are orange',
                                'distance': 0.4606401100294063,
                            },
                        ],
                        variables={
                            "qv": [1 for i in range(10)],
                        }
                    )

        finally:
            await self.con.execute('''
                delete Astronomy;
            ''')

    async def test_ext_ai_batch_embeddings_01(self):
        # Content that can be batched without being truncated
        #
        # Note:
        #   ai_ext.py: TestTokenizer counts each char as a separate token
        #   ext_ai.esdl: TestEmbeddingModel has a max input token length 100
        #   ext_ai.esdl: TestEmbeddingModel has a max batch token length 500

        content_prefix = 'batch_01_'
        entry_count = 20

        contents = [
            f"{content_prefix}{str(n).zfill(3)}{'a' * (50 + n)}"
            for n in range(entry_count)
        ]

        expected_batches = [
            [19, 0, 1, 2, 3, 4, 5],
            [18, 6, 7, 8, 9, 10],
            [17, 11, 12, 13, 14, 15],
            [16],
        ]

        try:
            await self.con.execute(
                f"""
                for c in {{{", ".join(f'"{c}"' for c in contents)}}}
                    insert Astronomy {{ content := c }};
                """,
            )

            async for tr in self.try_until_succeeds(
                ignore=(AssertionError,),
                timeout=30.0,
            ):
                async with tr:
                    await self.assert_query_result(
                        r'''
                        select count(
                            ext::ai::search(Astronomy, <array<float32>>$qv)
                        )
                        ''',
                        [entry_count],
                        variables={"qv": [1 for i in range(10)]}
                    )

        finally:
            await self.con.execute('''
                delete Astronomy;
            ''')

        # Check embeddings were batched correctly
        current_requests = [
            embeddings_request
            for embeddings_request in TestExtAI._embeddings_log
            if any(
                entry.startswith(content_prefix)
                for entry in embeddings_request
            )
        ]

        prefix_length = len(content_prefix)
        actual_batches = [
            [
                int(entry[prefix_length:prefix_length + 3])
                for entry in embeddings_request
            ]
            for embeddings_request in current_requests
        ]

        assert_data_shape.assert_data_shape(
            actual_batches,
            expected_batches,
            self.fail,
            message='Embeddings not batched correctly.'
        )

    async def test_ext_ai_batch_embeddings_02(self):
        # Content that can be batched, some entries are too long
        #
        # Note:
        #   ai_ext.py: TestTokenizer counts each char as a separate token
        #   ext_ai.esdl: TestEmbeddingModel has a max input token length 100
        #   ext_ai.esdl: TestEmbeddingModel has a max batch token length 500

        content_prefix = 'batch_02_'
        short_entry_count = 10
        long_entry_count = 10

        # 10 entries to get embeddings and 10 entries which are too long
        contents = (
            [
                f"{content_prefix}{str(n).zfill(3)}{'a' * (50 + n)}"
                for n in range(short_entry_count)
            ]
            + [
                f"{content_prefix}{str(n).zfill(3)}{'a' * (200 + n)}"
                for n in range(
                    short_entry_count,
                    short_entry_count + long_entry_count
                )
            ]
        )

        expected_batches = [
            [9, 0, 1, 2, 3, 4, 5],
            [8, 6, 7],
        ]

        try:
            await self.con.execute(
                f"""
                for c in {{{", ".join(f'"{c}"' for c in contents)}}}
                    insert Astronomy {{ content := c }};
                """,
            )

            async for tr in self.try_until_succeeds(
                ignore=(AssertionError,),
                timeout=30.0,
            ):
                async with tr:
                    await self.assert_query_result(
                        r'''
                        select count(
                            ext::ai::search(Astronomy, <array<float32>>$qv)
                        )
                        ''',
                        [short_entry_count],
                        variables={"qv": [1 for i in range(10)]}
                    )

        finally:
            await self.con.execute('''
                delete Astronomy;
            ''')

        # Check embeddings were batched correctly
        current_requests = [
            embeddings_request
            for embeddings_request in TestExtAI._embeddings_log
            if any(
                entry.startswith(content_prefix)
                for entry in embeddings_request
            )
        ]

        prefix_length = len(content_prefix)
        actual_batches = [
            [
                int(entry[prefix_length:prefix_length + 3])
                for entry in embeddings_request
            ]
            for embeddings_request in current_requests
        ]

        assert_data_shape.assert_data_shape(
            actual_batches,
            expected_batches,
            self.fail,
            message='Embeddings not batched correctly.'
        )

    async def test_ext_ai_batch_embeddings_03(self):
        # Content that can be batched, some entries to be truncated
        #
        # Note:
        #   ai_ext.py: TestTokenizer counts each char as a separate token
        #   ext_ai.esdl: TestEmbeddingModel has a max input token length 100
        #   ext_ai.esdl: TestEmbeddingModel has a max batch token length 500

        content_prefix = 'batch_03_'
        short_entry_count = 10
        long_entry_count = 10

        # 10 entries to get embeddings and 10 entries which are too long
        contents = (
            [
                f"{content_prefix}{str(n).zfill(3)}{'a' * (50 + n)}"
                for n in range(short_entry_count)
            ]
            + [
                f"{content_prefix}{str(n).zfill(3)}{'a' * (200 + n)}"
                for n in range(
                    short_entry_count,
                    short_entry_count + long_entry_count
                )
            ]
        )

        expected_batches = [
            [19, 0, 1, 2, 3, 4, 5],
            [18, 6, 7, 8, 9, 10],
            [17, 11, 12, 13, 14],
            [16, 15],
        ]

        try:
            await self.con.execute(
                f"""
                for c in {{{", ".join(f'"{c}"' for c in contents)}}}
                    insert Truncated {{ content := c }};
                """,
            )

            async for tr in self.try_until_succeeds(
                ignore=(AssertionError,),
                timeout=30.0,
            ):
                async with tr:
                    await self.assert_query_result(
                        r'''
                        select count(
                            ext::ai::search(Truncated, <array<float32>>$qv)
                        )
                        ''',
                        [short_entry_count + long_entry_count],
                        variables={"qv": [1 for i in range(10)]}
                    )

        finally:
            await self.con.execute('''
                delete Truncated;
            ''')

        # Check embeddings were batched correctly
        current_requests = [
            embeddings_request
            for embeddings_request in TestExtAI._embeddings_log
            if any(
                entry.startswith(content_prefix)
                for entry in embeddings_request
            )
        ]

        prefix_length = len(content_prefix)
        actual_batches = [
            [
                int(entry[prefix_length:prefix_length + 3])
                for entry in embeddings_request
            ]
            for embeddings_request in current_requests
        ]

        assert_data_shape.assert_data_shape(
            actual_batches,
            expected_batches,
            self.fail,
            message='Embeddings not batched correctly.'
        )

    async def test_ext_ai_index_custom_dimensions(self):
        await self.assert_query_result(
            """
            WITH
                Index := (
                    SELECT (
                        SELECT schema::ObjectType
                        FILTER .name = 'default::CustomDimensions').indexes
                    FILTER
                        .name = 'ext::ai::index'
                )
            SELECT
                Index {
                    annotations: {
                        @value
                    }
                    FILTER
                        .name = 'ext::ai::embedding_dimensions'
                }
            """,
            [{
                "annotations": [{
                    "@value": "9",
                }],
            }],
        )

    async def test_ext_ai_text_search_01(self):
        try:
            await self.con.execute(
                """
                insert Astronomy {
                    content := 'Skies on Venus are orange'
                };
                insert Astronomy {
                    content := 'Skies on Mars are red'
                };
                insert Astronomy {
                    content := 'Skies on Pluto are black and starry'
                };
                insert Astronomy {
                    content := 'Skies on Earth are blue'
                };
                """,
            )

            async for tr in self.try_until_succeeds(
                ignore=(AssertionError,),
                timeout=30.0,
            ):
                async with tr:
                    await self.assert_query_result(
                        r'''
                        with
                            result := ext::ai::search(
                                Astronomy, <str>$qv)
                        select
                            result.object {
                                content,
                                distance := result.distance,
                            }
                        order by
                            result.distance asc empty last
                            then result.object.content
                        ''',
                        [
                            {
                                'content': 'Skies on Earth are blue',
                                'distance': 0.09861218113400261,
                            },
                            {
                                'content': 'Skies on Venus are orange',
                                'distance': 0.11303140601637596,
                            },
                            {
                                'content': 'Skies on Mars are red',
                                'distance': 0.14066215115268055,
                            },
                            {
                                'content': (
                                    'Skies on Pluto are black and starry'
                                ),
                                'distance': 0.32063377951324246,
                            },
                        ],
                        variables={
                            "qv": "Nice weather",
                        }
                    )

        finally:
            await self.con.execute('''
                delete Astronomy;
            ''')

    async def test_ext_ai_text_search_02(self):
        # Ai text search calls batch their embeddings requests
        # with short inputs
        #
        # Some parameters are repeated.
        query_prefix = 'text_search_02_'

        try:
            await self.con.execute(
                """
                insert Astronomy {
                    content := 'Skies on Earth are blue'
                };
                """,
            )

            async for tr in self.try_until_succeeds(
                ignore=(AssertionError,),
                timeout=30.0,
            ):
                async with tr:
                    await self.assert_query_result(
                        f'''
                        select (
                            assert_single(ext::ai::search(
                                Astronomy, <str>$qa
                            ).distance),
                            assert_single(ext::ai::search(
                                Astronomy, <str>$qa
                            ).distance),
                            assert_single(ext::ai::search(
                                Astronomy, <str>$qb
                            ).distance),
                            assert_single(ext::ai::search(
                                Astronomy, <str>$qb
                            ).distance),
                            assert_single(ext::ai::search(
                                Astronomy, <str>$qb
                            ).distance),
                            assert_single(ext::ai::search(
                                Astronomy, <str>$qc
                            ).distance),
                            assert_single(ext::ai::search(
                                Astronomy, '{query_prefix + "Always night"}'
                            ).distance),
                            assert_single(ext::ai::search(
                                Astronomy, '{query_prefix + "Always night"}'
                            ).distance),
                        )
                        ''',
                        [(
                            0.10778218378080595,
                            0.10778218378080595,
                            0.350480947161671,
                            0.350480947161671,
                            0.350480947161671,
                            0.1513315752084945,
                            0.16085360832172635,
                            0.16085360832172635,
                        )],
                        variables={
                            "qa": query_prefix + "Nice weather",
                            "qb": query_prefix + "Lots of clouds",
                            "qc": query_prefix + "Dust everywhere",
                        }
                    )

        finally:
            await self.con.execute('''
                delete Astronomy;
            ''')

        # Check search embeddings were batched correctly
        current_requests = [
            embeddings_request
            for embeddings_request in TestExtAI._embeddings_log
            if any(
                entry.startswith(query_prefix)
                for entry in embeddings_request
            )
        ]

        prefix_length = len(query_prefix)
        actual_batches = [
            [
                entry[prefix_length:]
                for entry in embeddings_request
            ]
            for embeddings_request in current_requests
        ]

        # These will be embedded repeatedly in try_until_succeeds
        expected_batches = [[
            "Dust everywhere",
            "Always night",
            "Always night",
            "Nice weather",
            "Lots of clouds",
        ]]
        expected_batches = (
            expected_batches * (len(actual_batches) // len(expected_batches))
        )

        assert_data_shape.assert_data_shape(
            actual_batches,
            expected_batches,
            self.fail,
            message='Embeddings not batched correctly.'
        )

    async def test_ext_ai_text_search_03(self):
        # Ai text search calls batch their embeddings requests
        # with long inputs, no truncation needed
        #
        # Note:
        #   ai_ext.py: TestTokenizer counts each char as a separate token
        #   ext_ai.esdl: TestEmbeddingModel has a max input token length 100
        #   ext_ai.esdl: TestEmbeddingModel has a max batch token length 500
        query_prefix = 'text_search_03_'
        entry_count = 20

        queries = [
            f"{query_prefix}{str(n).zfill(3)}{'a' * (50 + n)}"
            for n in range(entry_count)
        ]

        try:
            await self.con.execute(
                """
                insert Astronomy {
                    content := 'Skies on Earth are blue'
                };
                """,
            )

            async for tr in self.try_until_succeeds(
                ignore=(AssertionError,),
                timeout=30.0,
            ):
                async with tr:
                    await self.assert_query_result(
                        f'''
                        select ({
                            ", ".join(
                                f"assert_single(ext::ai::search("
                                f"    Astronomy, <str>${n}"
                                f").distance)"
                                for n in range(len(queries))
                            )
                        })
                        ''',
                        [(
                            0.4663014891358067,
                            0.4669372419132616,
                            0.4675494836157368,
                            0.46813949300135127,
                            0.46870845787047366,
                            0.469257483000719,
                            0.4697875972666343,
                            0.47029976004002993,
                            0.4707948669542362,
                            0.4712737551047398,
                            0.471737207749386,
                            0.472185958563376,
                            0.47262069549743413,
                            0.4730420642816191,
                            0.47345067161213195,
                            0.47384708805405473,
                            0.4742318506890981,
                            0.4746054655340881,
                            0.4749684097530038,
                            0.4753211336828156,
                        )],
                        variables=tuple(queries)
                    )

        finally:
            await self.con.execute('''
                delete Astronomy;
            ''')

        # Check search embeddings were batched correctly
        current_requests = [
            embeddings_request
            for embeddings_request in TestExtAI._embeddings_log
            if any(
                entry.startswith(query_prefix)
                for entry in embeddings_request
            )
        ]

        prefix_length = len(query_prefix)
        actual_batches = [
            [
                int(entry[prefix_length:prefix_length + 3])
                for entry in embeddings_request
            ]
            for embeddings_request in current_requests
        ]

        # These will be embedded repeatedly in try_until_succeeds
        expected_batches = [
            [19, 0, 1, 2, 3, 4],
            [18, 5, 6, 7, 8, 9],
            [17, 10, 11, 12, 13, 14],
            [16, 15],
        ]
        expected_batches = (
            expected_batches * (len(actual_batches) // len(expected_batches))
        )

        assert_data_shape.assert_data_shape(
            actual_batches,
            expected_batches,
            self.fail,
            message='Embeddings not batched correctly.'
        )

    async def test_ext_ai_text_search_04(self):
        # Ai text search calls batch their embeddings requests
        # with long inputs, and truncation needed
        #
        # Note:
        #   ai_ext.py: TestTokenizer counts each char as a separate token
        #   ext_ai.esdl: TestEmbeddingModel has a max input token length 100
        #   ext_ai.esdl: TestEmbeddingModel has a max batch token length 500
        query_prefix = 'text_search_04_'
        short_entry_count = 10
        long_entry_count = 10

        # 10 entries to get embeddings and 10 entries which are too long
        contents = (
            [
                f"{query_prefix}{str(n).zfill(3)}{'a' * (50 + n)}"
                for n in range(short_entry_count)
            ]
            + [
                f"{query_prefix}{str(n).zfill(3)}{'a' * (200 + n)}"
                for n in range(
                    short_entry_count,
                    short_entry_count + long_entry_count
                )
            ]
        )

        try:
            await self.con.execute(
                """
                insert Truncated {
                    content := 'Skies on Earth are blue'
                };
                """,
            )

            async for tr in self.try_until_succeeds(
                ignore=(AssertionError,),
                timeout=30.0,
            ):
                async with tr:
                    await self.assert_query_result(
                        f'''
                        select ({
                            ", ".join(
                                f"assert_single(ext::ai::search("
                                f"    Truncated, <str>${n}"
                                f").distance)"
                                for n in range(len(contents))
                            )
                        })
                        ''',
                        [(
                            0.4663014891358067,
                            0.4669372419132616,
                            0.4675494836157368,
                            0.46813949300135127,
                            0.46870845787047366,
                            0.469257483000719,
                            0.4697875972666343,
                            0.47029976004002993,
                            0.4707948669542362,
                            0.4712737551047398,
                            0.47914243469471374,
                            0.47914243469471374,
                            0.47914243469471374,
                            0.47914243469471374,
                            0.47914243469471374,
                            0.47914243469471374,
                            0.47914243469471374,
                            0.47914243469471374,
                            0.47914243469471374,
                            0.47914243469471374,
                        )],
                        variables=tuple(contents)
                    )

        finally:
            await self.con.execute('''
                delete Truncated;
            ''')

        # Check search embeddings were batched correctly
        current_requests = [
            embeddings_request
            for embeddings_request in TestExtAI._embeddings_log
            if any(
                entry.startswith(query_prefix)
                for entry in embeddings_request
            )
        ]

        prefix_length = len(query_prefix)
        actual_batches = [
            [
                int(entry[prefix_length:prefix_length + 3])
                for entry in embeddings_request
            ]
            for embeddings_request in current_requests
        ]

        # These will be embedded repeatedly in try_until_succeeds
        expected_batches = [
            [19, 0, 1, 2, 3, 4],
            [18, 5, 6, 7, 8, 9],
            [17, 10, 11, 12, 13],
            [16, 14, 15],
        ]
        expected_batches = (
            expected_batches * (len(actual_batches) // len(expected_batches))
        )

        assert_data_shape.assert_data_shape(
            actual_batches,
            expected_batches,
            self.fail,
            message='Embeddings not batched correctly.'
        )

    async def test_ext_ai_text_search_05(self):
        # Ai text search calls batch their embeddings requests
        # with long inputs, and truncation not allowed
        #
        # Note:
        #   ai_ext.py: TestTokenizer counts each char as a separate token
        #   ext_ai.esdl: TestEmbeddingModel has a max input token length 100
        #   ext_ai.esdl: TestEmbeddingModel has a max batch token length 500
        query_prefix = 'text_search_05_'
        short_entry_count = 10
        long_entry_count = 10

        # 10 entries to get embeddings and 10 entries which are too long
        contents = (
            [
                f"{query_prefix}{str(n).zfill(3)}{'a' * (50 + n)}"
                for n in range(short_entry_count)
            ]
            + [
                f"{query_prefix}{str(n).zfill(3)}{'a' * (200 + n)}"
                for n in range(
                    short_entry_count,
                    short_entry_count + long_entry_count
                )
            ]
        )

        try:
            await self.con.execute(
                """
                insert Astronomy {
                    content := 'Skies on Earth are blue'
                };
                """,
            )

            async with self.assertRaisesRegexTx(
                edgedb.QueryError,
                r"Search text exceeds maximum input token length: "
                r"text_search_05_"
            ):
                await self.con.execute(
                    f'''
                    select ({
                        ", ".join(
                            f"assert_single(ext::ai::search("
                            f"    Astronomy, <str>${n}"
                            f").distance)"
                            for n in range(len(contents))
                        )
                    })
                    ''',
                    *contents
                )

        finally:
            await self.con.execute('''
                delete Truncated;
            ''')


class CharacterTokenizer(ai_ext.Tokenizer):
    def encode(self, text: str) -> list[int]:
        return [ord(c) for c in text]

    def encode_padding(self) -> int:
        return 0

    def decode(self, tokens: list[int]) -> str:
        return str(chr(t) for t in tokens)


class TestExtAIUtils(unittest.TestCase):

    def test_batch_embeddings_inputs_01(self):
        self.assertEqual(
            ai_ext._batch_embeddings_inputs(
                CharacterTokenizer(),
                [],
                10
            ),
            [],
        )
        self.assertEqual(
            ai_ext._batch_embeddings_inputs(
                CharacterTokenizer(),
                ['1', '22', '333', '4444'],
                10
            ),
            [([3, 0, 1, 2], 10)],
        )
        self.assertEqual(
            ai_ext._batch_embeddings_inputs(
                CharacterTokenizer(),
                ['1', '22', '333', '4444', '55555'],
                10
            ),
            [
                ([4, 0, 1], 8),
                ([3, 2], 7),
            ],
        )
        self.assertEqual(
            ai_ext._batch_embeddings_inputs(
                CharacterTokenizer(),
                ['1', '22', '333', '4444', '55555', '666666'],
                10
            ),
            [
                ([5, 0, 1], 9),
                ([4, 2], 8),
                ([3], 4),
            ],
        )
        self.assertEqual(
            ai_ext._batch_embeddings_inputs(
                CharacterTokenizer(),
                ['1', '22', '333', '4444', '55555', '666666'],
                10
            ),
            [
                ([5, 0, 1], 9),
                ([4, 2], 8),
                ([3], 4),
            ],
        )
        self.assertEqual(
            ai_ext._batch_embeddings_inputs(
                CharacterTokenizer(),
                ['1', '22', '333', '4444', '55555', '121212121212'],
                10
            ),
            [
                ([4, 0, 1], 8),
                ([3, 2], 7),
            ],
        )
        # Text is alphabetically ordered to ensure consistent batching
        self.assertEqual(
            ai_ext._batch_embeddings_inputs(
                CharacterTokenizer(),
                ['AAA', 'CCC', 'EEE', 'BBB', 'DDD'],
                10
            ),
            [
                ([2, 0, 3], 9),
                ([4, 1], 6),
            ],
        )


class TestExtAIDDL(tb_server.DDLTestCase):

    @test.xfail('''
        We need to add a check for duplicate model names
    ''')
    async def test_ext_ai_ddl_error_01(self):
        # Add model type when URI generated type exists
        await self.con.execute("""
            CREATE TYPE Foo {
                CREATE PROPERTY content: str;
            };
            CREATE EXTENSION pgvector;
            CREATE EXTENSION ai;
            CREATE ABSTRACT TYPE OriginalModel
                EXTENDING ext::ai::EmbeddingModel
            {
                ALTER ANNOTATION ext::ai::model_name
                    := "with-builtin-provider";
                ALTER ANNOTATION ext::ai::model_provider
                    := "builtin::ollama";
                ALTER ANNOTATION ext::ai::embedding_model_max_input_tokens
                    := "8192";
                ALTER ANNOTATION ext::ai::embedding_model_max_batch_tokens
                    := "8192";
                ALTER ANNOTATION ext::ai::embedding_model_max_output_dimensions
                    := "1024";
            };
        """)

        await self.con.execute("""
            ALTER TYPE Foo {
                CREATE DEFERRED INDEX ext::ai::index(
                    embedding_model := 'with-builtin-provider'
                ) ON (.content);
            };
        """)

        with self.assertRaisesRegex(
            edgedb.SchemaDefinitionError,
            r"An embedding model with that model name already exists."
        ):
            await self.con.execute("""
                CREATE ABSTRACT TYPE DuplicateModel
                    EXTENDING ext::ai::EmbeddingModel
                {
                    ALTER ANNOTATION ext::ai::model_name
                        := "with-builtin-provider";
                    ALTER ANNOTATION ext::ai::model_provider
                        := "builtin::ollama";
                    ALTER ANNOTATION ext::ai::embedding_model_max_input_tokens
                        := "8192";
                    ALTER ANNOTATION ext::ai::embedding_model_max_batch_tokens
                        := "8192";
                    ALTER ANNOTATION
                        ext::ai::embedding_model_max_output_dimensions
                        := "1024";
                };
            """)

    async def _assert_generated_models(
        self,
        model_descs: list[s_indexes.EmbeddingModelDesc],
        *,
        con=None,
    ):
        if con is None:
            con = self.con

        expected = [
            {
                "name": (
                    f"__ext_generated_types__::ai_embedding_"
                    f"{model_desc.model_provider.split(':')[-1]}_"
                    f"{model_desc.model_name}"
                ),
                "annotations": [
                    {
                        "name": "ext::ai::model_name",
                        "@value": model_desc.model_name,
                    },
                    {
                        "name": "ext::ai::model_provider",
                        "@value": model_desc.model_provider,
                    },
                    {
                        "name": "ext::ai::embedding_model_max_input_tokens",
                        "@value": str(model_desc.max_input_tokens),
                    },
                    {
                        "name": "ext::ai::embedding_model_max_batch_tokens",
                        "@value": str(model_desc.max_batch_tokens),
                    },
                    {
                        "name": (
                            "ext::ai::embedding_model_max_output_dimensions"
                        ),
                        "@value": str(model_desc.max_output_dimensions),
                    },
                    {
                        "name": (
                            "ext::ai::embedding_model_supports_shortening"
                        ),
                        "@value": (
                            str(model_desc.supports_shortening).lower()
                        ),
                    },
                ]
            }
            for model_desc in model_descs
        ]

        res = await con._fetchall_json(
            '''
            select schema::ObjectType {
                name,
                annotations: { name, @value }
            }
            filter contains(.name, '__ext_generated_types__')
            order by .name
            ''',
        )
        actual = json.loads(res)
        assert_data_shape.assert_data_shape(
            actual, expected, self.fail,
        )

    async def test_ext_ai_ddl_uri_01(self):
        # Builtin provider and builtin embedding model
        await self.con.execute("""
            CREATE TYPE Foo {
                CREATE PROPERTY content: str;
            };
            CREATE EXTENSION pgvector;
            CREATE EXTENSION ai;
        """)

        await self.con.execute("""
            ALTER TYPE Foo {
                CREATE DEFERRED INDEX ext::ai::index(
                    embedding_model := 'openai:text-embedding-3-small'
                ) ON (.content);
            };
        """)
        await self._assert_generated_models([])

        await self.con.execute("""
            ALTER TYPE Foo {
                DROP INDEX ext::ai::index(
                    embedding_model := 'openai:text-embedding-3-small'
                ) ON (.content);
            };
        """)
        await self._assert_generated_models([])

    async def test_ext_ai_ddl_uri_02(self):
        # Builtin provider and custom embedding model
        await self.con.execute("""
            CREATE TYPE Foo {
                CREATE PROPERTY content: str;
            };
            CREATE EXTENSION pgvector;
            CREATE EXTENSION ai;
            CREATE ABSTRACT TYPE NotInReference
                EXTENDING ext::ai::EmbeddingModel
            {
                ALTER ANNOTATION ext::ai::model_name
                    := "not-in-reference";
                ALTER ANNOTATION ext::ai::model_provider
                    := "builtin::ollama";
                ALTER ANNOTATION ext::ai::embedding_model_max_input_tokens
                    := "8192";
                ALTER ANNOTATION ext::ai::embedding_model_max_batch_tokens
                    := "8192";
                ALTER ANNOTATION ext::ai::embedding_model_max_output_dimensions
                    := "1024";
            };
        """)

        await self.con.execute("""
            ALTER TYPE Foo {
                CREATE DEFERRED INDEX ext::ai::index(
                    embedding_model := 'ollama:not-in-reference'
                ) ON (.content);
            };
        """)
        await self._assert_generated_models([])

        await self.con.execute("""
            ALTER TYPE Foo {
                DROP INDEX ext::ai::index(
                    embedding_model := 'ollama:not-in-reference'
                ) ON (.content);
            };
        """)
        await self._assert_generated_models([])

    async def test_ext_ai_ddl_uri_03(self):
        # Builtin provider and reference embedding model
        # User generated model type
        await self.con.execute("""
            CREATE TYPE Foo {
                CREATE PROPERTY content: str;
            };
            CREATE EXTENSION pgvector;
            CREATE EXTENSION ai;
            CREATE ABSTRACT TYPE FromReference
                EXTENDING ext::ai::EmbeddingModel
            {
                ALTER ANNOTATION ext::ai::model_name
                    := "with-builtin-provider";
                ALTER ANNOTATION ext::ai::model_provider
                    := "builtin::ollama";
                ALTER ANNOTATION ext::ai::embedding_model_max_input_tokens
                    := "8192";
                ALTER ANNOTATION ext::ai::embedding_model_max_batch_tokens
                    := "8192";
                ALTER ANNOTATION ext::ai::embedding_model_max_output_dimensions
                    := "1024";
            };
        """)

        await self.con.execute("""
            ALTER TYPE Foo {
                CREATE DEFERRED INDEX ext::ai::index(
                    embedding_model := 'ollama:with-builtin-provider'
                ) ON (.content);
            };
        """)
        await self._assert_generated_models([])

        await self.con.execute("""
            ALTER TYPE Foo {
                DROP INDEX ext::ai::index(
                    embedding_model := 'ollama:with-builtin-provider'
                ) ON (.content);
            };
        """)
        await self._assert_generated_models([])

    async def test_ext_ai_ddl_uri_04(self):
        # Builtin provider and reference embedding model
        # Creates new model type when created and drops it when removed
        await self.con.execute("""
            CREATE TYPE Foo {
                CREATE PROPERTY content: str;
            };
            CREATE EXTENSION pgvector;
            CREATE EXTENSION ai;
        """)

        await self.con.execute("""
            ALTER TYPE Foo {
                CREATE DEFERRED INDEX ext::ai::index(
                    embedding_model := 'ollama:with-builtin-provider'
                ) ON (.content);
            };
        """)
        await self._assert_generated_models([
            s_indexes.EmbeddingModelDesc(
                model_name='with-builtin-provider',
                model_provider='builtin::ollama',
                max_input_tokens=101,
                max_batch_tokens=501,
                max_output_dimensions=11,
                supports_shortening=True,
            )
        ])

        await self.con.execute("""
            ALTER TYPE Foo {
                DROP INDEX ext::ai::index(
                    embedding_model := 'ollama:with-builtin-provider'
                ) ON (.content);
            };
        """)
        await self._assert_generated_models([])

    async def test_ext_ai_ddl_uri_05(self):
        # Custom provider and reference embedding model
        # Creates new model type when created and drops it when removed
        await self.con.execute("""
            CREATE TYPE Foo {
                CREATE PROPERTY content: str;
            };
            CREATE EXTENSION pgvector;
            CREATE EXTENSION ai;
        """)

        await self.con.execute("""
            ALTER TYPE Foo {
                CREATE DEFERRED INDEX ext::ai::index(
                    embedding_model := 'test:with-custom-provider'
                ) ON (.content);
            };
        """)
        await self._assert_generated_models([
            s_indexes.EmbeddingModelDesc(
                model_name='with-custom-provider',
                model_provider='test',
                max_input_tokens=102,
                max_batch_tokens=502,
                max_output_dimensions=12,
                supports_shortening=False,
            )
        ])

        await self.con.execute("""
            ALTER TYPE Foo {
                DROP INDEX ext::ai::index(
                    embedding_model := 'test:with-custom-provider'
                ) ON (.content);
            };
        """)
        await self._assert_generated_models([])

    async def test_ext_ai_ddl_uri_06(self):
        # Custom provider and custom embedding model
        await self.con.execute("""
            CREATE TYPE Foo {
                CREATE PROPERTY content: str;
            };
            CREATE EXTENSION pgvector;
            CREATE EXTENSION ai;
            CREATE ABSTRACT TYPE NotInReference
                EXTENDING ext::ai::EmbeddingModel
            {
                ALTER ANNOTATION ext::ai::model_name
                    := "not-in-reference";
                ALTER ANNOTATION ext::ai::model_provider
                    := "custom-provider";
                ALTER ANNOTATION ext::ai::embedding_model_max_input_tokens
                    := "123";
                ALTER ANNOTATION ext::ai::embedding_model_max_batch_tokens
                    := "456";
                ALTER ANNOTATION ext::ai::embedding_model_max_output_dimensions
                    := "78";
            };
        """)

        await self.con.execute("""
            ALTER TYPE Foo {
                CREATE DEFERRED INDEX ext::ai::index(
                    embedding_model := 'custom-provider:not-in-reference'
                ) ON (.content);
            };
        """)
        await self._assert_generated_models([])

        await self.con.execute("""
            ALTER TYPE Foo {
                DROP INDEX ext::ai::index(
                    embedding_model := 'custom-provider:not-in-reference'
                ) ON (.content);
            };
        """)
        await self._assert_generated_models([])

    async def test_ext_ai_ddl_uri_07(self):
        # Builtin provider and reference embedding model

        # Multiple indexes with same reference embedding model
        await self.con.execute("""
            CREATE TYPE Foo {
                CREATE PROPERTY content: str;
            };
            CREATE TYPE Bar {
                CREATE PROPERTY content: str;
            };
            CREATE EXTENSION pgvector;
            CREATE EXTENSION ai;
        """)

        await self.con.execute("""
            ALTER TYPE Foo {
                CREATE DEFERRED INDEX ext::ai::index(
                    embedding_model := 'ollama:my-model-1'
                ) ON (.content);
            };
        """)
        await self._assert_generated_models([
            s_indexes.EmbeddingModelDesc(
                model_name='my-model-1',
                model_provider='builtin::ollama',
                max_input_tokens=103,
                max_batch_tokens=503,
                max_output_dimensions=13,
                supports_shortening=False,
            )
        ])

        await self.con.execute("""
            ALTER TYPE Bar {
                CREATE DEFERRED INDEX ext::ai::index(
                    embedding_model := 'ollama:my-model-1'
                ) ON (.content);
            };
        """)
        await self._assert_generated_models([
            s_indexes.EmbeddingModelDesc(
                model_name='my-model-1',
                model_provider='builtin::ollama',
                max_input_tokens=103,
                max_batch_tokens=503,
                max_output_dimensions=13,
                supports_shortening=False,
            )
        ])

        await self.con.execute("""
            ALTER TYPE Foo {
                DROP INDEX ext::ai::index(
                    embedding_model := 'ollama:my-model-1'
                ) ON (.content);
            };
        """)
        await self._assert_generated_models([
            s_indexes.EmbeddingModelDesc(
                model_name='my-model-1',
                model_provider='builtin::ollama',
                max_input_tokens=103,
                max_batch_tokens=503,
                max_output_dimensions=13,
                supports_shortening=False,
            )
        ])

        await self.con.execute("""
            ALTER TYPE Bar {
                DROP INDEX ext::ai::index(
                    embedding_model := 'ollama:my-model-1'
                ) ON (.content);
            };
        """)
        await self._assert_generated_models([])

    async def test_ext_ai_ddl_uri_08(self):
        # Builtin provider and reference embedding model

        # Multiple indexes with difference reference embedding model
        await self.con.execute("""
            CREATE TYPE Foo {
                CREATE PROPERTY content: str;
            };
            CREATE TYPE Bar {
                CREATE PROPERTY content: str;
            };
            CREATE EXTENSION pgvector;
            CREATE EXTENSION ai;
        """)

        await self.con.execute("""
            ALTER TYPE Foo {
                CREATE DEFERRED INDEX ext::ai::index(
                    embedding_model := 'ollama:my-model-1'
                ) ON (.content);
            };
        """)
        await self._assert_generated_models([
            s_indexes.EmbeddingModelDesc(
                model_name='my-model-1',
                model_provider='builtin::ollama',
                max_input_tokens=103,
                max_batch_tokens=503,
                max_output_dimensions=13,
                supports_shortening=False,
            )
        ])

        await self.con.execute("""
            ALTER TYPE Bar {
                CREATE DEFERRED INDEX ext::ai::index(
                    embedding_model := 'ollama:my-model-2'
                ) ON (.content);
            };
        """)
        await self._assert_generated_models([
            s_indexes.EmbeddingModelDesc(
                model_name='my-model-1',
                model_provider='builtin::ollama',
                max_input_tokens=103,
                max_batch_tokens=503,
                max_output_dimensions=13,
                supports_shortening=False,
            ),
            s_indexes.EmbeddingModelDesc(
                model_name='my-model-2',
                model_provider='builtin::ollama',
                max_input_tokens=104,
                max_batch_tokens=504,
                max_output_dimensions=14,
                supports_shortening=False,
            ),
        ])

        await self.con.execute("""
            ALTER TYPE Foo {
                DROP INDEX ext::ai::index(
                    embedding_model := 'ollama:my-model-1'
                ) ON (.content);
            };
        """)
        await self._assert_generated_models([
            s_indexes.EmbeddingModelDesc(
                model_name='my-model-2',
                model_provider='builtin::ollama',
                max_input_tokens=104,
                max_batch_tokens=504,
                max_output_dimensions=14,
                supports_shortening=False,
            )
        ])

        await self.con.execute("""
            ALTER TYPE Bar {
                DROP INDEX ext::ai::index(
                    embedding_model := 'ollama:my-model-2'
                ) ON (.content);
            };
        """)
        await self._assert_generated_models([])

    async def test_ext_ai_ddl_uri_error_01(self):
        # URI with mismatched provider and model
        await self.con.execute("""
            CREATE TYPE Foo {
                CREATE PROPERTY content: str;
            };
            CREATE EXTENSION pgvector;
            CREATE EXTENSION ai;
        """)

        with self.assertRaisesRegex(
            edgedb.SchemaDefinitionError,
            r"An embedding model with the name 'text-embedding-3-small' exists "
            r"but the provider specified by the index \('anthropic'\) "
            r"differs from the one specified by the model \('openai'\)\."
        ):
            await self.con.execute("""
                ALTER TYPE Foo {
                    CREATE DEFERRED INDEX ext::ai::index(
                        embedding_model := 'anthropic:text-embedding-3-small'
                    ) ON (.content);
                };
            """)

    async def test_ext_ai_ddl_uri_error_02(self):
        # URI with unknown provider
        await self.con.execute("""
            CREATE TYPE Foo {
                CREATE PROPERTY content: str;
            };
            CREATE EXTENSION pgvector;
            CREATE EXTENSION ai;
        """)

        with self.assertRaisesRegex(
            edgedb.SchemaDefinitionError,
            r"An embedding model with the name 'text-embedding-3-small' exists "
            r"but the provider specified by the index \('unknown'\) "
            r"differs from the one specified by the model \('openai'\)\."
        ):
            await self.con.execute("""
                ALTER TYPE Foo {
                    CREATE DEFERRED INDEX ext::ai::index(
                        embedding_model := 'unknown:text-embedding-3-small'
                    ) ON (.content);
                };
            """)

    async def test_ext_ai_ddl_uri_error_03(self):
        # URI with unknown model
        await self.con.execute("""
            CREATE TYPE Foo {
                CREATE PROPERTY content: str;
            };
            CREATE EXTENSION pgvector;
            CREATE EXTENSION ai;
        """)

        with self.assertRaisesRegex(
            edgedb.SchemaDefinitionError,
            r"undefined embedding model: no subtype of "
            r"ext::ai::EmbeddingModel is annotated as 'unknown'"
        ):
            await self.con.execute("""
                ALTER TYPE Foo {
                    CREATE DEFERRED INDEX ext::ai::index(
                        embedding_model := 'openai:unknown'
                    ) ON (.content);
                };
            """)

    async def test_ext_ai_ddl_uri_error_04(self):
        # URI with unknown provider and model
        await self.con.execute("""
            CREATE TYPE Foo {
                CREATE PROPERTY content: str;
            };
            CREATE EXTENSION pgvector;
            CREATE EXTENSION ai;
        """)

        with self.assertRaisesRegex(
            edgedb.SchemaDefinitionError,
            r"undefined embedding model: no subtype of "
            r"ext::ai::EmbeddingModel is annotated as 'unknown'"
        ):
            await self.con.execute("""
                ALTER TYPE Foo {
                    CREATE DEFERRED INDEX ext::ai::index(
                        embedding_model := 'unknown:unknown'
                    ) ON (.content);
                };
            """)

    @test.xfail('''
        We need to add a check for duplicate model names
    ''')
    async def test_ext_ai_ddl_uri_error_05(self):
        # Add model type when URI generated type exists
        await self.con.execute("""
            CREATE TYPE Foo {
                CREATE PROPERTY content: str;
            };
            CREATE EXTENSION pgvector;
            CREATE EXTENSION ai;
        """)

        await self.con.execute("""
            ALTER TYPE Foo {
                CREATE DEFERRED INDEX ext::ai::index(
                    embedding_model := 'ollama:with-builtin-provider'
                ) ON (.content);
            };
        """)

        with self.assertRaisesRegex(
            edgedb.SchemaDefinitionError,
            r"undefined embedding model: no subtype of "
            r"ext::ai::EmbeddingModel is annotated as 'unknown'"
        ):
            await self.con.execute("""
                CREATE ABSTRACT TYPE MyModel
                    EXTENDING ext::ai::EmbeddingModel
                {
                    ALTER ANNOTATION ext::ai::model_name
                        := "with-builtin-provider";
                    ALTER ANNOTATION ext::ai::model_provider
                        := "builtin::ollama";
                    ALTER ANNOTATION ext::ai::embedding_model_max_input_tokens
                        := "8192";
                    ALTER ANNOTATION ext::ai::embedding_model_max_batch_tokens
                        := "8192";
                    ALTER ANNOTATION
                        ext::ai::embedding_model_max_output_dimensions
                        := "1024";
                };
            """)

    async def test_ext_ai_ddl_uri_error_06(self):
        # Drop model type when referred to by URI index
        # Model in reference
        await self.con.execute("""
            CREATE TYPE Foo {
                CREATE PROPERTY content: str;
            };
            CREATE EXTENSION pgvector;
            CREATE EXTENSION ai;
            CREATE ABSTRACT TYPE FromReference
                EXTENDING ext::ai::EmbeddingModel
            {
                ALTER ANNOTATION ext::ai::model_name
                    := "with-builtin-provider";
                ALTER ANNOTATION ext::ai::model_provider
                    := "builtin::ollama";
                ALTER ANNOTATION ext::ai::embedding_model_max_input_tokens
                    := "8192";
                ALTER ANNOTATION ext::ai::embedding_model_max_batch_tokens
                    := "8192";
                ALTER ANNOTATION ext::ai::embedding_model_max_output_dimensions
                    := "1024";
            };
        """)

        await self.con.execute("""
            ALTER TYPE Foo {
                CREATE DEFERRED INDEX ext::ai::index(
                    embedding_model := 'ollama:with-builtin-provider'
                ) ON (.content);
            };
        """)

        with self.assertRaisesRegex(
            edgedb.SchemaError,
            r"cannot drop object type 'default::FromReference' "
            r"because other objects in the schema depend on it"
        ):
            await self.con.execute("""
                DROP TYPE FromReference;
            """)

    async def test_ext_ai_ddl_uri_error_07(self):
        # Drop model type when referred to by URI index
        # Model not in reference
        await self.con.execute("""
            CREATE TYPE Foo {
                CREATE PROPERTY content: str;
            };
            CREATE EXTENSION pgvector;
            CREATE EXTENSION ai;
            CREATE ABSTRACT TYPE NotInReference
                EXTENDING ext::ai::EmbeddingModel
            {
                ALTER ANNOTATION ext::ai::model_name
                    := "not-in-reference";
                ALTER ANNOTATION ext::ai::model_provider
                    := "custom-provider";
                ALTER ANNOTATION ext::ai::embedding_model_max_input_tokens
                    := "123";
                ALTER ANNOTATION ext::ai::embedding_model_max_batch_tokens
                    := "456";
                ALTER ANNOTATION ext::ai::embedding_model_max_output_dimensions
                    := "78";
            };
        """)

        await self.con.execute("""
            ALTER TYPE Foo {
                CREATE DEFERRED INDEX ext::ai::index(
                    embedding_model := 'ollama:not-in-reference'
                ) ON (.content);
            };
        """)

        with self.assertRaisesRegex(
            edgedb.SchemaError,
            r"cannot drop object type 'default::NotInReference' "
            r"because other objects in the schema depend on it"
        ):
            await self.con.execute("""
                DROP TYPE NotInReference;
            """)

    async def test_ext_ai_ddl_uri_reference_json_01(self):
        # Custom model defined by user then added to reference json
        # New type should not be created
        with tempfile.TemporaryDirectory() as temp_dir:
            old_ref_file = (
                pathlib.Path(__file__).parent
                / 'ai_reference_files' / 'testing.json'
            )
            new_ref_file = (
                pathlib.Path(__file__).parent
                / 'ai_reference_files' / 'testing-extra.json'
            )

            async with tb_server.start_edgedb_server(
                data_dir=temp_dir,
                default_auth_method=args.ServerAuthMethod.Trust,
                extra_args=[f'--ai-reference-file={old_ref_file}'],
            ) as sd:
                con = await sd.connect()
                try:
                    await con.execute('''
                        CREATE TYPE Foo {
                            CREATE PROPERTY content: str;
                        };
                        CREATE TYPE Bar {
                            CREATE PROPERTY content: str;
                        };
                        CREATE EXTENSION pgvector;
                        CREATE EXTENSION ai;
                        CREATE ABSTRACT TYPE FromReference
                            EXTENDING ext::ai::EmbeddingModel
                        {
                            ALTER ANNOTATION ext::ai::model_name
                                := "extra-model-1";
                            ALTER ANNOTATION ext::ai::model_provider
                                := "builtin::ollama";
                            ALTER ANNOTATION
                                ext::ai::embedding_model_max_input_tokens
                                := "111";
                            ALTER ANNOTATION
                                ext::ai::embedding_model_max_batch_tokens
                                := "511";
                            ALTER ANNOTATION
                                ext::ai::embedding_model_max_output_dimensions
                                := "21";
                        };
                    ''')

                    await con.execute("""
                        ALTER TYPE Foo {
                            CREATE DEFERRED INDEX ext::ai::index(
                                embedding_model := 'ollama:extra-model-1'
                            ) ON (.content);
                        };
                    """)
                    await self._assert_generated_models([], con=con)

                finally:
                    await con.aclose()

            async with tb_server.start_edgedb_server(
                data_dir=temp_dir,
                default_auth_method=args.ServerAuthMethod.Trust,
                extra_args=[f'--ai-reference-file={new_ref_file}'],
            ) as sd:
                con = await sd.connect()
                try:
                    await con.execute("""
                        ALTER TYPE Bar {
                            CREATE DEFERRED INDEX ext::ai::index(
                                embedding_model := 'ollama:extra-model-1'
                            ) ON (.content);
                        };
                    """)
                    await self._assert_generated_models([], con=con)

                    await con.execute("""
                        ALTER TYPE Foo {
                            DROP INDEX ext::ai::index(
                                embedding_model := 'ollama:extra-model-1'
                            ) ON (.content);
                        };
                    """)
                    await self._assert_generated_models([], con=con)

                    await con.execute("""
                        ALTER TYPE Bar {
                            DROP INDEX ext::ai::index(
                                embedding_model := 'ollama:extra-model-1'
                            ) ON (.content);
                        };
                    """)
                    await self._assert_generated_models([], con=con)

                finally:
                    await con.aclose()

    async def test_ext_ai_ddl_uri_reference_json_02(self):
        # New model added to reference json
        # New type should be created, but this only succeeds after the json is
        # updated.
        with tempfile.TemporaryDirectory() as temp_dir:
            old_ref_file = (
                pathlib.Path(__file__).parent
                / 'ai_reference_files' / 'testing.json'
            )
            new_ref_file = (
                pathlib.Path(__file__).parent
                / 'ai_reference_files' / 'testing-extra.json'
            )

            async with tb_server.start_edgedb_server(
                data_dir=temp_dir,
                default_auth_method=args.ServerAuthMethod.Trust,
                extra_args=[f'--ai-reference-file={old_ref_file}'],
            ) as sd:
                con = await sd.connect()
                try:
                    await con.execute('''
                        CREATE TYPE Foo {
                            CREATE PROPERTY content: str;
                        };
                        CREATE EXTENSION pgvector;
                        CREATE EXTENSION ai;
                    ''')

                    with self.assertRaisesRegex(
                        edgedb.SchemaDefinitionError,
                        r"undefined embedding model: no subtype of "
                        r"ext::ai::EmbeddingModel is annotated as "
                        r"'extra-model-1'"
                    ):
                        await con.execute("""
                            ALTER TYPE Foo {
                                CREATE DEFERRED INDEX ext::ai::index(
                                    embedding_model := 'ollama:extra-model-1'
                                ) ON (.content);
                            };
                        """)
                    await self._assert_generated_models([], con=con)

                finally:
                    await con.aclose()

            async with tb_server.start_edgedb_server(
                data_dir=temp_dir,
                default_auth_method=args.ServerAuthMethod.Trust,
                extra_args=[f'--ai-reference-file={new_ref_file}'],
            ) as sd:
                con = await sd.connect()
                try:
                    await con.execute("""
                        ALTER TYPE Foo {
                            CREATE DEFERRED INDEX ext::ai::index(
                                embedding_model := 'ollama:extra-model-1'
                            ) ON (.content);
                        };
                    """)
                    await self._assert_generated_models(
                        [
                            s_indexes.EmbeddingModelDesc(
                                model_name='extra-model-1',
                                model_provider='builtin::ollama',
                                max_input_tokens=111,
                                max_batch_tokens=511,
                                max_output_dimensions=21,
                                supports_shortening=False,
                            ),
                        ],
                        con=con,
                    )

                    await con.execute("""
                        ALTER TYPE Foo {
                            DROP INDEX ext::ai::index(
                                embedding_model := 'ollama:extra-model-1'
                            ) ON (.content);
                        };
                    """)
                    await self._assert_generated_models([], con=con)

                finally:
                    await con.aclose()
