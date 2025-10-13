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

from typing import (
    Any,
    Callable,
    Iterable,
    Iterator,
    Mapping,
    NoReturn,
    Optional,
    overload,
    Self,
    TYPE_CHECKING,
)

import abc
import collections
import itertools

import immutables as immu

from edb import errors
from edb.common import english
from edb.common import lru

from . import casts as s_casts
from . import migrations as s_migrations
from . import modules as s_mod
from . import name as sn
from . import objects as so
from . import operators as s_oper
from . import functions as s_func
from . import pseudo as s_pseudo
from . import types as s_types
from . import _schema as rust_schema

if TYPE_CHECKING:
    import uuid
    from edb.common import parsing

    Refs_T = immu.Map[
        uuid.UUID,
        immu.Map[
            tuple[type[so.Object], str],
            immu.Map[uuid.UUID, None],
        ],
    ]

EXT_MODULE = sn.UnqualName('ext')

STD_MODULES = (
    sn.UnqualName('std'),
    sn.UnqualName('schema'),
    sn.UnqualName('std::math'),
    sn.UnqualName('sys'),
    sn.UnqualName('sys::perm'),
    sn.UnqualName('cfg'),
    sn.UnqualName('cfg::perm'),
    sn.UnqualName('std::cal'),
    sn.UnqualName('std::net'),
    sn.UnqualName('std::net::http'),
    sn.UnqualName('std::net::perm'),
    sn.UnqualName('std::pg'),
    sn.UnqualName('std::_test'),
    sn.UnqualName('std::fts'),
    sn.UnqualName('std::lang'),
    sn.UnqualName('std::lang::go'),
    sn.UnqualName('std::lang::js'),
    sn.UnqualName('std::lang::py'),
    sn.UnqualName('std::lang::rs'),
    EXT_MODULE,
    sn.UnqualName('std::enc'),
)

SPECIAL_MODULES = (
    sn.UnqualName('__derived__'),
    sn.UnqualName('__ext_casts__'),
    sn.UnqualName('__ext_index_matches__'),
)

# Specifies the order of processing of files and directories in lib/
STD_SOURCES = (
    sn.UnqualName('std'),
    sn.UnqualName('schema'),
    sn.UnqualName('math'),
    sn.UnqualName('sys'),
    sn.UnqualName('cfg'),
    sn.UnqualName('cal'),
    sn.UnqualName('ext'),
    sn.UnqualName('enc'),
    sn.UnqualName('pg'),
    sn.UnqualName('fts'),
    sn.UnqualName('net'),
)
TESTMODE_SOURCES = (
    sn.UnqualName('_testmode'),
)


