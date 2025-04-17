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

from pygls.server import LanguageServer
from pygls.workspace import TextDocument
from lsprotocol import types as lsp_types

from edb import errors
from edb.edgeql import ast as qlast
from edb.edgeql import tokenizer
from edb.edgeql import parser as qlparser
from edb.edgeql.parser.grammar import tokens as qltokens
import edb._edgeql_parser as rust_parser

from . import Result, is_schema_file
from . import utils as ls_utils


def parse(
    doc: TextDocument, ls: LanguageServer
) -> Result[list[qlast.Base] | qlast.Schema, list[lsp_types.Diagnostic]]:
    sdl = is_schema_file(doc.filename) if doc.filename else False

    start_t = qltokens.T_STARTSDLDOCUMENT if sdl else qltokens.T_STARTBLOCK
    start_t_name = start_t.__name__[2:]

    source_res = _tokenize(doc.source)
    if diagnostics := source_res.err:
        return Result(err=diagnostics)
    source = source_res.ok
    assert source

    result, productions = rust_parser.parse(start_t_name, source.tokens())

    if result.errors:
        diagnostics = []
        for error in result.errors:
            message, span, hint, details = error

            if details:
                message += f"\n{details}"
            if hint:
                message += f"\nHint: {hint}"

            diagnostics.append(
                lsp_types.Diagnostic(
                    range=ls_utils.span_to_lsp(source.text(), span),
                    severity=lsp_types.DiagnosticSeverity.Error,
                    message=message,
                )
            )

        return Result(err=diagnostics)

    # parsing successful
    assert isinstance(result.out, rust_parser.CSTNode)

    try:
        ast = qlparser._cst_to_ast(
            result.out, productions, source, doc.filename
        ).val
    except errors.EdgeDBError as e:
        return Result(
            err=[
                lsp_types.Diagnostic(
                    range=ls_utils.span_to_lsp(source.text(), e.get_span()),
                    severity=lsp_types.DiagnosticSeverity.Error,
                    message=e.args[0],
                )
            ]
        )
    if sdl:
        assert isinstance(ast, qlast.Schema), ast
    else:
        assert isinstance(ast, list), ast
    return Result(ok=ast)


def parse_and_suggest(
    doc: TextDocument, position: lsp_types.Position, ls: LanguageServer
) -> list[lsp_types.CompletionItem]:
    sdl = is_schema_file(doc.path)

    start_t = qltokens.T_STARTSDLDOCUMENT if sdl else qltokens.T_STARTBLOCK
    start_t_name = start_t.__name__[2:]

    # tokenize
    source_res = _tokenize(doc.source)
    if not source_res.ok:
        return []
    source: tokenizer.Source = source_res.ok

    # limit tokens to things preceding cursor position
    target = tokenizer.line_col_to_source_point(
        doc.source, position.line, position.character
    )
    cut_index = len(source.tokens())
    for index, tok in enumerate(source.tokens()):
        if not tok.span_end() <= target.offset:
            cut_index = index
            break
    tokens = source.tokens()[0:cut_index]

    # run parser and suggest next possible keywords
    suggestions = rust_parser.suggest_next_keywords(start_t_name, tokens)

    # convert to CompletionItem
    return [
        lsp_types.CompletionItem(
            label=keyword,
            kind=lsp_types.CompletionItemKind.Keyword,
        )
        for keyword in suggestions
    ]


def _tokenize(
    source: str,
) -> Result[tokenizer.Source, list[lsp_types.Diagnostic]]:
    try:
        return Result(ok=tokenizer.Source.from_string(source))
    except errors.EdgeQLSyntaxError as e:
        return Result(
            err=[
                lsp_types.Diagnostic(
                    range=ls_utils.span_to_lsp(source, e.get_span()),
                    severity=lsp_types.DiagnosticSeverity.Error,
                    message=e.args[0],
                )
            ]
        )


def _position_in_span(pos: lsp_types.Position, span: tuple[Any, Any]):
    start, end = span

    if pos.line < start.line - 1:
        return False
    if pos.line > end.line - 1:
        return False
    if pos.line == start.line - 1 and pos.character < start.column - 1:
        return False
    if pos.line == end.line - 1 and pos.character > end.column - 1:
        return False
    return True
