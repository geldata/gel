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

from typing import Optional, cast, Iterable
import pathlib
import os

from pygls import uris as pygls_uris
import pygls
from lsprotocol import types as lsp_types


from edb import errors

from edb.edgeql import ast as qlast

from edb.schema import schema as s_schema
from edb.schema import std as s_std
from edb.schema import ddl as s_ddl
import pygls.workspace

from . import parsing as ls_parsing
from . import is_schema_file
from . import project
from . import utils as ls_utils
from . import server as ls_server
from edb.language_server import Result


def get_schema(
    ls: ls_server.GelLanguageServer,
) -> tuple[s_schema.Schema | None, ls_utils.DiagnosticsSet, str | None]:
    if ls.state.schema:
        return (ls.state.schema, ls_utils.DiagnosticsSet(), None)

    err_msg: str | None = None
    if len(ls.state.schema_docs) == 0:
        schema_dir, err_msg = _determine_schema_dir(ls)
        if not schema_dir:
            return (None, ls_utils.DiagnosticsSet(), err_msg)
        err_msg = _load_schema_docs(ls, schema_dir)

    if len(ls.state.schema_docs) == 0:
        return (None, ls_utils.DiagnosticsSet(), err_msg)

    schema, diagnostics = _compile_schema(ls)
    return schema, diagnostics, None


def store_schema_doc(
    ls: ls_server.GelLanguageServer, doc: pygls.workspace.TextDocument
) -> list[lsp_types.Diagnostic]:
    res = _ensure_schema_docs_loaded(ls)
    if e := res.err:
        return [ls_utils.new_diagnostic_at_the_top(e)]
    schema_dir = cast(pathlib.Path, res.ok)

    # dont update if doc is not in schema_dir
    if schema_dir not in pathlib.Path(doc.path).parents:
        return [
            ls_utils.new_diagnostic_at_the_top(
                f"this schema file is not in schema-dir ({schema_dir})"
            )
        ]

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

    # clear AST cache
    ls.state.schema_sdl = None

    return []


def _ensure_schema_docs_loaded(
    ls: ls_server.GelLanguageServer,
) -> Result[pathlib.Path, str]:
    schema_dir, err_msg = _determine_schema_dir(ls)
    if not schema_dir:
        return Result(err=err_msg or "cannot find schema-dir")

    if len(ls.state.schema_docs) == 0:
        if err_mgs := _load_schema_docs(ls, schema_dir):
            return Result(err=err_mgs)
    return Result(ok=schema_dir)


def _get_workspace_path(
    ls: ls_server.GelLanguageServer,
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
    ls: ls_server.GelLanguageServer, schema_dir: pathlib.Path
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

    # clear AST cache
    ls.state.schema_sdl = None

    return None


def _determine_schema_dir(
    ls: ls_server.GelLanguageServer,
) -> tuple[pathlib.Path | None, str | None]:
    workspace_path, err_msg = _get_workspace_path(ls)
    if not workspace_path:
        return None, err_msg or "Cannot determine schema dir"

    project_dir = workspace_path / pathlib.Path(ls.config.project_dir)

    manifest, err_msg = _load_manifest(ls, project_dir)
    if not manifest:
        # no manifest: don't infer any schema dir
        return None, err_msg

    if manifest.project and manifest.project.schema_dir:
        schema_dir = project_dir / manifest.project.schema_dir
    else:
        schema_dir = project_dir / "dbschema"

    if schema_dir.is_dir():
        return schema_dir, None
    return None, f"Missing schema dir at {schema_dir}"


def _load_manifest(
    ls: ls_server.GelLanguageServer,
    project_dir: pathlib.Path,
) -> tuple[project.Manifest | None, str | None]:
    if ls.state.manifest:
        return ls.state.manifest[0], None

    try:
        ls.state.manifest = project.read_manifest(project_dir)
        return ls.state.manifest[0], None
    except BaseException as e:
        return None, str(e)


def _parse_schema(
    ls: ls_server.GelLanguageServer,
) -> ls_utils.DiagnosticsSet:
    diagnostics = ls_utils.DiagnosticsSet()

    if ls.state.schema_sdl:
        return ls_utils.DiagnosticsSet()

    sdl = qlast.Schema(declarations=[])
    for doc in ls.state.schema_docs:
        res = ls_parsing.parse(doc)
        if d := res.err:
            diagnostics.by_doc[doc] = d
        else:
            diagnostics.by_doc[doc] = []
            if isinstance(res.ok, qlast.Schema):
                sdl.declarations.extend(res.ok.declarations)
            else:
                # TODO: complain that .gel contains non-SDL syntax
                pass
    ls.state.schema_sdl = sdl
    return diagnostics


def _compile_schema(
    ls: ls_server.GelLanguageServer,
) -> tuple[s_schema.Schema | None, ls_utils.DiagnosticsSet]:
    diagnostics = _parse_schema(ls)
    assert ls.state.schema_sdl

    std_schema = _load_std_schema(ls.state)

    # apply SDL to std schema
    ls.show_message_log("compiling schema ..")
    try:
        schema, _warnings = s_ddl.apply_sdl(
            ls.state.schema_sdl, base_schema=std_schema
        )
        ls.state.schema = schema
        ls.show_message_log(".. done")
    except errors.EdgeDBError as error:
        ls.show_message_log(".. error")
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
        diagnostics.append(do, ls_utils.error_to_lsp(error))

    ls.state.schema_diagnostics = diagnostics
    return (schema, diagnostics)


def _load_std_schema(state: ls_server.State) -> s_schema.Schema:
    if state.std_schema is not None:
        return state.std_schema

    schema: s_schema.Schema = s_schema.EMPTY_SCHEMA
    for modname in s_schema.STD_SOURCES:
        schema = s_std.load_std_module(schema, modname)

    state.std_schema = schema
    return state.std_schema


# Given a path from a node to qlast.Schema root, collects the names of
# encapsulating modules.
def get_module_context(path: Iterable[qlast.Base]) -> str | None:
    mod_names = []
    for node in path:
        if isinstance(node, qlast.ModuleDeclaration):
            mod_names.append(node.name.name)
    if not mod_names:
        return None
    mod_names.reverse()
    return '::'.join(mod_names)
