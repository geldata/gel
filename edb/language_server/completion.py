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

from typing import Any

from lsprotocol import types as lsp_types
import pygls

from edb.common import ast
from edb.common import span as edb_span
from edb.edgeql import ast as qlast
from edb.edgeql import tokenizer as qltokenizer
from edb.edgeql import compiler as qlcompiler

from . import parsing as ls_parsing
from . import server as ls_server


def get_completion(
    ls: ls_server.GelLanguageServer, params: lsp_types.CompletionParams
) -> lsp_types.CompletionList:
    document = ls.workspace.get_text_document(params.text_document.uri)

    target = qltokenizer.line_col_to_source_point(
        document.source, params.position.line, params.position.character
    )

    # get syntactic suggestions
    items, can_be_ident = ls_parsing.get_completion(document, target.offset, ls)

    if can_be_ident:
        ql_ast = ls_parsing.parse_and_recover(document)
        if isinstance(ql_ast, list):
            items = (
                _get_completion_in_ql(ls, document, ql_ast, target.offset)
            ) + items

    return lsp_types.CompletionList(is_incomplete=False, items=items)


def _get_completion_in_ql(
    ls: ls_server.GelLanguageServer,
    document: pygls.workspace.TextDocument,
    ql_stmts: list[qlast.Base],
    target: int,
) -> list[lsp_types.CompletionItem]:
    # replace the expr under the cursor with qlast.Cursor
    if not ql_stmts:
        return []
    for ql_stmt in ql_stmts:
        replaced = replace_by_source_position(ql_stmt, qlast.Cursor(), target)
        if replaced:
            break
    if not replaced:
        ls.show_message_log(f'Cannot inject qlast.Cursor')
        return []

    # compile the stmt that now contains the qlast.Cursor,
    # which should halt compilation, when it gets to the cursor
    try:
        diagnostics, _ir_stmts = ls_server.compile_ql(ls, document, [ql_stmt])
    except qlcompiler.expr.IdentCompletionException as e:
        return [
            lsp_types.CompletionItem(
                label=s, kind=lsp_types.CompletionItemKind.Variable
            )
            for s in e.suggestions
        ]

    for diags in diagnostics.by_doc.values():
        for d in diags:
            ls.show_message_log(f'Cannot provide completion: {d.message}')
            return []

    raise AssertionError('qlast.Cursor did not raise IdentCompletionException')


# Replaces an expr node in AST that has a certain position within the source.
# It matches the first Expr whose span contains the target offset in a
# post-order traversal of the AST.
def replace_by_source_position(
    tree: qlast.Base, replacement: qlast.Expr, target_offset: int
) -> bool:
    replacer = SpanReplacer(target_offset, replacement)
    replacer.visit(tree)
    return replacer.found


class SpanReplacer(ast.NodeTransformer):
    target_offset: int
    replacement: qlast.Expr
    found: bool

    def __init__(self, target_offset: int, replacement: qlast.Expr):
        super().__init__()
        self.target_offset = target_offset
        self.replacement = replacement
        self.found = False

    def generic_visit(self, node, *, combine_results=None) -> Any:
        if self.found:
            return node

        has_span = False
        if node_span := getattr(node, 'span', None):
            has_span = True
            if not edb_span.span_contains(node_span, self.target_offset):
                return node

        r = super().generic_visit(node)

        if not self.found and has_span and isinstance(node, qlast.Expr):
            self.found = True
            return self.replacement

        return r
