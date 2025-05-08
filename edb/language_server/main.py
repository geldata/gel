#
# This source file is part of the EdgeDB open source project.
#
# Copyright 2008-present MagicStack Inc. and the EdgeDB authors.
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

import sys
import json


from lsprotocol import types as lsp_types
import click

from edb import buildmeta
from edb.edgeql import parser as qlparser

from . import server as ls_server
from . import definition as ls_definition
from . import completion as ls_completion


@click.command()
@click.option('--version', is_flag=True, help="Show the version and exit.")
@click.option(
    '--stdio',
    is_flag=True,
    help="Use stdio for LSP. This is currently the only transport.",
)
@click.argument("options", type=str, default='{}')
def main(options: str | None, *, version: bool, stdio: bool):
    if version:
        print(f"gel-ls, version {buildmeta.get_version()}")
        sys.exit(0)

    ls = init(options)

    if stdio:
        ls.start_io()
    else:
        print("Error: no LSP transport enabled. Use --stdio.")


def init(options_json: str | None) -> ls_server.GelLanguageServer:
    # load config
    options_dict = json.loads(options_json or '{}')
    project_dir = '.'
    if 'project_dir' in options_dict:
        project_dir = options_dict['project_dir']
    config = ls_server.Config(project_dir=project_dir)

    # construct server
    ls = ls_server.GelLanguageServer(config)

    # register hooks
    @ls.feature(
        lsp_types.INITIALIZE,
    )
    def init(_params: lsp_types.InitializeParams):
        qlparser.preload_spec()
        ls.show_message_log('gel-ls ready for requests')

    @ls.feature(lsp_types.TEXT_DOCUMENT_DID_OPEN)
    def text_document_did_open(params: lsp_types.DidOpenTextDocumentParams):
        ls_server.document_updated(ls, params.text_document.uri)

    @ls.feature(lsp_types.TEXT_DOCUMENT_DID_SAVE)
    def text_document_did_save(params: lsp_types.DidChangeTextDocumentParams):
        ls_server.document_updated(ls, params.text_document.uri)

    @ls.feature(lsp_types.TEXT_DOCUMENT_DEFINITION)
    def text_document_definition(
        params: lsp_types.DefinitionParams,
    ) -> lsp_types.Definition:
        return ls_definition.get_definition(ls, params)

    @ls.feature(
        lsp_types.TEXT_DOCUMENT_COMPLETION,
        lsp_types.CompletionOptions(trigger_characters=[',']),
    )
    def completion(params: lsp_types.CompletionParams):
        return ls_completion.get_completion(ls, params)

    return ls