class Schema(abc.ABC):
    '''
    Data store for objects and their data.

    Objects have:
    - a class (also called mcls for meta class or scls for schema class),
    - an id (of type UUID),
    - data (a tuple of python values),
    - name (of type sn.Name).

    Objects can be retrieved by:
    - id,
    - name (fully qualified),
    - shortname (only for function and operator class),
    - references.
    '''

    @abc.abstractmethod
    def _get_by_name(
        self,
        name: sn.Name,
    ) -> Optional[so.Object]:
        raise NotImplementedError

    @abc.abstractmethod
    def _get_by_shortname[T: s_func.Function | s_oper.Operator](
        self,
        mcls: type[T],
        shortname: sn.Name,
    ) -> Optional[tuple[T, ...]]:
        raise NotImplementedError

    @abc.abstractmethod
    def _get_by_globalname[T: so.Object](
        self, mcls: type[T], name: sn.Name,
    ) -> Optional[T]:
        raise NotImplementedError

    @abc.abstractmethod
    def add(
        self,
        id: uuid.UUID,
        sclass: type[so.Object],
        data: tuple[Any, ...],
    ) -> Self:
        raise NotImplementedError

    def discard(self: Self, obj: so.Object) -> Self:
        if self.has_object(obj.id):
            return self.delete(obj)
        else:
            return self

    @abc.abstractmethod
    def delete(self: Self, obj: so.Object) -> Self:
        raise NotImplementedError

    @abc.abstractmethod
    def delist(self: Self, name: sn.Name) -> Self:
        raise NotImplementedError

    @abc.abstractmethod
    def update_obj(
        self: Self,
        obj: so.Object,
        updates: Mapping[str, Any],
    ) -> Self:
        raise NotImplementedError

    @abc.abstractmethod
    def get_data_raw(
        self,
        obj: so.Object,
    ) -> Optional[tuple[Any, ...]]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_field_raw(
        self,
        obj: so.Object,
        field_index: int,
    ) -> Optional[Any]:
        raise NotImplementedError

    @abc.abstractmethod
    def set_field(
        self: Self,
        obj: so.Object,
        field: str,
        value: Any,
    ) -> Self:
        raise NotImplementedError

    @abc.abstractmethod
    def unset_field(
        self: Self,
        obj: so.Object,
        field: str,
    ) -> Self:
        raise NotImplementedError

    @abc.abstractmethod
    def has_object(self, object_id: uuid.UUID) -> bool:
        raise NotImplementedError

    def has_module(self, name: str) -> bool:
        return self.get_global(s_mod.Module, name, None) is not None

    def has_migration(self, name: str) -> bool:
        return self.get_global(s_migrations.Migration, name, None) is not None

    @overload
    def get_by_id(
        self,
        obj_id: uuid.UUID,
        default: so.Object | so.NoDefaultT = so.NoDefault,
        *,
        type: None = None,
    ) -> so.Object:
        ...

    @overload
    def get_by_id(
        self,
        obj_id: uuid.UUID,
        default: so.Object_T | so.NoDefaultT = so.NoDefault,
        *,
        type: Optional[type[so.Object_T]] = None,
    ) -> so.Object_T:
        ...

    @overload
    def get_by_id(
        self,
        obj_id: uuid.UUID,
        default: None = None,
        *,
        type: Optional[type[so.Object_T]] = None,
    ) -> Optional[so.Object_T]:
        ...

    def get_by_id(
        self,
        obj_id: uuid.UUID,
        default: so.Object_T | so.NoDefaultT | None = so.NoDefault,
        *,
        type: Optional[type[so.Object_T]] = None,
    ) -> Optional[so.Object_T]:
        return self._get_by_id(obj_id, default, type=type)

    @abc.abstractmethod
    def _get_by_id(
        self,
        obj_id: uuid.UUID,
        default: so.Object_T | so.NoDefaultT | None = so.NoDefault,
        *,
        type: Optional[type[so.Object_T]] = None,
    ) -> Optional[so.Object_T]:
        raise NotImplementedError

    @overload
    def get_by_name[T: so.Object](
        self,
        name: sn.Name | str,
        default: T | so.NoDefaultT = so.NoDefault,
        type: Optional[type[T]] = None,
        span: Optional[parsing.Span] = None
    ) -> T: ...

    @overload
    def get_by_name[T: so.Object](
        self,
        name: sn.Name | str,
        default: None = None,
        type: Optional[type[T]] = None,
        span: Optional[parsing.Span] = None
    ) -> Optional[T]: ...

    def get_by_name[T: so.Object](
        self,
        name: sn.Name | str,
        default: T | so.NoDefaultT | None = so.NoDefault,
        type: Optional[type[T]] = None,
        span: Optional[parsing.Span] = None
    ) -> Optional[T]:
        """Retrieve object by name (not global name or short name)"""

        if isinstance(name, str):
            name = sn.QualName.from_string(name)
        obj = self._get_by_name(name)
        if obj is not None:
            if type is not None:
                if not isinstance(obj, type):
                    Schema.raise_wrong_type(name, obj.__class__, type, span)
            return obj  # type: ignore
        elif default is not so.NoDefault:
            return default
        else:
            Schema.raise_bad_reference(name, type=type)

    def get_by_shortname[T: s_func.Function | s_oper.Operator](
        self,
        mcls: type[T],
        shortname: str | sn.Name,
        span: Optional[parsing.Span] = None
    ) -> tuple[T, ...]:
        """Retrieve object by shortname"""

        if isinstance(shortname, str):
            shortname = sn.QualName.from_string(shortname)
        objs = self._get_by_shortname(mcls, shortname)
        if objs is not None:
            return objs
        else:
            Schema.raise_bad_reference(shortname, type=mcls)

    # TODO: rename to get_by_globalname
    @overload
    def get_global[T: so.Object](
        self,
        mcls: type[T],
        name: str | sn.Name,
        default: T | so.NoDefaultT = so.NoDefault,
    ) -> T:
        ...

    # TODO: rename to get_by_globalname
    @overload
    def get_global[T: so.Object](
        self,
        mcls: type[T],
        name: str | sn.Name,
        default: None = None,
    ) -> Optional[T]:
        ...

    # TODO: rename to get_by_globalname
    def get_global[T: so.Object](
        self,
        mcls: type[T],
        name: str | sn.Name,
        default: T | so.NoDefaultT | None = so.NoDefault,
    ) -> Optional[T]:
        if isinstance(name, str):
            name = sn.UnqualName(name)
        obj = self._get_by_globalname(mcls, name)
        if obj is not None:
            return obj
        elif default is not so.NoDefault:
            return default
        else:
            Schema.raise_bad_reference(name, type=mcls)

    @overload
    def get(
        self,
        name: str | sn.Name,
        default: so.Object | so.NoDefaultT = so.NoDefault,
        *,
        module_aliases: Optional[Mapping[Optional[str], str]] = None,
        condition: Optional[Callable[[so.Object], bool]] = None,
        label: Optional[str] = None,
        span: Optional[parsing.Span] = None,
    ) -> so.Object:
        ...

    @overload
    def get(
        self,
        name: str | sn.Name,
        default: None,
        *,
        module_aliases: Optional[Mapping[Optional[str], str]] = None,
        condition: Optional[Callable[[so.Object], bool]] = None,
        label: Optional[str] = None,
        span: Optional[parsing.Span] = None,
    ) -> Optional[so.Object]:
        ...

    @overload
    def get[T: so.Object](
        self,
        name: str | sn.Name,
        default: T | so.NoDefaultT = so.NoDefault,
        *,
        module_aliases: Optional[Mapping[Optional[str], str]] = None,
        type: type[T],
        condition: Optional[Callable[[so.Object], bool]] = None,
        label: Optional[str] = None,
        span: Optional[parsing.Span] = None,
    ) -> T:
        ...

    @overload
    def get[T: so.Object](
        self,
        name: str | sn.Name,
        default: None,
        *,
        module_aliases: Optional[Mapping[Optional[str], str]] = None,
        type: type[T],
        condition: Optional[Callable[[so.Object], bool]] = None,
        label: Optional[str] = None,
        span: Optional[parsing.Span] = None,
    ) -> Optional[T]:
        ...

    @overload
    def get(
        self,
        name: str | sn.Name,
        default: so.Object | so.NoDefaultT | None = so.NoDefault,
        *,
        module_aliases: Optional[Mapping[Optional[str], str]] = None,
        type: Optional[type[so.Object]] = None,
        condition: Optional[Callable[[so.Object], bool]] = None,
        label: Optional[str] = None,
        span: Optional[parsing.Span] = None,
    ) -> Optional[so.Object]:
        ...

    def get(
        self,
        name: str | sn.Name,
        default: so.Object | so.NoDefaultT | None = so.NoDefault,
        *,
        module_aliases: Optional[Mapping[Optional[str], str]] = None,
        type: Optional[type[so.Object]] = None,
        condition: Optional[Callable[[so.Object], bool]] = None,
        label: Optional[str] = None,
        span: Optional[parsing.Span] = None,
    ) -> Optional[so.Object]:

        def getter(schema: Schema, name: sn.Name) -> Optional[so.Object]:
            obj = schema._get_by_name(name)
            if obj is not None and condition is not None:
                if not condition(obj):
                    obj = None
            return obj

        obj = lookup(
            self,
            name,
            getter=getter,
            default=default,
            module_aliases=module_aliases,
        )

        if obj is not so.NoDefault:
            # We do our own type check, instead of using get_by_id's, so
            # we can produce a user-facing error message.
            if obj and type is not None and not isinstance(obj, type):
                Schema.raise_wrong_type(name, obj.__class__, type, span)

            return obj
        else:
            Schema.raise_bad_reference(
                name=name,
                label=label,
                module_aliases=module_aliases,
                span=span,
                type=type,
            )

    @abc.abstractmethod
    def _get_object_ids(self) -> Iterable[uuid.UUID]:
        raise NotImplementedError

    @abc.abstractmethod
    def _get_global_name_ids(
        self
    ) -> Iterable[tuple[type[so.Object], uuid.UUID]]:
        raise NotImplementedError

    def get_children(
        self,
        scls: so.Object_T,
    ) -> frozenset[so.Object_T]:
        # Ideally get_referrers needs to be made generic via
        # an overload on scls_type, but mypy crashes on that.
        return self.get_referrers(
            scls,
            scls_type=type(scls),
            field_name='bases',
        )

    def get_descendants(
        self,
        scls: so.Object_T,
    ) -> frozenset[so.Object_T]:
        return self.get_referrers(
            scls, scls_type=type(scls), field_name='ancestors')

    def get_objects[Object_T: so.Object](
        self,
        *,
        exclude_stdlib: bool = False,
        exclude_global: bool = False,
        exclude_extensions: bool = False,
        exclude_internal: bool = True,
        included_modules: Optional[Iterable[sn.Name]] = None,
        excluded_modules: Optional[Iterable[sn.Name]] = None,
        included_items: Optional[Iterable[sn.Name]] = None,
        excluded_items: Optional[Iterable[sn.Name]] = None,
        type: Optional[type[Object_T]] = None,
        extra_filters: Iterable[Callable[[Schema, Object_T], bool]] = (),
    ) -> SchemaIterator[Object_T]:
        return SchemaIterator[Object_T](
            self,
            self._get_object_ids(),
            exclude_global=exclude_global,
            exclude_stdlib=exclude_stdlib,
            exclude_extensions=exclude_extensions,
            exclude_internal=exclude_internal,
            included_modules=included_modules,
            excluded_modules=excluded_modules,
            included_items=included_items,
            excluded_items=excluded_items,
            type=type,
            extra_filters=extra_filters,
        )

    def get_modules(self) -> tuple[s_mod.Module, ...]:
        modules = []
        for mcls, id in self._get_global_name_ids():
            if mcls is s_mod.Module:
                modules.append(mcls(_private_id=id))
        return tuple(modules)  # type: ignore

    def get_last_migration(self) -> Optional[s_migrations.Migration]:
        return _get_last_migration(self)

    def get_casts_to_type(
        self,
        to_type: s_types.Type,
        *,
        implicit: bool = False,
        assignment: bool = False,
    ) -> frozenset[s_casts.Cast]:
        return self._get_casts(
            to_type,
            disposition='to_type',
            implicit=implicit,
            assignment=assignment,
        )

    def get_casts_from_type(
        self,
        from_type: s_types.Type,
        *,
        implicit: bool = False,
        assignment: bool = False,
    ) -> frozenset[s_casts.Cast]:
        return self._get_casts(
            from_type,
            disposition='from_type',
            implicit=implicit,
            assignment=assignment,
        )

    @lru.lru_method_cache()
    def _get_casts(
        self,
        stype: s_types.Type,
        *,
        disposition: str,
        implicit: bool = False,
        assignment: bool = False,
    ) -> frozenset[s_casts.Cast]:
        all_casts = self.get_referrers(
            stype, scls_type=s_casts.Cast, field_name=disposition
        )

        casts = []
        for castobj in all_casts:
            if implicit and not castobj.get_allow_implicit(self):
                continue
            if assignment and not castobj.get_allow_assignment(self):
                continue
            casts.append(castobj)

        return frozenset(casts)

    @overload
    def get_referrers[T: so.Object](
        self,
        scls: so.Object,
        *,
        scls_type: type[T],
        field_name: Optional[str] = None,
    ) -> frozenset[T]:
        ...

    @overload
    def get_referrers(
        self,
        scls: so.Object,
        *,
        scls_type: None = None,
        field_name: Optional[str] = None,
    ) -> frozenset[so.Object]:
        ...

    @abc.abstractmethod
    def get_referrers(
        self,
        scls: so.Object,
        *,
        scls_type: Optional[type[so.Object]] = None,
        field_name: Optional[str] = None,
    ) -> frozenset[so.Object]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_referrers_ex(
        self,
        scls: so.Object,
        *,
        scls_type: Optional[type[so.Object_T]] = None,
    ) -> dict[
        tuple[type[so.Object_T], str],
        frozenset[so.Object_T],
    ]:
        raise NotImplementedError

    @staticmethod
    def raise_wrong_type(
        name: str | sn.Name,
        actual_type: type[so.Object_T],
        expected_type: type[so.Object_T],
        span: Optional[parsing.Span],
    ) -> NoReturn:
        refname = str(name)

        actual_type_name = actual_type.get_schema_class_displayname()
        expected_type_name = expected_type.get_schema_class_displayname()
        raise errors.InvalidReferenceError(
            f'{refname!r} exists, but is {english.add_a(actual_type_name)}, '
            f'not {english.add_a(expected_type_name)}',
            span=span,
        )

    @staticmethod
    def raise_bad_reference(
        name: str | sn.Name,
        *,
        label: Optional[str] = None,
        module_aliases: Optional[Mapping[Optional[str], str]] = None,
        span: Optional[parsing.Span] = None,
        type: Optional[type[so.Object]] = None,
    ) -> NoReturn:
        refname = str(name)

        if label is None:
            if type is not None:
                label = type.get_schema_class_displayname()
            else:
                label = 'schema item'

        if type is not None:
            if issubclass(type, so.QualifiedObject):
                if not sn.is_qualified(refname):
                    if module_aliases is not None:
                        default_module = module_aliases.get(None)
                        if default_module is not None:
                            refname = type.get_displayname_static(
                                sn.QualName(default_module, refname),
                            )
                else:
                    refname = type.get_displayname_static(
                        sn.QualName.from_string(refname))
            else:
                refname = type.get_displayname_static(
                    sn.UnqualName.from_string(refname))

        raise errors.InvalidReferenceError(
            f'{label} {refname!r} does not exist',
            span=span,
        )


