#
# This source file is part of the EdgeDB open source project.
#
# Copyright 2016-present MagicStack Inc. and the EdgeDB authors.
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

import pathlib
import sys

import click

from edb.tools.edb import edbcommands

from edb.testbase import http as tb


@edbcommands.command('fake-ai-server')
@click.option(
    '--port', type=int, default=0)
def fake_ai_server(*, port):
    """Run a fake AI embedding server"""

    # Hmmmmmm.
    tests_dir = pathlib.Path(__file__).parent.parent.parent / 'tests'
    sys.path.append(str(tests_dir))
    import test_ext_ai  # type: ignore

    mock_server = tb.MockHttpServer(port=port)
    mock_server.start()

    base_url = mock_server.get_base_url().rstrip("/")

    mock_server.register_route_handler(
        "POST",
        base_url,
        "/v1/embeddings",
    )(test_ext_ai.TestExtAI.mock_api_embeddings)

    print("Running on", base_url)
    print("Consider this config:\n")
    print(test_ext_ai.TestExtAI.get_ai_config(base_url))
