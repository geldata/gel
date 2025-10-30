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

from typing import Optional

from lsprotocol import types as lsp_types
import pygls
import pygls.workspace

from edb.common import span as edb_span
from edb.edgeql import ast as qlast
from edb.edgeql import tokenizer as qltokenizer
from edb.ir import ast as irast

from edb.schema import objects as s_objects
from edb.schema import name as s_name
from edb.schema import schema as s_schema
from edb.schema import types as s_types

from . import parsing as ls_parsing
from . import utils as ls_utils
from . import server as ls_server
from . import schema as ls_schema
from . import is_schema_file, is_edgeql_file


def get_definition(
    ls: ls_server.GelLanguageServer, params: lsp_types.DefinitionParams
) -> lsp_types.Location | list[lsp_types.Location]:
    doc_uri = params.text_document.uri
    document = ls.workspace.get_text_document(doc_uri)

    position: int = qltokenizer.line_col_to_source_point(
        document.source, params.position.line, params.position.character
    ).offset
    ls.show_message_log(f'get_definition at position = {position}')

    try:
        if is_schema_file(doc_uri):
            return _get_definition_in_schema(ls, document, position) or []

        elif is_edgeql_file(doc_uri):
            ql_ast_res = ls_parsing.parse(document)
            if not ql_ast_res.ok:
                return []
            ql_ast = ql_ast_res.ok

            if isinstance(ql_ast, qlast.Commands):
                return (
                    _get_definition_in_ql(ls, document, ql_ast, position) or []
                )
            else:
                # SDL in query files?
                pass
        else:
            ls.show_message_log(f'Unknown file type: {doc_uri}')

    except BaseException as e:
        ls_server.send_internal_error(ls, e)

    return []


def _get_definition_in_ql(
    ls: ls_server.GelLanguageServer,
    document: pygls.workspace.TextDocument,
    ql_ast: qlast.Commands,
    position: int,
) -> lsp_types.Location | None:
    # compile the whole doc
    # TODO: search ql ast before compiling all stmts
    _, ir_stmts = ls_server.compile_ql(ls, document, ql_ast.commands)

    # find the ir node at the position
    node_path = None
    for ir_stmt in ir_stmts:
        node_path = edb_span.find_by_source_position(ir_stmt, position)
        if node_path:
            break

    if not node_path:
        ls.show_message_log(f"cannot find span in {len(ir_stmts)} stmts")
        return None
    node = node_path[0]
    assert isinstance(node, irast.Base), node
    ls.show_message_log(f"node: {node}")

    schema = ir_stmt.schema
    assert schema

    # lookup schema objects depending on which ir node we are over
    target = _determine_ir_target(node, schema)
    if not target:
        ls.show_message_log(f"don't know how to lookup schema by {node}")
        return None

    return _schema_obj_to_doc_location(ls, target, schema, document)


def _determine_ir_target(
    node: irast.Base, schema: s_schema.Schema
) -> Optional[s_objects.Object]:
    # special handling: references to WITH bindings
    if (
        isinstance(node, irast.SetE)
        and node.is_binding == irast.BindingKind.With
    ):
        target = schema.get_by_id(
            node.typeref.id, type=s_objects.InheritingObject
        )
        assert target
        while (
            target.get_span(schema) is None
            and isinstance(target, s_types.Type)
            and target.get_from_alias(schema)
        ):
            target = target.get_bases(schema).objects(schema)[0]
        return target

    # unwrap a set
    if isinstance(node, irast.SetE):
        node = node.expr

    # unwrap select stmts
    while isinstance(node, irast.SelectStmt):
        node = node.result.expr

    # references to object types
    if isinstance(node, irast.TypeRoot):
        return schema.get_by_id(node.typeref.id)

    # references to pointers
    if isinstance(node, irast.Pointer) and isinstance(
        node.ptrref, irast.PointerRef
    ):
        return schema.get_by_id(node.ptrref.id)

    return None


# Finds definition of names in schema files.
#
# Parses the file and finds the ObjectRef at the given position. Then, it
# computes "module context", by looking at names of encapsulating modules so
# it can convert ObjectRef into a qualified name. Then it just looks up that
# name in the schema.
#
# This impl might be lacking, since it does not use the code we use for name
# resolution in the main compiler (tracing.py), and might report some
# definitions incorrectly (i.e. within expressions).
def _get_definition_in_schema(
    ls: ls_server.GelLanguageServer,
    document: pygls.workspace.TextDocument,
    position: int,
) -> lsp_types.Location | None:
    res = ls_schema._ensure_schema_docs_loaded(ls)
    if res.err:
        return None

    # parse current doc, return on errors
    _ = ls_schema._parse_schema(ls)
    assert ls.state.schema_sdl

    # find the span in ql ast
    node_path = edb_span.find_by_source_position(ls.state.schema_sdl, position)
    if not node_path:
        return None

    # ls.show_message_log(f"found node: {dump_to_str(node_path[0])}")

    # only resolve ObjectRefs
    if not isinstance(node_path[0], qlast.ObjectRef):
        return None

    # convert qlast.ObjectRef into a sn.QualName
    name: str = node_path[0].name
    module: Optional[str] = node_path[0].module
    if not module:
        module = ls_schema.get_module_context(node_path[1:])
    if not module:
        return None
    q_name = s_name.QualName(module, name)
    ls.show_message_log(f"name: {q_name}")

    # lookup the name in latest compiled schema
    schema = ls.state.schema
    if not schema:
        return None
    obj = schema.get(q_name, default=None)
    if not obj:
        ls.show_message_log(f"object with this name not found")
        return None

    return _schema_obj_to_doc_location(ls, obj, schema, document)


def _schema_obj_to_doc_location(
    ls: ls_server.GelLanguageServer,
    obj: s_objects.Object,
    schema: s_schema.Schema,
    curr_doc: pygls.workspace.TextDocument,
) -> lsp_types.Location | None:
    name = obj.get_name(schema)
    ls.show_message_log(f"find schema object: {name}")

    span: edb_span.Span | None = obj.get_span(schema)
    if not span:
        ls.show_message_log(f"no span for schema object")
        return None

    # find originating document
    doc: Optional[pygls.workspace.TextDocument] = None

    # is doc the current document?
    if span.filename == curr_doc.filename:
        doc = curr_doc

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