def lookup[T](
    schema: Schema,
    name: sn.Name | str,
    *,
    getter: Callable[[Schema, sn.QualName], T | None],
    default: T | so.NoDefaultT = so.NoDefault,
    module_aliases: Optional[Mapping[Optional[str], str]],
) -> T | so.NoDefaultT:
    """
    Find something in the schema with a given name.

    This function mostly mirrors edgeql.tracer.resolve_name
    except:
    - When searching in std, disallow some modules (often the base modules)
    - If no result found, return default
    """
    if isinstance(name, str):
        name = sn.name_from_string(name)

    obj_name = name.name
    module = name.module if isinstance(name, sn.QualName) else None
    orig_module = module

    if module == '__std__':
        fqname = sn.QualName('std', obj_name)
        result = getter(schema, fqname)
        if result is not None:
            return result
        else:
            return default

    # Apply module aliases
    module = apply_module_aliases(
        module, module_aliases
    )

    # Check if something matches the name
    if module is not None:
        fqname = sn.QualName(module, obj_name)
        result = getter(schema, fqname)
        if result is not None:
            return result

    # For unqualified names, fallback to std::{obj_name}
    if orig_module is None:
        fqname = sn.QualName('std', obj_name)
        result = getter(schema, fqname)
        if result is not None:
            return result

    # For qualified names, fallback to std::{module}::{obj_name}
    # This is allowed only when there is no top-level module with the same name.
    if module and not schema.has_module(module.split('::')[0]):
        fqname = sn.QualName(f'std::{module}', obj_name)
        result = getter(schema, fqname)
        if result is not None:
            return result

    return default


