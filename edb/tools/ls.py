#
# This source file is part of the EdgeDB open source project.
#
# Copyright 2020-present MagicStack Inc. and the EdgeDB authors.
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

from typing import Optional
import sys
import click

from edb import buildmeta
from edb.tools.edb import edbcommands


@edbcommands.command("ls")
@click.option('--version', is_flag=True, help="Show the version and exit.")
@click.option(
    '--stdio',
    is_flag=True,
    help="Use stdio for LSP. This is currently the only transport.",
)
@click.argument("options", type=str, default='{}')
def main(options: Optional[str], *, version: bool, stdio: bool):
    # import language_server only if we are using this command
    # otherwise this breaks when pygls is not installed
    from edb.language_server import main as ls_main

    if version:
        print(f"gel-ls, version {buildmeta.get_version()}")
        sys.exit(0)

    ls = ls_main.init(options)

    if stdio:
        ls.start_io()
    else:
        print("Error: no LSP transport enabled. Use --stdio.")
