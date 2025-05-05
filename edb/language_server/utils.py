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

import dataclasses
from typing import Iterable

from lsprotocol import types as lsp_types
import pygls

from edb import errors
from edb.edgeql import tokenizer


@dataclasses.dataclass(kw_only=True)
class DiagnosticsSet:
    by_doc: dict[pygls.workspace.TextDocument, list[lsp_types.Diagnostic]] = (
        dataclasses.field(default_factory=lambda: {})
    )

    def append(
        self,
        doc: pygls.workspace.TextDocument,
        diagnostic: lsp_types.Diagnostic,
    ):
        if doc not in self.by_doc:
            self.by_doc[doc] = []
        self.by_doc[doc].append(diagnostic)

    def extend(
        self,
        doc: pygls.workspace.TextDocument,
        diagnostics: Iterable[lsp_types.Diagnostic],
    ):
        if doc not in self.by_doc:
            self.by_doc[doc] = []
        self.by_doc[doc].extend(diagnostics)


# Convert a Span to LSP Range
def span_to_lsp(
    source: str, span: tuple[int, int | None] | None
) -> lsp_types.Range:
    if span:
        (start, end) = tokenizer.inflate_span(source, span)
    else:
        (start, end) = (None, None)
    assert end

    return lsp_types.Range(
        start=(
            lsp_types.Position(
                line=start.line - 1,
                character=start.column - 1,
            )
            if start
            else lsp_types.Position(line=0, character=0)
        ),
        end=(
            lsp_types.Position(
                line=end.line - 1,
                character=end.column - 1,
            )
            if end
            else lsp_types.Position(line=0, character=0)
        ),
    )


# Convert EdgeDBError into an LSP Diagnostic
def error_to_lsp(error: errors.EdgeDBError) -> lsp_types.Diagnostic:
    return lsp_types.Diagnostic(
        range=(
            lsp_types.Range(
                start=lsp_types.Position(
                    line=error.line - 1,
                    character=error.col - 1,
                ),
                end=lsp_types.Position(
                    line=error.line_end - 1,
                    character=error.col_end - 1,
                ),
            )
            if error.line >= 0
            else lsp_types.Range(
                start=lsp_types.Position(line=0, character=0),
                end=lsp_types.Position(line=0, character=0),
            )
        ),
        severity=lsp_types.DiagnosticSeverity.Error,
        message=error.args[0],
    )


# Constructs a new diagnostic in the first line of the document
def new_diagnostic_at_the_top(message: str) -> lsp_types.Diagnostic:
    return lsp_types.Diagnostic(
        range=lsp_types.Range(
            start=lsp_types.Position(line=0, character=0),
            end=lsp_types.Position(line=1, character=0),
        ),
        severity=lsp_types.DiagnosticSeverity.Error,
        message=message,
        related_information=[],
    )
