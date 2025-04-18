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
from edb.common import traceback as edb_traceback
from edb.edgeql import parser as qlparser
from edb.edgeql import tokenizer as qltokenizer

from . import parsing as ls_parsing
from . import server as ls_server
from . import is_schema_file, is_edgeql_file


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
        ls.show_message_log('Starting')
        qlparser.preload_spec()
        ls.show_message_log('Started')

    @ls.feature(lsp_types.TEXT_DOCUMENT_DID_OPEN)
    def text_document_did_open(params: lsp_types.DidOpenTextDocumentParams):
        document_updated(ls, params.text_document.uri)

    @ls.feature(lsp_types.TEXT_DOCUMENT_DID_CHANGE)
    def text_document_did_change(params: lsp_types.DidChangeTextDocumentParams):
        document_updated(ls, params.text_document.uri)

    @ls.feature(lsp_types.TEXT_DOCUMENT_DEFINITION)
    def text_document_definition(params: lsp_types.DefinitionParams):
        return document_definition(ls, params)

    @ls.feature(
        lsp_types.TEXT_DOCUMENT_COMPLETION,
        lsp_types.CompletionOptions(trigger_characters=[',']),
    )
    def completions(params: lsp_types.CompletionParams):
        document = ls.workspace.get_text_document(params.text_document.uri)

        items = ls_parsing.parse_and_suggest(document, params.position, ls)
        return lsp_types.CompletionList(is_incomplete=False, items=items)

    return ls


def document_updated(ls: ls_server.GelLanguageServer, doc_uri: str):
    # each call to this function should yield in exactly one publish_diagnostics
    # for this document

    document = ls.workspace.get_text_document(doc_uri)
    diagnostic_set: ls_server.DiagnosticsSet

    try:
        if is_schema_file(doc_uri):
            # schema file

            diagnostics = ls_server.update_schema_doc(ls, document)

            # recompile schema
            ls.state.schema = None
            _schema, diagnostic_set, err_msg = ls_server.get_schema(ls)
            diagnostic_set.extend(document, diagnostics)

            if err_msg:
                ls.show_message(f'Error: {err_msg}')

        elif is_edgeql_file(doc_uri):
            # query file
            ql_ast_res = ls_parsing.parse(document, ls)
            if diag := ql_ast_res.err:
                ls.publish_diagnostics(document.uri, diag, document.version)
                return
            assert ql_ast_res.ok
            ql_ast = ql_ast_res.ok

            if isinstance(ql_ast, list):
                diagnostic_set, _ = ls_server.compile(ls, document, ql_ast)
            else:
                # SDL in query files?
                diagnostic_set = ls_server.DiagnosticsSet()
        else:
            ls.show_message_log(f'Unknown file type: {doc_uri}')
            diagnostic_set = ls_server.DiagnosticsSet()
            # doc_uri in ('gel.toml')

        diagnostic_set.extend(document, [])  # make sure we publish for document
        for doc, diags in diagnostic_set.by_doc.items():
            ls.publish_diagnostics(doc.uri, diags, doc.version)
    except BaseException as e:
        send_internal_error(ls, e)
        ls.publish_diagnostics(document.uri, [], document.version)


def document_definition(
    ls: ls_server.GelLanguageServer, params: lsp_types.DefinitionParams
) -> lsp_types.Location | None:
    doc_uri = params.text_document.uri
    document = ls.workspace.get_text_document(doc_uri)

    position: int = qltokenizer.line_col_to_source_point(
        document.source, params.position.line, params.position.character
    ).offset
    ls.show_message_log(f'position = {position}')

    try:
        if is_schema_file(doc_uri):
            ls.show_message_log(
                'Definition in schema files are not supported yet'
            )

        elif is_edgeql_file(doc_uri):

            ql_ast_res = ls_parsing.parse(document, ls)
            if not ql_ast_res.ok:
                return None
            ql_ast = ql_ast_res.ok

            if isinstance(ql_ast, list):
                return ls_server.get_definition_in_ql(
                    ls, document, ql_ast, position
                )
            else:
                # SDL in query files?
                pass
        else:
            ls.show_message_log(f'Unknown file type: {doc_uri}')

    except BaseException as e:
        send_internal_error(ls, e)

    return None


def send_internal_error(ls: ls_server.GelLanguageServer, e: BaseException):
    text = edb_traceback.format_exception(e)
    ls.show_message_log(f'Internal error: {text}')