def apply_module_aliases(
    module: str | None,
    module_aliases: Optional[Mapping[Optional[str], str]],
) -> str | None:
    if module_aliases is not None:
        # Apply modalias
        first: Optional[str]
        if module:
            first, sep, rest = module.partition('::')
        else:
            first, sep, rest = module, '', ''

        fq_module = module_aliases.get(first)
        if fq_module is not None:
            module = fq_module + sep + rest

    return module


def upgrade_schema(schema: Schema) -> Schema:
    """Repair a schema object serialized by an older patch version

    When an edgeql+schema patch adds fields to schema types, old
    serialized schemas will be broken, since their tuples are missing
    the fields.

    In this situation, we run through all the data tuples and fill
    them out. The upgraded version will then be cached.
    """

    if isinstance(schema, ChainedSchema):
        return ChainedSchema(
            base_schema=upgrade_schema(schema._base_schema),
            top_schema=upgrade_schema(schema._top_schema),
            global_schema=upgrade_schema(schema._global_schema),
        )

    # TODO
    return None  # type: ignore


class SchemaIterator[Object_T: so.Object]:
    def __init__(
        self,
        schema: Schema,
        object_ids: Iterable[uuid.UUID],
        *,
        exclude_stdlib: bool = False,
        exclude_global: bool = False,
        exclude_extensions: bool = False,
        exclude_internal: bool = True,
        included_modules: Optional[Iterable[sn.Name]],
        excluded_modules: Optional[Iterable[sn.Name]],
        included_items: Optional[Iterable[sn.Name]] = None,
        excluded_items: Optional[Iterable[sn.Name]] = None,
        type: Optional[type[Object_T]] = None,
        extra_filters: Iterable[Callable[[Schema, Object_T], bool]] = (),
    ) -> None:

        filters = []

        if type is not None:
            t = type
            filters.append(lambda schema, obj: isinstance(obj, t))

        if included_modules:
            modules = frozenset(included_modules)
            filters.append(
                lambda schema, obj:
                    isinstance(obj, so.QualifiedObject) and
                    obj.get_name(schema).get_module_name() in modules)

        if excluded_modules or exclude_stdlib:
            excmod: set[sn.Name] = set()
            if excluded_modules:
                excmod.update(excluded_modules)
            if exclude_stdlib:
                excmod.update(STD_MODULES)
            filters.append(
                lambda schema, obj: (
                    not isinstance(obj, so.QualifiedObject)
                    or obj.get_name(schema).get_module_name() not in excmod
                )
            )

        if included_items:
            objs = frozenset(included_items)
            filters.append(
                lambda schema, obj: obj.get_name(schema) in objs)

        if excluded_items:
            objs = frozenset(excluded_items)
            filters.append(
                lambda schema, obj: obj.get_name(schema) not in objs)

        if exclude_stdlib:
            filters.append(
                lambda schema, obj: not isinstance(obj, s_pseudo.PseudoType)
            )

        if exclude_extensions:
            filters.append(
                lambda schema, obj:
                obj.get_name(schema).get_root_module_name() != EXT_MODULE
            )

        if exclude_global:
            filters.append(
                lambda schema, obj: not isinstance(obj, so.GlobalObject)
            )

        if exclude_internal:
            filters.append(
                lambda schema, obj: not isinstance(obj, so.InternalObject)
            )

        # Extra filters are last, because they might depend on type.
        filters.extend(extra_filters)

        self._filters = filters
        self._schema = schema
        self._object_ids = object_ids

    def __iter__(self) -> Iterator[Object_T]:
        filters = self._filters
        schema = self._schema
        get_by_id = schema.get_by_id
        for obj_id in self._object_ids:
            obj = get_by_id(obj_id)
            if all(f(self._schema, obj) for f in filters):
                yield obj  # type: ignore


