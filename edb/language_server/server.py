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

from typing import Mapping, Iterable, Optional
import dataclasses
import pathlib
import os

from pygls.server import LanguageServer
from pygls import uris as pygls_uris
import pygls
from lsprotocol import types as lsp_types


from edb import errors
from edb.common import span as edb_span

from edb.edgeql import ast as qlast
from edb.edgeql import compiler as qlcompiler

from edb.ir import ast as irast

from edb.schema import schema as s_schema
from edb.schema import objects as s_objects
from edb.schema import std as s_std
from edb.schema import ddl as s_ddl
import pygls.workspace

from . import parsing as ls_parsing
from . import is_schema_file
from . import project
from . import utils as ls_utils


@dataclasses.dataclass(kw_only=True)
class State:
    manifest: tuple[project.Manifest, pathlib.Path] | None = None

    schema_docs: list[pygls.workspace.TextDocument] = dataclasses.field(
        default_factory=lambda: []
    )

    schema: s_schema.Schema | None = None

    std_schema: s_schema.Schema | None = None


@dataclasses.dataclass(kw_only=True)
class Config:
    project_dir: str


class GelLanguageServer(LanguageServer):
    state: State
    config: Config

    def __init__(self, config: Config):
        super().__init__("Gel Language Server", "v0.1")
        self.state = State()
        self.config = config


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


def _new_diagnostic_at_the_top(message: str) -> lsp_types.Diagnostic:
    return lsp_types.Diagnostic(
        range=lsp_types.Range(
            start=lsp_types.Position(line=0, character=0),
            end=lsp_types.Position(line=1, character=0),
        ),
        severity=lsp_types.DiagnosticSeverity.Error,
        message=message,
        related_information=[],
    )


def compile(
    ls: GelLanguageServer,
    doc: pygls.workspace.TextDocument,
    stmts: list[qlast.Base],
) -> tuple[DiagnosticsSet, list[irast.Statement]]:
    if not stmts:
        return (DiagnosticsSet(by_doc={doc: []}), [])

    schema, diagnostics_set, err_msg = get_schema(ls)
    if not schema:
        if len(ls.state.schema_docs) == 0:
            diagnostics_set.append(
                doc,
                _new_diagnostic_at_the_top(
                    err_msg or "Cannot find schema files"
                ),
            )
        return (diagnostics_set, [])

    diagnostics: list[lsp_types.Diagnostic] = []
    ir_stmts: list[irast.Statement] = []
    modaliases: Mapping[str | None, str] = {None: "default"}
    for ql_stmt in stmts:
        try:
            if isinstance(ql_stmt, qlast.DDLCommand):
                schema, _delta = s_ddl.delta_and_schema_from_ddl(
                    ql_stmt, schema=schema, modaliases=modaliases
                )

            elif isinstance(ql_stmt, (qlast.Command, qlast.Expr)):
                options = qlcompiler.CompilerOptions(modaliases=modaliases)
                ir_res = qlcompiler.compile_ast_to_ir(
                    ql_stmt, schema, options=options
                )
                if isinstance(ir_res, irast.Statement):
                    ir_stmts.append(ir_res)
            else:
                ls.show_message_log(f"skip compile of {ql_stmt}")
        except errors.EdgeDBError as error:
            diagnostics.append(_convert_error(error))

    diagnostics_set.extend(doc, diagnostics)
    return (diagnostics_set, ir_stmts)


def _convert_error(error: errors.EdgeDBError) -> lsp_types.Diagnostic:
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


def get_schema(
    ls: GelLanguageServer,
) -> tuple[s_schema.Schema | None, DiagnosticsSet, str | None]:
    if ls.state.schema:
        return (ls.state.schema, DiagnosticsSet(), None)

    err_msg: str | None = None
    if len(ls.state.schema_docs) == 0:
        schema_dir, err_msg = _determine_schema_dir(ls)
        if not schema_dir:
            return (None, DiagnosticsSet(), err_msg)
        err_msg = _load_schema_docs(ls, schema_dir)

    if len(ls.state.schema_docs) == 0:
        return (None, DiagnosticsSet(), err_msg)

    schema, diagnostics = _compile_schema(ls)
    return schema, diagnostics, None


