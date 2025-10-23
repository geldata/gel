#
# This source file is part of the EdgeDB open source project.
#
# Copyright 2020-present MagicStack Inc. and the EdgeDB authors.
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

from edb.schema import objects as s_obj
from edb.schema import schema as s_schema

from . import structure as sr_struct


SchemaClassLayout = dict[type[s_obj.Object], sr_struct.SchemaTypeLayout]


def parse_schema(
    base_schema: s_schema.Schema,
    data: str | bytes,
    schema_class_layout: SchemaClassLayout,
) -> s_schema.Schema:
    """Parse JSON-encoded schema objects and populate the schema with them.

    Args:
        schema:
            A schema instance to use as a starting point.
        data:
            A JSON-encoded schema object data as returned
            by an introspection query.
        schema_class_layout:
            A mapping describing schema class layout in the reflection,
            as returned from
            :func:`schema.reflection.structure.generate_structure`.

    Returns:
        A schema instance including objects encoded in the provided
        JSON sequence.
    """

    if isinstance(data, bytes):
        data = str(data, 'utf-8')
    if isinstance(base_schema, s_schema.ChainedSchema):
        base_schema = base_schema._base_schema
    assert isinstance(base_schema, s_schema.RustSchema)
    return s_schema.RustSchema.parse_reflection(base_schema, data)