class ChainedSchema(Schema):

    __slots__ = ('_base_schema', '_top_schema', '_global_schema')

    def __init__(
        self, base_schema: Schema, top_schema: Schema, global_schema: Schema
    ) -> None:
        self._base_schema = base_schema
        self._top_schema = top_schema
        self._global_schema = global_schema

    def _get_object_ids(self) -> Iterable[uuid.UUID]:
        return itertools.chain(
            self._base_schema._get_object_ids(),
            self._top_schema._get_object_ids(),
            self._global_schema._get_object_ids(),
        )

    def _get_global_name_ids(
        self
    ) -> Iterable[tuple[type[so.Object], uuid.UUID]]:
        return itertools.chain(
            self._base_schema._get_global_name_ids(),
            self._top_schema._get_global_name_ids(),
            self._global_schema._get_global_name_ids(),
        )

    def get_top_schema(self) -> Schema:
        return self._top_schema

    def get_global_schema(self) -> Schema:
        return self._global_schema

    def add(
        self,
        id: uuid.UUID,
        sclass: type[so.Object],
        data: tuple[Any, ...],
    ) -> ChainedSchema:
        if issubclass(sclass, so.GlobalObject):
            return ChainedSchema(
                self._base_schema,
                self._top_schema,
                self._global_schema.add(id, sclass, data),
            )
        else:
            return ChainedSchema(
                self._base_schema,
                self._top_schema.add(id, sclass, data),
                self._global_schema,
            )

    def delete(self, obj: so.Object) -> ChainedSchema:
        if isinstance(obj, so.GlobalObject):
            return ChainedSchema(
                self._base_schema,
                self._top_schema,
                self._global_schema.delete(obj),
            )
        else:
            return ChainedSchema(
                self._base_schema,
                self._top_schema.delete(obj),
                self._global_schema,
            )

    def delist(
        self,
        name: sn.Name,
    ) -> ChainedSchema:
        return ChainedSchema(
            self._base_schema,
            self._top_schema.delist(name),
            self._global_schema,
        )

    def update_obj(
        self,
        obj: so.Object,
        updates: Mapping[str, Any],
    ) -> ChainedSchema:
        if isinstance(obj, so.GlobalObject):
            return ChainedSchema(
                self._base_schema,
                self._top_schema,
                self._global_schema.update_obj(obj, updates),
            )
        else:
            obj_id = obj.id
            base_obj = self._base_schema.get_by_id(obj_id, default=None)
            if (
                base_obj is not None
                and not self._top_schema.has_object(obj_id)
            ):
                top_schema = self._top_schema.add(
                    obj_id,
                    type(base_obj),
                    self._base_schema.get_data_raw(base_obj),
                )
            else:
                top_schema = self._top_schema

            return ChainedSchema(
                self._base_schema,
                top_schema.update_obj(obj, updates),
                self._global_schema,
            )

    def get_data_raw(
        self,
        obj: so.Object,
    ) -> Optional[tuple[Any, ...]]:
        data = self._top_schema.get_data_raw(obj)
        if data is not None:
            return data
        data = self._base_schema.get_data_raw(obj)
        if data is not None:
            return data
        return self._global_schema.get_data_raw(obj)

    def get_field_raw(
        self,
        obj: so.Object,
        field_index: int,
    ) -> Optional[Any]:
        if self._top_schema.has_object(obj.id):
            return self._top_schema.get_field_raw(obj, field_index)
        if self._base_schema.has_object(obj.id):
            return self._base_schema.get_field_raw(obj, field_index)
        if self._global_schema.has_object(obj.id):
            return self._global_schema.get_field_raw(obj, field_index)
        raise AssertionError(
            f'cannot get item data: item {str(obj.id)!r} '
            f'is not present in the schema {self!r}'
        )

    def set_field(
        self,
        obj: so.Object,
        fieldname: str,
        value: Any,
    ) -> ChainedSchema:
        if isinstance(obj, so.GlobalObject):
            return ChainedSchema(
                self._base_schema,
                self._top_schema,
                self._global_schema.set_field(obj, fieldname, value),
            )
        else:
            return ChainedSchema(
                self._base_schema,
                self._top_schema.set_field(obj, fieldname, value),
                self._global_schema,
            )

    def unset_field(
        self,
        obj: so.Object,
        field: str,
    ) -> ChainedSchema:
        if isinstance(obj, so.GlobalObject):
            return ChainedSchema(
                self._base_schema,
                self._top_schema,
                self._global_schema.unset_field(obj, field),
            )
        else:
            return ChainedSchema(
                self._base_schema,
                self._top_schema.unset_field(obj, field),
                self._global_schema,
            )

    def get_referrers(
        self,
        scls: so.Object,
        *,
        scls_type: Optional[type[so.Object_T]] = None,
        field_name: Optional[str] = None,
    ) -> frozenset[so.Object_T]:
        return (
            self._base_schema.get_referrers(  # type: ignore [return-value]
                scls,
                scls_type=scls_type,
                field_name=field_name,
            )
            | self._top_schema.get_referrers(
                scls,
                scls_type=scls_type,
                field_name=field_name,
            )
            | self._global_schema.get_referrers(  # type: ignore [operator]
                scls,
                scls_type=scls_type,
                field_name=field_name,
            )
        )

    def get_referrers_ex(
        self,
        scls: so.Object,
        *,
        scls_type: Optional[type[so.Object_T]] = None,
    ) -> dict[
        tuple[type[so.Object_T], str],
        frozenset[so.Object_T],
    ]:
        base = self._base_schema.get_referrers_ex(scls, scls_type=scls_type)
        top = self._top_schema.get_referrers_ex(scls, scls_type=scls_type)
        gl = self._global_schema.get_referrers_ex(scls, scls_type=scls_type)
        return {
            k: (
                base.get(k, frozenset())
                | top.get(k, frozenset())
                | gl.get(k, frozenset())
            )
            for k in itertools.chain(base, top)
        }

    def _get_by_id(
        self,
        obj_id: uuid.UUID,
        default: so.Object_T | so.NoDefaultT | None = so.NoDefault,
        *,
        type: Optional[type[so.Object_T]] = None,
    ) -> Optional[so.Object_T]:
        obj = self._top_schema.get_by_id(obj_id, type=type, default=None)
        if obj is None:
            obj = self._base_schema.get_by_id(
                obj_id, default=None, type=type)
            if obj is None:
                obj = self._global_schema.get_by_id(
                    obj_id, default=default, type=type)
        return obj

    # Important micro-optimization
    if not TYPE_CHECKING:
        get_by_id = _get_by_id

    def _get_by_globalname[T: so.Object](
        self, mcls: type[T], name: sn.Name,
    ) -> Optional[T]:
        if issubclass(mcls, so.GlobalObject):
            if o := self._global_schema._get_by_globalname(
                mcls, name
            ):
                return o  # type: ignore
        if obj := self._top_schema._get_by_globalname(mcls, name):
            return obj
        return self._base_schema._get_by_globalname(mcls, name)

    def _get_by_shortname[T: s_func.Function | s_oper.Operator](
        self,
        mcls: type[T],
        shortname: sn.Name,
    ) -> Optional[tuple[T, ...]]:
        objs = self._base_schema._get_by_shortname(mcls, shortname)
        if objs is not None:
            return objs
        return self._top_schema._get_by_shortname(mcls, shortname)

    def _get_by_name(
        self,
        name: sn.Name,
    ) -> Optional[so.Object]:
        objs = self._base_schema._get_by_name(name)
        if objs is not None:
            return objs
        return self._top_schema._get_by_name(name)

    def has_object(self, object_id: uuid.UUID) -> bool:
        return (
            self._base_schema.has_object(object_id)
            or self._top_schema.has_object(object_id)
            or self._global_schema.has_object(object_id)
        )


