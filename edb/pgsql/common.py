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

import binascii
import functools
import hashlib
import base64
import re
from typing import Literal, Optional, overload
import uuid

from edb import buildmeta
from edb.common import typeutils
from edb.common import uuidgen
from edb.schema import casts as s_casts
from edb.schema import constraints as s_constr
from edb.schema import defines as s_def
from edb.schema import functions as s_func
from edb.schema import indexes as s_indexes
from edb.schema import name as s_name
from edb.schema import objects as so
from edb.schema import objtypes as s_objtypes
from edb.schema import operators as s_opers
from edb.schema import pointers as s_pointers
from edb.schema import scalars as s_scalars
from edb.schema import types as s_types
from edb.schema import schema as s_schema

from edb.pgsql import ast as pgast

from . import keywords as pg_keywords


# This is a postgres limitation.
# Note that this can be overridden in custom builds.
# https://www.postgresql.org/docs/current/datatype-enum.html
MAX_ENUM_LABEL_LENGTH = 63


def quote_e_literal(string: str) -> str:
    def escape_sq(s):
        split = re.split(r"(\n|\\\\|\\')", s)

        if len(split) == 1:
            return s.replace(r"'", r"\'")

        return ''.join((r if i % 2 else r.replace(r"'", r"\'"))
                       for i, r in enumerate(split))

    return "E'" + escape_sq(string) + "'"


def quote_literal(string: str) -> str:
    return "'" + string.replace("'", "''") + "'"


def _quote_ident(string: str) -> str:
    return '"' + string.replace('"', '""') + '"'


def quote_ident(ident: str | pgast.Star, *, force=False, column=False) -> str:
    if isinstance(ident, pgast.Star):
        return "*"
    return (
        _quote_ident(ident)
        if needs_quoting(ident, column=column) or force else ident
    )


def quote_col(ident: str | pgast.Star) -> str:
    return quote_ident(ident, column=True)


def quote_bytea_literal(data: bytes) -> str:
    """Return valid SQL representation of a bytes value."""

    if data:
        b = binascii.b2a_hex(data).decode('ascii')
        return f"'\\x{b}'::bytea"
    else:
        return "''::bytea"


def needs_quoting(string: str, column: bool = False) -> bool:
    isalnum = (
        string
        and not string[0].isdecimal()
        and string.replace('_', 'a').isalnum()
    )
    return (
        not isalnum or
        string.lower() in pg_keywords.by_type[
            pg_keywords.RESERVED_KEYWORD] or
        string.lower() in pg_keywords.by_type[
            pg_keywords.TYPE_FUNC_NAME_KEYWORD] or
        (column and string.lower() in pg_keywords.by_type[
            pg_keywords.COL_NAME_KEYWORD]) or
        string.lower() != string
    )


def qname(*parts: str | pgast.Star, column: bool = False) -> str:
    assert len(parts) <= 3, parts
    return '.'.join([quote_ident(q, column=column) for q in parts])


def quote_type(type_: tuple[str, ...] | str) -> str:
    if isinstance(type_, tuple):
        first = qname(*type_[:-1]) + '.' if len(type_) > 1 else ''
        last = type_[-1]
    else:
        first = ''
        last = type_

    is_rowtype = last.endswith('%ROWTYPE')
    if is_rowtype:
        last = last[:-8]

    is_array = last.endswith('[]')
    if is_array:
        last = last[:-2]

    param = None
    if '(' in last:
        last, param = last.split('(', 1)
        param = '(' + param

    last = quote_ident(last)

    if is_rowtype:
        last += '%ROWTYPE'

    if param:
        last += param

    if is_array:
        last += '[]'

    return first + last


def get_module_backend_name(module: s_name.Name) -> str:
    # standard modules go into "edgedbstd", user ones into "edgedbpub"
    return "edgedbstd" if module in s_schema.STD_MODULES else "edgedbpub"


def get_unique_random_name() -> str:
    return base64.b64encode(uuidgen.uuid1mc().bytes).rstrip(b'=').decode()


VERSIONED_SCHEMAS = ('edgedb', 'edgedbstd', 'edgedbsql', 'edgedbinstdata')


SCHEMA_SUFFIX: str | None = None


def versioned_schema(s: str) -> str:
    global SCHEMA_SUFFIX
    if SCHEMA_SUFFIX is None:
        version = buildmeta.get_version_dict()['major']
        SCHEMA_SUFFIX = f'_v{version}_{buildmeta.EDGEDB_CATALOG_VERSION:x}'

    # N.B: We don't bother quoting the schema name, so make sure it is
    # lower case and doesn't have weird characters.
    return f'{s}{SCHEMA_SUFFIX}'


