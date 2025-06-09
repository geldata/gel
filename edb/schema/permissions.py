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


from edb.edgeql import ast as qlast
from edb.edgeql import qltypes

from . import annos as s_anno
from . import delta as sd
from . import objects as so


class Permission(
    so.QualifiedObject,
    s_anno.AnnotationSubject,
    qlkind=qltypes.SchemaObjectClass.PERMISSION,
    data_safe=True,
):
    pass


class PermissionCommandContext(
    sd.ObjectCommandContext[Permission],
    s_anno.AnnotationSubjectCommandContext,
):
    pass


class PermissionCommand(
    sd.QualifiedObjectCommand[Permission],
    s_anno.AnnotationSubjectCommand[Permission],
    context_class=PermissionCommandContext,
):
    pass


class CreatePermission(
    PermissionCommand,
    sd.CreateObject[Permission],
):
    astnode = qlast.CreatePermission


class AlterPermission(
    PermissionCommand,
    sd.AlterObject[Permission],
):
    astnode = qlast.AlterPermission


class DeletePermission(
    PermissionCommand,
    sd.DeleteObject[Permission],
):
    astnode = qlast.DropPermission


class RenamePermission(
    PermissionCommand,
    sd.RenameObject[Permission],
):
    pass