@lru.per_job_lru_cache()
def _get_operators(
    schema: Schema,
    name: sn.Name,
) -> tuple[s_oper.Operator, ...] | None:
    return schema._get_by_shortname(s_oper.Operator, name)


@lru.per_job_lru_cache()
def _get_last_migration(
    schema: Schema,
) -> Optional[s_migrations.Migration]:

    migrations: list[s_migrations.Migration] = [
        mcls(_private_id=id)  # type: ignore
        for mcls, id in schema._get_global_name_ids()
        if mcls is s_migrations.Migration
    ]

    if not migrations:
        return None

    migration_map = collections.defaultdict(list)
    root = None
    for m in migrations:
        parents = m.get_parents(schema).objects(schema)
        if not parents:
            if root is not None:
                raise errors.InternalServerError(
                    'multiple migration roots found')
            root = m
        for parent in parents:
            migration_map[parent].append(m)

    if root is None:
        raise errors.InternalServerError('cannot find migration root')

    latest = root
    while children := migration_map[latest]:
        if len(children) > 1:
            raise errors.InternalServerError(
                'nonlinear migration history detected')
        latest = children[0]

    return latest


class RustSchema(Schema):
    def __init__(self, inner: rust_schema.Schema):
        self.inner = inner

    @staticmethod
    def empty() -> RustSchema:
        return RustSchema(rust_schema.Schema.empty())

    @staticmethod
    def parse_reflection(
        base_schema: RustSchema, reflected_json: str
    ) -> Schema:
        return RustSchema(
            rust_schema.Schema.parse_reflection(
                base_schema.inner, reflected_json
            )
        )

    def dump(self, pretty: bool = False) -> str:
        return self.inner.dump(pretty=pretty)

    def has_object(self, id: uuid.UUID) -> bool:
        return self.inner.has_object(id)

    def _get_by_id(
        self,
        obj_id: uuid.UUID,
        default: so.Object_T | so.NoDefaultT | None = so.NoDefault,
        *,
        type: Optional[type[so.Object_T]] = None,
    ) -> Optional[so.Object_T]:
        obj = self.inner.get_by_id(obj_id)
        if obj is None:
            if default is so.NoDefault:
                raise LookupError(
                    f'reference to a non-existent schema item {obj_id}'
                    f' in schema {self!r}'
                ) from None
            else:
                return default

        if type is not None and not isinstance(obj, type):
            raise TypeError(
                f'schema object {obj_id!r} exists, but is a '
                f'{obj.__class__.get_schema_class_displayname()!r}, '
                f'not a {type.get_schema_class_displayname()!r}'
            )
        return obj  # type: ignore

    def get_by_name(
        self, name: sn.Name
    ) -> Optional[so.Object]:
        return self.inner.get_by_name(name)

    def get_by_globalname[T: so.Object](
        self, cls: type[T], name: sn.Name
    ) -> Optional[T]:
        return self.inner.get_by_global_name(cls, name)

    def get_by_shortname[T: so.Object](
        self, cls: type[T], name: sn.Name
    ) -> Optional[tuple[T, ...]]:
        return self.inner.get_by_short_name(cls, name)

    def get_obj_data_raw(self, obj: so.Object) -> Optional[tuple[Any, ...]]:
        return self.inner.get_data_raw(obj)

    def get_obj_field_raw(
        self, obj: so.Object, field_index: int
    ) -> Optional[Any]:
        return self.inner.get_field_raw(obj, field_index)

    def _get_object_ids(self) -> Iterable[uuid.UUID]:
        return self.inner._get_object_ids()

    def _get_global_name_ids(
        self,
    ) -> Iterable[tuple[type[so.Object], uuid.UUID]]:
        return self.inner._get_global_name_ids()

    def get_referrers(
        self,
        scls: so.Object,
        *,
        scls_type: Optional[type[so.Object_T]] = None,
        field_name: Optional[str] = None,
    ) -> frozenset[so.Object_T]:
        return self.inner.get_referrers(  # type: ignore
            scls, scls_type, field_name
        )

    def get_referrers_ex(
        self,
        scls: so.Object,
        *,
        scls_type: Optional[type[so.Object_T]] = None,
    ) -> dict[
        tuple[type[so.Object_T], str],
        frozenset[so.Object_T],
    ]:
        return self.inner.get_referrers_ex(scls, scls_type)  # type: ignore

    def add(
        self, id: uuid.UUID, sclass: type[so.Object], data: tuple[Any]
    ) -> RustSchema:
        # print('add_raw', sclass, data)
        return RustSchema(self.inner.add(id, sclass, data))

    def delete(self, obj: so.Object) -> RustSchema:
        return RustSchema(self.inner.delete(obj))

    def delist(self, name: sn.Name) -> RustSchema:
        return RustSchema(self.inner.delist(name))

    def set_obj_field(
        self,
        obj: so.Object,
        fieldname: str,
        value: Any,
    ) -> RustSchema:
        # print('set_obj_field', scls, fieldname, value)
        return RustSchema(self.inner.set_field(obj, fieldname, value))

    def unset_obj_field(self, obj: so.Object, fieldname: str) -> RustSchema:
        return RustSchema(self.inner.unset_field(obj, fieldname))

    def update_obj(
        self,
        obj: so.Object,
        updates: Mapping[str, Any],
    ) -> RustSchema:
        if not updates:
            return self

        # print('update_obj', obj, updates)
        return RustSchema(self.inner.set_fields(obj, updates))


EMPTY_SCHEMA: Schema = RustSchema.empty()