def maybe_versioned_schema(
    s: str,
    versioned: bool=True,
) -> str:
    return (
        versioned_schema(s)
        if versioned and s in VERSIONED_SCHEMAS
        else s
    )


def versioned_name(
    s: tuple[str, ...],
) -> tuple[str, ...]:
    if len(s) > 1:
        return (maybe_versioned_schema(s[0]), *s[1:])
    else:
        return s


def maybe_versioned_name(
    s: tuple[str, ...], *, versioned: bool,
) -> tuple[str, ...]:
    return versioned_name(s) if versioned else s


@functools.lru_cache()
def _edgedb_name_to_pg_name(name: str, prefix_length: int = 0) -> str:
    # Note: PostgreSQL doesn't have a sha1 implementation as a
    # built-in function available in all versions, hence we use md5.
    #
    # Although sha1 would be slightly better as it's marginally faster than
    # md5 (and it doesn't matter which function is better cryptographically
    # in this case.)
    hashed = base64.b64encode(
        hashlib.md5(name.encode(), usedforsecurity=False).digest()
    ).decode().rstrip('=')

    return (
        name[:prefix_length] +
        hashed +
        ':' +
        name[-(s_def.MAX_NAME_LENGTH - prefix_length - 1 - len(hashed)):]
    )


def edgedb_name_to_pg_name(name: str, prefix_length: int = 0) -> str:
    """Convert Gel name to a valid PostgresSQL column name.

    PostgreSQL has a limit of 63 characters for column names.

    @param name: Gel name to convert
    @return: PostgreSQL column name
    """
    if not (0 <= prefix_length < s_def.MAX_NAME_LENGTH):
        raise ValueError('supplied name is too long '
                         'to be kept in original form')

    name = str(name)
    if len(name) <= s_def.MAX_NAME_LENGTH - prefix_length:
        return name

    return _edgedb_name_to_pg_name(name, prefix_length)


def convert_name(
    name: s_name.QualName, suffix='', catenate=True,
    *,
    versioned=True,
):
    schema = get_module_backend_name(name.get_module_name())
    if suffix:
        sname = f'{name.name}_{suffix}'
    else:
        sname = name.name

    dbname = edgedb_name_to_pg_name(sname)

    if versioned:
        schema = maybe_versioned_schema(schema)

    if catenate:
        return qname(schema, dbname)
    else:
        return schema, dbname


def get_database_backend_name(db_name: str, *, tenant_id: str) -> str:
    return f'{tenant_id}_{db_name}'


def get_role_backend_name(role_name: str, *, tenant_id: str) -> str:
    return f'{tenant_id}_{role_name}'


def update_aspect(name, aspect):
    """Update the aspect on a non catenated name.

    It also needs to be from an object that uses ids for names"""
    suffix = get_aspect_suffix(aspect)
    stripped = name[1].rsplit("_", 1)[0]
    if suffix:
        return (name[0], f'{stripped}_{suffix}')
    else:
        return (name[0], stripped)


def get_scalar_backend_name(
    id, module_name, catenate=True, *, versioned=True, aspect=None
):
    if aspect is None:
        aspect = 'domain'
    if aspect not in (
        "domain",
        "sequence",
        "enum",
        "enum-cast-into-str",
        "enum-cast-from-str",
        "source-del-imm-otl-f",
        "source-del-imm-otl-t",
    ):
        raise ValueError(
            f'unexpected aspect for scalar backend name: {aspect!r}')
    name = s_name.QualName(module=module_name, name=str(id))

    # XXX: TRAMPOLINE: VERSIONING???
    if aspect.startswith("enum-cast-"):
        suffix = "_into_str" if aspect == "enum-cast-into-str" else "_from_str"
        name = s_name.QualName(name.module, name.name + suffix)
        return get_cast_backend_name(
            name, catenate, versioned=versioned, aspect="function")

    return convert_name(name, aspect, catenate, versioned=False)


def get_aspect_suffix(aspect):
    if aspect == 'table':
        return ''
    elif aspect == 'inhview':
        return 't'
    else:
        return aspect


def is_inhview_name(name: str) -> bool:
    return name.endswith('_t')