def update_schema_doc(
    ls: GelLanguageServer, doc: pygls.workspace.TextDocument
) -> list[lsp_types.Diagnostic]:
    schema_dir, err_msg = _determine_schema_dir(ls)
    if not schema_dir:
        return [_new_diagnostic_at_the_top(err_msg or "cannot find schema-dir")]

    # dont update if doc is not in schema_dir
    if schema_dir not in pathlib.Path(doc.path).parents:
        return [
            _new_diagnostic_at_the_top(
                f"this schema file is not in schema-dir ({schema_dir})"
            )
        ]

    if len(ls.state.schema_docs) == 0:
        _load_schema_docs(ls, schema_dir)

    existing = next(
        (i for i, d in enumerate(ls.state.schema_docs) if d.path == doc.path),
        None,
    )
    if existing is not None:
        # update
        ls.state.schema_docs[existing] = doc
    else:
        # insert
        ls.show_message_log("new schema file added: " + doc.path)
        ls.show_message_log("existing files: ")
        for d in ls.state.schema_docs:
            ls.show_message_log("- " + d.path)

        ls.state.schema_docs.append(doc)

    return []


def _get_workspace_path(
    ls: GelLanguageServer,
) -> tuple[pathlib.Path | None, str | None]:
    if len(ls.workspace.folders) > 1:
        return None, "Workspaces with multiple root folders are not supported"
    if len(ls.workspace.folders) == 0:
        return None, "No workspace open, cannot load schema"

    workspace: lsp_types.WorkspaceFolder = next(
        iter(ls.workspace.folders.values())
    )
    return pathlib.Path(pygls_uris.to_fs_path(workspace.uri)), None


# Looks as the file system and loads schema documents into ls.state
# Returns error message.
def _load_schema_docs(
    ls: GelLanguageServer, schema_dir: pathlib.Path
) -> Optional[str]:
    # discard all existing docs
    ls.state.schema_docs.clear()

    try:
        entries = os.listdir(schema_dir)
    except FileNotFoundError:
        return f"Cannot list directory: {schema_dir}"

    # read .esdl files
    for entry in entries:
        if not is_schema_file(entry):
            continue
        doc = ls.workspace.get_text_document(f"file://{schema_dir / entry}")
        ls.state.schema_docs.append(doc)

    return None


def _determine_schema_dir(
    ls: GelLanguageServer,
) -> tuple[pathlib.Path | None, str | None]:
    workspace_path, err_msg = _get_workspace_path(ls)
    if not workspace_path:
        return None, err_msg or "Cannot determine schema dir"

    project_dir = workspace_path / pathlib.Path(ls.config.project_dir)

    manifest, err_msg = _load_manifest(ls, project_dir)
    if not manifest:
        # no manifest: don't infer any schema dir
        return None, err_msg

    if manifest.project:
        schema_dir = project_dir / manifest.project.schema_dir
    else:
        schema_dir = project_dir / "dbschema"

    if schema_dir.is_dir():
        return schema_dir, None
    return None, f"Missing schema dir at {schema_dir}"


def _load_manifest(
    ls: GelLanguageServer,
    project_dir: pathlib.Path,
) -> tuple[project.Manifest | None, str | None]:
    if ls.state.manifest:
        return ls.state.manifest[0], None

    try:
        ls.state.manifest = project.read_manifest(project_dir)
        return ls.state.manifest[0], None
    except BaseException as e:
        return None, str(e)


