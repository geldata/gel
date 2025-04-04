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

from typing import Any, Optional

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

    source, result, productions = _parse_inner(doc.source, sdl)

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
        return Result(err=[
            lsp_types.Diagnostic(
                range=ls_utils.span_to_lsp(source.text(), e.get_span()),
                severity=lsp_types.DiagnosticSeverity.Error,
                message=e.args[0],
            )
        ])
    if sdl:
        assert isinstance(ast, qlast.Schema), ast
    else:
        assert isinstance(ast, list), ast
    return Result(ok=ast)


def parse_and_suggest(
    doc: TextDocument, position: lsp_types.Position
) -> Optional[lsp_types.CompletionItem]:
    sdl = doc.filename.endswith('.esdl') if doc.filename else False

    source, result, _productions = _parse_inner(doc.source, sdl)
    for error in result.errors:
        message: str
        message, span, _hint, _details = error
        if not message.startswith('Missing keyword '):
            continue
        (start, end) = tokenizer.inflate_span(source.text(), span)

        if not _position_in_span(position, (start, end)):
            continue

        keyword = message.removeprefix('Missing keyword \'')[:-1]

        return lsp_types.CompletionItem(
            label=keyword,
            kind=lsp_types.CompletionItemKind.Keyword,
        )
    return None


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


def _parse_inner(
    source_str: str, sdl: bool
) -> tuple[tokenizer.Source, rust_parser.ParserResult, Any]:
    try:
        source = tokenizer.Source.from_string(source_str)
    except Exception as e:
        # TODO
        print(e)
        raise AssertionError(e)

    start_t = qltokens.T_STARTSDLDOCUMENT if sdl else qltokens.T_STARTBLOCK
    start_t_name = start_t.__name__[2:]
    tokens = source.tokens()

    result, productions = rust_parser.parse(start_t_name, tokens)
    return source, result, productions