def get_objtype_backend_name(
    id: uuid.UUID,
    module_name: str,
    *,
    catenate: bool = True,
    versioned: bool = False,
    aspect: Optional[str] = None,
):
    if aspect is None:
        aspect = 'table'
    if (
        aspect not in {'table', 'inhview', 'dummy'}
        and not re.match(
            r'(source|target)-del-(def|imm)-(inl|otl)-(f|t)', aspect)
        and not aspect.startswith("ext")
    ):
        raise ValueError(
            f'unexpected aspect for object type backend name: {aspect!r}')

    name = s_name.QualName(module=module_name, name=str(id))

    suffix = get_aspect_suffix(aspect)
    return convert_name(
        name, suffix=suffix, catenate=catenate, versioned=versioned)


def get_pointer_backend_name(
    id, module_name, *, catenate=False, aspect=None, versioned=True
):
    if aspect is None:
        aspect = 'table'

    if aspect not in ('table', 'index', 'inhview', 'dummy'):
        raise ValueError(
            f'unexpected aspect for pointer backend name: {aspect!r}')

    name = s_name.QualName(module=module_name, name=str(id))

    suffix = get_aspect_suffix(aspect)
    return convert_name(
        name, suffix=suffix, catenate=catenate, versioned=versioned
    )


operator_map = {
    s_name.name_from_string('std::AND'): 'AND',
    s_name.name_from_string('std::OR'): 'OR',
    s_name.name_from_string('std::NOT'): 'NOT',
    s_name.name_from_string('std::?='): 'IS NOT DISTINCT FROM',
    s_name.name_from_string('std::?!='): 'IS DISTINCT FROM',
    s_name.name_from_string('std::LIKE'): 'LIKE',
    s_name.name_from_string('std::ILIKE'): 'ILIKE',
    s_name.name_from_string('std::NOT LIKE'): 'NOT LIKE',
    s_name.name_from_string('std::NOT ILIKE'): 'NOT ILIKE',
}


def get_operator_backend_name(
    name, catenate=False, *, versioned=True, aspect=None
):
    if aspect is None:
        aspect = 'operator'

    if aspect == 'function':
        return convert_name(name, 'f', catenate=catenate, versioned=versioned)
    elif aspect != 'operator':
        raise ValueError(
            f'unexpected aspect for operator backend name: {aspect!r}')

    oper_name = operator_map.get(name)
    if oper_name is None:
        oper_name = name.name
        if re.search(r'[a-zA-Z]', oper_name):
            raise ValueError(
                f'cannot represent operator {oper_name} in Postgres')

        oper_name = f'`{oper_name}`'
        schema = 'edgedb'
    else:
        schema = ''

    if catenate:
        return qname(schema, oper_name)
    else:
        return schema, oper_name


def get_cast_backend_name(
    fullname: s_name.QualName, catenate=False, *, versioned=True, aspect=None
):
    if aspect == "function":
        return convert_name(
            fullname, "f", catenate=catenate, versioned=versioned)
    else:
        raise ValueError(
            f'unexpected aspect for cast backend name: {aspect!r}')


def get_function_backend_name(
    name, backend_name, catenate=False, versioned=True,
):
    real_name = backend_name or name.name

    fullname = s_name.QualName(module=name.module, name=real_name)
    schema, func_name = convert_name(
        fullname, catenate=False, versioned=versioned)
    if catenate:
        return qname(schema, func_name)
    else:
        return schema, func_name


def get_constraint_backend_name(id, module_name, catenate=True, *, aspect=None):
    if aspect not in ('trigproc', 'index'):
        raise ValueError(
            f'unexpected aspect for constraint backend name: {aspect!r}')

    sname = str(id)
    if aspect == 'index':
        aspect = None
        sname = get_constraint_raw_name(id)
    name = s_name.QualName(module=module_name, name=sname)
    return convert_name(name, aspect, catenate)


def get_constraint_raw_name(id):
    return f'{id};schemaconstr'


def get_index_backend_name(id, module_name, catenate=True, *, aspect=None):
    if aspect is None:
        aspect = 'index'
    name = s_name.QualName(module=module_name, name=str(id))
    return convert_name(name, aspect, catenate)


def get_index_table_backend_name(
    index: s_indexes.Index,
    schema: s_schema.Schema,
    *,
    aspect: Optional[str] = None,
) -> tuple[str, str]:
    subject = index.get_subject(schema)
    assert isinstance(subject, s_types.Type)
    return get_backend_name(schema, subject, aspect=aspect, catenate=False)


def get_tuple_backend_name(
    id, catenate=True, *, aspect=None
) -> str | tuple[str, str]:

    name = s_name.QualName(module='edgedb', name=f'{id}_t')
    return convert_name(name, aspect, catenate)


@overload
def get_backend_name(
    schema: s_schema.Schema,
    obj: so.Object,
    catenate: Literal[True]=True,
    *,
    versioned: bool=True,
    aspect: Optional[str]=None
) -> str:
    ...