def _compile_schema(
    ls: GelLanguageServer,
) -> tuple[s_schema.Schema | None, DiagnosticsSet]:
    # parse
    sdl = qlast.Schema(declarations=[])
    diagnostics = DiagnosticsSet()
    for doc in ls.state.schema_docs:
        res = ls_parsing.parse(doc, ls)
        if d := res.err:
            diagnostics.by_doc[doc] = d
        else:
            diagnostics.by_doc[doc] = []
            if isinstance(res.ok, qlast.Schema):
                sdl.declarations.extend(res.ok.declarations)
            else:
                # TODO: complain that .esdl contains non-SDL syntax
                pass

    std_schema = _load_std_schema(ls.state)

    # apply SDL to std schema
    ls.show_message_log("compiling schema ..")
    try:
        schema, _warnings = s_ddl.apply_sdl(sdl, base_schema=std_schema)
        ls.show_message_log(".. done")
    except errors.EdgeDBError as error:
        schema = None

        # find doc
        do = next(
            (d for d in ls.state.schema_docs if error.filename == d.filename),
            None,
        )
        if do is None:
            ls.show_message_log(
                f"cannot find original doc of the error ({error.filename}), "
                "using first schema file"
            )
            do = ls.state.schema_docs[0]

        # convert error
        diagnostics.by_doc[do].append(_convert_error(error))

    ls.state.schema = schema
    return (schema, diagnostics)


def _load_std_schema(state: State) -> s_schema.Schema:
    if state.std_schema is not None:
        return state.std_schema

    schema: s_schema.Schema = s_schema.EMPTY_SCHEMA
    for modname in [*s_schema.STD_SOURCES, *s_schema.TESTMODE_SOURCES]:
        schema = s_std.load_std_module(schema, modname)
    schema, _ = s_std.make_schema_version(schema)
    schema, _ = s_std.make_global_schema_version(schema)

    state.std_schema = schema
    return state.std_schema


def get_definition_in_ql(
    ls: GelLanguageServer,
    document: pygls.workspace.TextDocument,
    ql_ast: list[qlast.Base],
    position: int,
) -> lsp_types.Location | None:
    # compile the whole doc
    # TODO: search ql ast before compiling all stmts
    _, ir_stmts = compile(ls, document, ql_ast)

    # find the ir node at the position
    node = None
    for ir_stmt in ir_stmts:
        node = edb_span.find_by_source_position(ir_stmt, position)
        if node:
            break

    if not node:
        ls.show_message_log(f"cannot find span in {len(ir_stmts)} stmts")
        return None

    assert isinstance(node, irast.Base), node
    ls.show_message_log(f"node: {str(node)}")
    ls.show_message_log(f"span: {str(node.span)}")

    schema = ir_stmt.schema
    assert schema

    # lookup schema objects depending on which ir node we are over
    target: Optional[s_objects.Object] = None
    if isinstance(node, irast.Set):
        node = node.expr
    if isinstance(node, irast.TypeRoot):
        target = schema.get_by_id(node.typeref.id)
    elif isinstance(node, irast.Pointer):
        if isinstance(node.ptrref, irast.PointerRef):
            target = schema.get_by_id(node.ptrref.id)
    if not target:
        ls.show_message_log(f"don't know how to lookup schema by {node}")
        return None

    span: edb_span.Span | None = target.get_span(schema)
    if not span:
        name = target.get_name(schema)
        ls.show_message_log(f"schema object found, but no span: {name}")
        return None

    # find originating document
    doc: Optional[pygls.workspace.TextDocument] = None

    # is doc the current document?
    if span.filename == document.filename:
        doc = document

    # find schema docs with this filename
    if not doc:
        docs = ls.state.schema_docs
        doc = next((d for d in docs if d.filename == span.filename), None)

    if not doc:
        ls.show_message_log(f"Cannot find doc: {span.filename}")
        return None

    return lsp_types.Location(
        uri=doc.uri,
        range=ls_utils.span_to_lsp(doc.source, (span.start, span.end)),
    )
