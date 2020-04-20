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


from __future__ import annotations

from typing import *


from edb import errors
from edb.edgeql import ast as qlast

from . import scalars as s_scalars
from . import annos as s_anno
from . import objects as so
from . import objtypes as s_objtypes
from . import delta as sd
from . import types as s_types


if TYPE_CHECKING:
    from . import schema as s_schema


class AliasCommandContext(
    sd.ObjectCommandContext[Any],
    s_anno.AnnotationSubjectCommandContext
):
    pass


class AliasCommand(
    sd.QualifiedObjectCommand[so.QualifiedObject],
    s_types.TypeCommand[Any],
    context_class=AliasCommandContext,
):

    _scalar_cmd_map = {
        qlast.CreateAlias: s_scalars.CreateScalarType,
        qlast.AlterAlias: s_scalars.AlterScalarType,
        qlast.DropAlias: s_scalars.DeleteScalarType,
    }

    _objtype_cmd_map = {
        qlast.CreateAlias: s_objtypes.CreateObjectType,
        qlast.AlterAlias: s_objtypes.AlterObjectType,
        qlast.DropAlias: s_objtypes.DeleteObjectType,
    }

    _array_cmd_map = {
        qlast.CreateAlias: s_types.CreateArrayExprAlias,
        qlast.DropAlias: s_types.DeleteArrayExprAlias,
    }

    _tuple_cmd_map = {
        qlast.CreateAlias: s_types.CreateTupleExprAlias,
        qlast.DropAlias: s_types.DeleteTupleExprAlias,
    }

    @classmethod
    def command_for_ast_node(
        cls,
        astnode: qlast.DDLOperation,
        schema: s_schema.Schema,
        context: sd.CommandContext,
    ) -> Type[sd.Command]:
        modaliases = cls._modaliases_from_ast(schema, astnode, context)
        ctx = AliasCommandContext(
            schema,
            op=sd._dummy_object_command,
            scls=sd._dummy_object,
            modaliases=modaliases,
        )

        # Any is used here for simplicity: mapping is assigned
        # with one of the class attributes defined in this class
        mapping: Dict[Type[qlast.ObjectDDL], Any]

        with context(ctx):
            assert isinstance(astnode, qlast.NamedDDL)
            classname = cls._classname_from_ast(schema, astnode, context)

            if isinstance(astnode, qlast.CreateAlias):
                expr = cls._get_alias_expr(astnode)
                ir = cls._compile_view_expr(expr, classname, schema, context)
                scls = ir.stype
            else:
                scls = schema.get(classname)

            if isinstance(scls, s_scalars.ScalarType):
                mapping = cls._scalar_cmd_map
            elif isinstance(scls, s_types.Tuple):
                mapping = cls._tuple_cmd_map
            elif isinstance(scls, s_types.Array):
                mapping = cls._array_cmd_map
            elif isinstance(scls, s_objtypes.ObjectType):
                mapping = cls._objtype_cmd_map
            else:
                raise errors.InternalServerError(
                    f'unsupported alias type: '
                    f'{scls.get_schema_class_displayname()}'
                )

            # type ignore below is used, because the values are defined
            # as Any above
            return mapping[type(astnode)]  # type: ignore


class CreateAlias(AliasCommand):
    astnode = qlast.CreateAlias


class RenameAlias(AliasCommand):
    pass


class AlterAlias(AliasCommand):
    astnode = qlast.AlterAlias


class DeleteAlias(AliasCommand):
    astnode = qlast.DropAlias