@overload
def get_backend_name(
    schema: s_schema.Schema,
    obj: so.Object,
    catenate: Literal[False],
    *,
    versioned: bool=True,
    aspect: Optional[str]=None
) -> tuple[str, str]:
    ...


def get_backend_name(
    schema: s_schema.Schema,
    obj: so.Object,
    catenate: bool=True,
    *,
    aspect: Optional[str]=None,
    versioned: bool=True,
) -> str | tuple[str, str]:
    name: s_name.QualName | s_name.Name
    if isinstance(obj, s_objtypes.ObjectType):
        name = obj.get_name(schema)
        return get_objtype_backend_name(
            obj.id, name.module, catenate=catenate,
            aspect=aspect, versioned=versioned,
        )

    elif isinstance(obj, s_pointers.Pointer):
        name = obj.get_name(schema)
        return get_pointer_backend_name(obj.id, name.module, catenate=catenate,
                                        versioned=versioned,
                                        aspect=aspect)

    elif isinstance(obj, s_scalars.ScalarType):
        name = obj.get_name(schema)
        return get_scalar_backend_name(obj.id, name.module, catenate=catenate,
                                       versioned=versioned,
                                       aspect=aspect)

    elif isinstance(obj, s_opers.Operator):
        name = obj.get_shortname(schema)
        return get_operator_backend_name(
            name, catenate, versioned=versioned, aspect=aspect)

    elif isinstance(obj, s_casts.Cast):
        name = obj.get_name(schema)
        return get_cast_backend_name(
            name, catenate, versioned=versioned, aspect=aspect)

    elif isinstance(obj, s_func.Function):
        name = obj.get_shortname(schema)
        backend_name = obj.get_backend_name(schema)
        return get_function_backend_name(
            name, backend_name, catenate, versioned=versioned)

    elif isinstance(obj, s_constr.Constraint):
        name = obj.get_name(schema)
        return get_constraint_backend_name(
            obj.id, name.module, catenate, aspect=aspect)

    elif isinstance(obj, s_indexes.Index):
        name = obj.get_name(schema)
        return get_index_backend_name(
            obj.id, name.module, catenate, aspect=aspect)

    elif isinstance(obj, s_types.Tuple):
        # XXX: TRAMPOLINE: VERSIONED?
        return get_tuple_backend_name(
            obj.id, catenate, aspect=aspect)

    else:
        raise ValueError(f'cannot determine backend name for {obj!r}')


def get_object_from_backend_name(schema, metaclass, name, *, aspect=None):

    if issubclass(metaclass, s_objtypes.ObjectType):
        table_name = name[1]
        obj_id = uuidgen.UUID(table_name)
        return schema.get_by_id(obj_id)

    elif issubclass(metaclass, s_pointers.Pointer):
        obj_id = uuidgen.UUID(name)
        return schema.get_by_id(obj_id)

    else:
        raise ValueError(
            f'cannot determine object from backend name for {metaclass!r}')


def get_sql_value_function_op(op: pgast.SQLValueFunctionOP) -> str:
    from edb.pgsql.ast import SQLValueFunctionOP as OP

    NAMES = {
        OP.CURRENT_DATE: "current_date",
        OP.CURRENT_TIME: "current_time",
        OP.CURRENT_TIME_N: "current_time",
        OP.CURRENT_TIMESTAMP: "current_timestamp",
        OP.CURRENT_TIMESTAMP_N: "current_timestamp",
        OP.LOCALTIME: "localtime",
        OP.LOCALTIME_N: "localtime",
        OP.LOCALTIMESTAMP: "localtimestamp",
        OP.LOCALTIMESTAMP_N: "localtimestamp",
        OP.CURRENT_ROLE: "current_role",
        OP.CURRENT_USER: "current_user",
        OP.USER: "user",
        OP.SESSION_USER: "session_user",
        OP.CURRENT_CATALOG: "current_catalog",
        OP.CURRENT_SCHEMA: "current_schema",
    }
    return NAMES[op]


# Settings that are enums or bools and should not be quoted.
# Can be retrived from PostgreSQL with:
#   SELECt name FROM pg_catalog.pg_settings WHERE vartype IN ('enum', 'bool');
ENUM_SETTINGS = {
    'allow_alter_system',
    'allow_in_place_tablespaces',
    'allow_system_table_mods',
    'archive_mode',
    'array_nulls',
    'autovacuum',
    'backslash_quote',
    'bytea_output',
    'check_function_bodies',
    'client_min_messages',
    'compute_query_id',
    'constraint_exclusion',
    'data_checksums',
    'data_sync_retry',
    'debug_assertions',
    'debug_logical_replication_streaming',
    'debug_parallel_query',
    'debug_pretty_print',
    'debug_print_parse',
    'debug_print_plan',
    'debug_print_rewritten',
    'default_toast_compression',
    'default_transaction_deferrable',
    'default_transaction_isolation',
    'default_transaction_read_only',
    'dynamic_shared_memory_type',
    'edb_stat_statements.save',
    'edb_stat_statements.track',
    'edb_stat_statements.track_planning',
    'edb_stat_statements.track_utility',
    'enable_async_append',
    'enable_bitmapscan',
    'enable_gathermerge',
    'enable_group_by_reordering',
    'enable_hashagg',
    'enable_hashjoin',
    'enable_incremental_sort',
    'enable_indexonlyscan',
    'enable_indexscan',
    'enable_material',
    'enable_memoize',
    'enable_mergejoin',
    'enable_nestloop',
    'enable_parallel_append',
    'enable_parallel_hash',
    'enable_partition_pruning',
    'enable_partitionwise_aggregate',
    'enable_partitionwise_join',
    'enable_presorted_aggregate',
    'enable_seqscan',
    'enable_sort',
    'enable_tidscan',
    'escape_string_warning',
    'event_triggers',
    'exit_on_error',
    'fsync',
    'full_page_writes',
    'geqo',
    'gss_accept_delegation',
    'hot_standby',
    'hot_standby_feedback',
    'huge_pages',
    'huge_pages_status',
    'icu_validation_level',
    'ignore_checksum_failure',
    'ignore_invalid_pages',
    'ignore_system_indexes',
    'in_hot_standby',
    'integer_datetimes',
    'intervalstyle',
    'jit',
    'jit_debugging_support',
    'jit_dump_bitcode',
    'jit_expressions',
    'jit_profiling_support',
    'jit_tuple_deforming',
    'krb_caseins_users',
    'lo_compat_privileges',
    'log_checkpoints',
    'log_connections',
    'log_disconnections',
    'log_duration',
    'log_error_verbosity',
    'log_executor_stats',
    'log_hostname',
    'log_lock_waits',
    'log_min_error_statement',
    'log_min_messages',
    'log_parser_stats',
    'log_planner_stats',
    'log_recovery_conflict_waits',
    'log_replication_commands',
    'log_statement',
    'log_statement_stats',
    'log_truncate_on_rotation',
    'logging_collector',
    'parallel_leader_participation',
    'password_encryption',
    'plan_cache_mode',
    'quote_all_identifiers',
    'recovery_init_sync_method',
    'recovery_prefetch',
    'recovery_target_action',
    'recovery_target_inclusive',
    'remove_temp_files_after_crash',
    'restart_after_crash',
    'row_security',
    'send_abort_for_crash',
    'send_abort_for_kill',
    'session_replication_role',
    'shared_memory_type',
    'ssl',
    'ssl_max_protocol_version',
    'ssl_min_protocol_version',
    'ssl_passphrase_command_supports_reload',
    'ssl_prefer_server_ciphers',
    'standard_conforming_strings',
    'stats_fetch_consistency',
    'summarize_wal',
    'sync_replication_slots',
    'synchronize_seqscans',
    'synchronous_commit',
    'syslog_facility',
    'syslog_sequence_numbers',
    'syslog_split_messages',
    'trace_connection_negotiation',
    'trace_notify',
    'trace_sort',
    'track_activities',
    'track_commit_timestamp',
    'track_counts',
    'track_functions',
    'track_io_timing',
    'track_wal_io_timing',
    'transaction_deferrable',
    'transaction_isolation',
    'transaction_read_only',
    'transform_null_equals',
    'update_process_title',
    'wal_compression',
    'wal_init_zero',
    'wal_level',
    'wal_log_hints',
    'wal_receiver_create_temp_slot',
    'wal_recycle',
    'wal_sync_method',
    'xmlbinary',
    'xmloption',
    'zero_damaged_pages',
}


def setting_to_sql(name, setting):
    is_enum = name.lower() in ENUM_SETTINGS

    assert typeutils.is_container(setting)
    return ', '.join(setting_val_to_sql(v, is_enum) for v in setting)


def setting_val_to_sql(val: str | int | float, is_enum: bool):
    if isinstance(val, str):
        if is_enum:
            # special case: no quoting
            return val
        # quote as identifier
        return quote_ident(val)
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        return str(val)
    raise NotImplementedError('cannot convert setting to SQL: ', val)
