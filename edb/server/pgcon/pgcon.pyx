#
# This source file is part of the EdgeDB open source project.
#
# Copyright 2016-present MagicStack Inc. and the EdgeDB authors.
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

from typing import (
    Any,
    Callable,
    Dict,
    Optional,
)

import asyncio
import contextlib
import decimal
import codecs
import hashlib
import json
import logging
import os.path
import sys
import struct
import textwrap
import time

cimport cython
cimport cpython

from . cimport cpythonx

from libc.stdint cimport int8_t, uint8_t, int16_t, uint16_t, \
                         int32_t, uint32_t, int64_t, uint64_t, \
                         UINT32_MAX

from edb import errors
from edb.edgeql import qltypes
from edb.pgsql import common as pgcommon
from edb.pgsql.common import quote_literal as pg_ql
from edb.pgsql import codegen as pg_codegen

from edb.server.pgproto cimport hton
from edb.server.pgproto cimport pgproto
from edb.server.pgproto.pgproto cimport (
    WriteBuffer,
    ReadBuffer,

    FRBuffer,
    frb_init,
    frb_read,
    frb_get_len,
    frb_slice_from,
)

from edb.server import compiler
from edb.server.compiler import dbstate
from edb.server import defines
from edb.server.cache cimport stmt_cache
from edb.server.dbview cimport dbview
from edb.server.protocol cimport args_ser
from edb.server.protocol cimport pg_ext
from edb.server import metrics

from edb.server.protocol cimport frontend

from edb.common import debug

from . import errors as pgerror

DEF DATA_BUFFER_SIZE = 100_000
DEF PREP_STMTS_CACHE = 100

DEF COPY_SIGNATURE = b"PGCOPY\n\377\r\n\0"

DEF TEXT_OID = 25

cdef object CARD_NO_RESULT = compiler.Cardinality.NO_RESULT
cdef object FMT_NONE = compiler.OutputFormat.NONE
cdef dict POSTGRES_SHUTDOWN_ERR_CODES = {
    '57P01': 'admin_shutdown',
    '57P02': 'crash_shutdown',
}

cdef object EMPTY_SQL_STATE = b"{}"
cdef WriteBuffer NO_ARGS = args_ser.combine_raw_args()

cdef object logger = logging.getLogger('edb.server')

include "./pgcon_sql.pyx"


@cython.final
cdef class EdegDBCodecContext(pgproto.CodecContext):

    cdef:
        object _codec

    def __cinit__(self):
        self._codec = codecs.lookup('utf-8')

    cpdef get_text_codec(self):
        return self._codec

    cdef is_encoding_utf8(self):
        return True


@cython.final
cdef class PGConnection:

    def __init__(self, dbname):
        self.buffer = ReadBuffer()

        self.loop = asyncio.get_running_loop()
        self.dbname = dbname

        self.connection = None
        self.transport = None
        self.msg_waiter = None

        self.prep_stmts = stmt_cache.StatementsCache(maxsize=PREP_STMTS_CACHE)

        self.connected_fut = self.loop.create_future()
        self.connected = False

        self.waiting_for_sync = 0
        self.xact_status = PQTRANS_UNKNOWN

        self.backend_pid = -1
        self.backend_secret = -1
        self.parameter_status = dict()

        self.last_parse_prep_stmts = []
        self.debug = debug.flags.server_proto

        self.last_indirect_return = None

        self.log_listeners = []

        self.server = None
        self.tenant = None
        self.is_system_db = False
        self.close_requested = False

        self.pinned_by = None

        self.idle = True
        self.cancel_fut = None

        self._is_ssl = False

        # Set to the error the connection has been aborted with
        # by the backend.
        self.aborted_with_error = None

        # Session State Management
        # ------------------------
        # Due to the fact that backend sessions are not pinned to frontend
        # sessions (EdgeQL, SQL, etc.) out of transactions, we need to sync
        # the backend state with the frontend state before executing queries.
        #
        # For performance reasons, we try to avoid syncing the state by
        # remembering the last state we've synced (last_state), and prefer
        # backend connection with the same state as the frontend.
        #
        # Syncing the state is done by resetting the session state as a whole,
        # followed by applying the new state, so that we don't have to track
        # individual config resets. Again for performance reasons, the state
        # sync is usually applied in the same implicit transaction as the
        # actual query in order to avoid extra round trips.
        #
        # Though, there are exceptions when we need to sync the state in a
        # separate transaction by inserting a SYNC message before the actual
        # query. This is because either that the query itself is a START
        # TRANSACTION / non-transactional command and a few other cases (see
        # _parse_execute() below), or the state change affects new transaction
        # creation like changing the `default_transaction_isolation` or its
        # siblings (see `needs_commit_state` parameters). In such cases, we
        # remember the `last_state` immediately after we received the
        # ReadyForQuery message caused by the SYNC above, if there are no
        # errors happened during state sync. Otherwise, we only remember
        # `last_state` after the implicit transaction ends successfully, when
        # we're sure the state is synced permanently.
        #
        # The actual queries may also change the session state. Regardless of
        # how we synced state previously, we always remember the `last_state`
        # after successful executions (also after transactions without errors,
        # implicit or explicit).
        #
        # Finally, resetting an existing session state that was positive in
        # `needs_commit_state` also requires a commit, because the new state
        # may not have `needs_commit_state`. To achieve this, we remember the
        # previous `needs_commit_state` in `state_reset_needs_commit` and
        # always insert a SYNC in the next state sync if it's True. Also, if
        # the actual queries modified those `default_transaction_*` settings,
        # we also need to set `state_reset_needs_commit` to True for the next
        # state sync(reset). See `needs_commit_after_state_sync()` functions
        # in dbview classes (EdgeQL and SQL).
        self.last_state = dbview.DEFAULT_STATE
        self.state_reset_needs_commit = False

        self._sql = PGSQLConnection(self)

    cpdef set_stmt_cache_size(self, int maxsize):
        self.prep_stmts.resize(maxsize)

    @property
    def is_ssl(self):
        return self._is_ssl

    @is_ssl.setter
    def is_ssl(self, value):
        self._is_ssl = value

    def debug_print(self, *args):
        print(
            '::PGCONN::',
            hex(id(self)),
            f'pgpid: {self.backend_pid}',
            *args,
            file=sys.stderr,
        )

    def in_tx(self):
        return (
            self.xact_status == PQTRANS_INTRANS or
            self.xact_status == PQTRANS_INERROR
        )

    def is_cancelling(self):
        return self.cancel_fut is not None

    def start_pg_cancellation(self):
        if self.cancel_fut is not None:
            raise RuntimeError('another cancellation is in progress')
        self.cancel_fut = self.loop.create_future()

    def finish_pg_cancellation(self):
        assert self.cancel_fut is not None
        self.cancel_fut.set_result(True)

    def get_server_parameter_status(self, parameter: str) -> Optional[str]:
        return self.parameter_status.get(parameter)

    def abort(self):
        if not self.transport:
            return
        self.close_requested = True
        self.transport.abort()
        self.transport = None
        self.connected = False
        self.prep_stmts.clear()

    def terminate(self):
        if not self.transport:
            return
        self.close_requested = True
        self.write(WriteBuffer.new_message(b'X').end_message())
        self.transport.close()
        self.transport = None
        self.connected = False
        self.prep_stmts.clear()

        if self.msg_waiter and not self.msg_waiter.done():
            self.msg_waiter.set_exception(ConnectionAbortedError())
            self.msg_waiter = None

    async def close(self):
        self.terminate()

    def set_tenant(self, tenant):
        self.tenant = tenant
        self.server = tenant.server

    def mark_as_system_db(self):
        if self.tenant.get_backend_runtime_params().has_create_database:
            assert defines.EDGEDB_SYSTEM_DB in self.dbname
        self.is_system_db = True

    def add_log_listener(self, cb):
        self.log_listeners.append(cb)

    async def listen_for_sysevent(self):
        try:
            if self.tenant.get_backend_runtime_params().has_create_database:
                assert defines.EDGEDB_SYSTEM_DB in self.dbname
            await self.sql_execute(b'LISTEN __edgedb_sysevent__;')
        except Exception:
            try:
                self.abort()
            finally:
                raise

    async def signal_sysevent(self, event, **kwargs):
        if self.tenant.get_backend_runtime_params().has_create_database:
            assert defines.EDGEDB_SYSTEM_DB in self.dbname
        event = json.dumps({
            'event': event,
            'server_id': self.server._server_id,
            'args': kwargs,
        })
        query = f"""
            SELECT pg_notify(
                '__edgedb_sysevent__',
                {pg_ql(event)}
            )
        """.encode()
        await self.sql_execute(query)

    async def sync(self):
        if self.waiting_for_sync:
            raise RuntimeError('a "sync" has already been requested')

        self.before_command()
        try:
            self.waiting_for_sync += 1
            self.write(_SYNC_MESSAGE)

            while True:
                if not self.buffer.take_message():
                    await self.wait_for_message()
                mtype = self.buffer.get_message_type()

                if mtype == b'Z':
                    self.parse_sync_message()
                    return
                else:
                    self.fallthrough()
        finally:
            await self.after_command()

    async def wait_for_sync(self):
        error = None
        try:
            while True:
                if not self.buffer.take_message():
                    await self.wait_for_message()
                mtype = self.buffer.get_message_type()
                if mtype == b'Z':
                    return self.parse_sync_message()
                elif mtype == b'E':
                    # ErrorResponse
                    er_cls, fields = self.parse_error_message()
                    error = er_cls(fields=fields)
                else:
                    if not self.parse_notification():
                        if PG_DEBUG or self.debug:
                            self.debug_print(f'PGCon.wait_for_sync: discarding '
                                            f'{chr(mtype)!r} message')
                        self.buffer.discard_message()
        finally:
            if error is not None:
                # Postgres might send an ErrorResponse if, e.g.
                # in implicit transaction fails to commit due to
                # serialization conflicts.
                raise error

    cdef inline str get_tenant_label(self):
        if self.tenant is None:
            return "system"
        else:
            return self.tenant.get_instance_name()

    cdef bint before_prepare(
        self,
        bytes stmt_name,
        int dbver,
        WriteBuffer outbuf,
    ):
        cdef bint parse = 1

        while self.prep_stmts.needs_cleanup():
            stmt_name_to_clean, _ = self.prep_stmts.cleanup_one()
            if self.debug:
                self.debug_print(f"discarding ps {stmt_name_to_clean!r}")
            outbuf.write_buffer(
                self.make_clean_stmt_message(stmt_name_to_clean))

        if stmt_name in self.prep_stmts:
            if self.prep_stmts[stmt_name] == dbver:
                parse = 0
            else:
                if self.debug:
                    self.debug_print(f"discarding ps {stmt_name!r}")
                outbuf.write_buffer(
                    self.make_clean_stmt_message(stmt_name))
                del self.prep_stmts[stmt_name]

        return parse

    cdef write_sync(self, WriteBuffer outbuf):
        outbuf.write_bytes(_SYNC_MESSAGE)
        self.waiting_for_sync += 1

    cdef send_sync(self):
        self.write(_SYNC_MESSAGE)
        self.waiting_for_sync += 1

    def _build_apply_state_req(self, bytes serstate, WriteBuffer out):
        cdef:
            WriteBuffer buf

        if self.debug:
            self.debug_print("Syncing state: ", serstate)

        buf = WriteBuffer.new_message(b'B')
        buf.write_bytestring(b'')  # portal name
        buf.write_bytestring(b'_clear_state')  # statement name
        buf.write_int16(0)  # number of format codes
        buf.write_int16(0)  # number of parameters
        buf.write_int16(0)  # number of result columns
        out.write_buffer(buf.end_message())

        buf = WriteBuffer.new_message(b'E')
        buf.write_bytestring(b'')  # portal name
        buf.write_int32(0)  # limit: 0 - return all rows
        out.write_buffer(buf.end_message())

        buf = WriteBuffer.new_message(b'B')
        buf.write_bytestring(b'')  # portal name
        buf.write_bytestring(b'_reset_session_config')  # statement name
        buf.write_int16(0)  # number of format codes
        buf.write_int16(0)  # number of parameters
        buf.write_int16(0)  # number of result columns
        out.write_buffer(buf.end_message())

        buf = WriteBuffer.new_message(b'E')
        buf.write_bytestring(b'')  # portal name
        buf.write_int32(0)  # limit: 0 - return all rows
        out.write_buffer(buf.end_message())

        if serstate is not None:
            buf = WriteBuffer.new_message(b'B')
            buf.write_bytestring(b'')  # portal name
            buf.write_bytestring(b'_apply_state')  # statement name
            buf.write_int16(1)  # number of format codes
            buf.write_int16(1)  # binary
            buf.write_int16(1)  # number of parameters
            buf.write_int32(len(serstate) + 1)
            buf.write_byte(1)  # jsonb format version
            buf.write_bytes(serstate)
            buf.write_int16(0)  # number of result columns
            out.write_buffer(buf.end_message())

            buf = WriteBuffer.new_message(b'E')
            buf.write_bytestring(b'')  # portal name
            buf.write_int32(0)  # limit: 0 - return all rows
            out.write_buffer(buf.end_message())

    def _build_apply_sql_state_req(self, bytes state, WriteBuffer out):
        cdef:
            WriteBuffer buf

        buf = WriteBuffer.new_message(b'B')
        buf.write_bytestring(b'')  # portal name
        buf.write_bytestring(b'_clear_state')  # statement name
        buf.write_int16(0)  # number of format codes
        buf.write_int16(0)  # number of parameters
        buf.write_int16(0)  # number of result columns
        out.write_buffer(buf.end_message())

        buf = WriteBuffer.new_message(b'E')
        buf.write_bytestring(b'')  # portal name
        buf.write_int32(0)  # limit: 0 - return all rows
        out.write_buffer(buf.end_message())

        buf = WriteBuffer.new_message(b'B')
        buf.write_bytestring(b'')  # portal name
        buf.write_bytestring(b'_reset_session_config')  # statement name
        buf.write_int16(0)  # number of format codes
        buf.write_int16(0)  # number of parameters
        buf.write_int16(0)  # number of result columns
        out.write_buffer(buf.end_message())

        buf = WriteBuffer.new_message(b'E')
        buf.write_bytestring(b'')  # portal name
        buf.write_int32(0)  # limit: 0 - return all rows
        out.write_buffer(buf.end_message())

        if state != EMPTY_SQL_STATE:
            buf = WriteBuffer.new_message(b'B')
            buf.write_bytestring(b'')  # portal name
            buf.write_bytestring(b'_apply_sql_state')  # statement name
            buf.write_int16(1)  # number of format codes
            buf.write_int16(1)  # binary
            buf.write_int16(1)  # number of parameters
            buf.write_int32(len(state) + 1)
            buf.write_byte(1)  # jsonb format version
            buf.write_bytes(state)
            buf.write_int16(0)  # number of result columns
            out.write_buffer(buf.end_message())

            buf = WriteBuffer.new_message(b'E')
            buf.write_bytestring(b'')  # portal name
            buf.write_int32(0)  # limit: 0 - return all rows
            out.write_buffer(buf.end_message())

    async def _parse_apply_state_resp(self, int expected_completed):
        cdef:
            int num_completed = 0

        while True:
            if not self.buffer.take_message():
                await self.wait_for_message()
            mtype = self.buffer.get_message_type()

            if mtype == b'2' or mtype == b'D':
                # BindComplete or Data
                self.buffer.discard_message()

            elif mtype == b'E':
                er_cls, er_fields = self.parse_error_message()
                raise er_cls(fields=er_fields)

            elif mtype == b'C':
                self.buffer.discard_message()
                num_completed += 1
                if num_completed == expected_completed:
                    return
            else:
                self.fallthrough()

    @contextlib.asynccontextmanager
    async def parse_execute_script_context(self):
        self.before_command()
        started_at = time.monotonic()
        try:
            try:
                yield
            finally:
                while self.waiting_for_sync:
                    await self.wait_for_sync()
        finally:
            metrics.backend_query_duration.observe(
                time.monotonic() - started_at, self.get_tenant_label()
            )
            await self.after_command()

    cdef send_query_unit_group(
        self, object query_unit_group, bint sync,
        object bind_datas, bytes state,
        ssize_t start, ssize_t end, int dbver, object parse_array,
        object query_prefix,
        bint needs_commit_state,
    ):
        # parse_array is an array of booleans for output with the same size as
        # the query_unit_group, indicating if each unit is freshly parsed
        cdef:
            WriteBuffer out
            WriteBuffer buf
            WriteBuffer bind_data
            bytes stmt_name
            ssize_t idx = start
            bytes sql
            tuple sqls

        out = WriteBuffer.new()
        parsed = set()

        if state is not None and start == 0:
            self._build_apply_state_req(state, out)
            if needs_commit_state or self.state_reset_needs_commit:
                self.write_sync(out)

        # Build the parse_array first, closing statements if needed before
        # actually executing any command that may fail, in order to ensure
        # self.prep_stmts is always in sync with the actual open statements
        for query_unit in query_unit_group.units[start:end]:
            if query_unit.system_config:
                raise RuntimeError(
                    "CONFIGURE INSTANCE command is not allowed in scripts"
                )
            stmt_name = query_unit.sql_hash
            if stmt_name:
                # The same EdgeQL query may show up twice in the same script.
                # We just need to know and skip if we've already parsed the
                # same query within current send batch, because self.prep_stmts
                # will be updated before the next batch, with maybe a different
                # dbver after DDL.
                if stmt_name not in parsed and self.before_prepare(
                    stmt_name, dbver, out
                ):
                    parse_array[idx] = True
                    parsed.add(stmt_name)
            idx += 1
        idx = start

        for query_unit, bind_data in zip(
            query_unit_group.units[start:end], bind_datas):
            stmt_name = query_unit.sql_hash
            sql = query_unit.sql
            if query_prefix:
                sql = query_prefix + sql
            if stmt_name:
                if parse_array[idx]:
                    buf = WriteBuffer.new_message(b'P')
                    buf.write_bytestring(stmt_name)
                    buf.write_bytestring(sql)
                    buf.write_int16(0)
                    out.write_buffer(buf.end_message())
                    metrics.query_size.observe(
                        len(sql),
                        self.get_tenant_label(),
                        'compiled',
                    )

                buf = WriteBuffer.new_message(b'B')
                buf.write_bytestring(b'')  # portal name
                buf.write_bytestring(stmt_name)
                buf.write_buffer(bind_data)
                out.write_buffer(buf.end_message())

                buf = WriteBuffer.new_message(b'E')
                buf.write_bytestring(b'')  # portal name
                buf.write_int32(0)  # limit: 0 - return all rows
                out.write_buffer(buf.end_message())

            else:
                buf = WriteBuffer.new_message(b'P')
                buf.write_bytestring(b'')  # statement name
                buf.write_bytestring(sql)
                buf.write_int16(0)
                out.write_buffer(buf.end_message())
                metrics.query_size.observe(
                    len(sql), self.get_tenant_label(), 'compiled'
                )

                buf = WriteBuffer.new_message(b'B')
                buf.write_bytestring(b'')  # portal name
                buf.write_bytestring(b'')  # statement name
                buf.write_buffer(bind_data)
                out.write_buffer(buf.end_message())

                buf = WriteBuffer.new_message(b'E')
                buf.write_bytestring(b'')  # portal name
                buf.write_int32(0)  # limit: 0 - return all rows
                out.write_buffer(buf.end_message())

            idx += 1

        if sync:
            self.write_sync(out)
        else:
            out.write_bytes(FLUSH_MESSAGE)

        self.write(out)

    async def force_error(self):
        self.before_command()

        # Send a bogus parse that will cause an error to be generated
        out = WriteBuffer.new()
        buf = WriteBuffer.new_message(b'P')
        buf.write_bytestring(b'')
        buf.write_bytestring(b'<INTERNAL ERROR IN GEL PGCON>')
        buf.write_int16(0)

        # Then do a sync to get everything executed and lined back up
        out.write_buffer(buf.end_message())
        self.write_sync(out)

        self.write(out)

        try:
            await self.wait_for_sync()
        except pgerror.BackendError as e:
            pass
        else:
            raise RuntimeError("Didn't get expected error!")
        finally:
            await self.after_command()

    async def wait_for_state_resp(
        self, bytes state, bint state_sync, bint needs_commit_state
    ):
        if state_sync:
            try:
                await self._parse_apply_state_resp(2 if state is None else 3)
            finally:
                await self.wait_for_sync()
            self.last_state = state
            self.state_reset_needs_commit = needs_commit_state
        else:
            await self._parse_apply_state_resp(2 if state is None else 3)

    async def wait_for_command(
        self,
        object query_unit,
        bint parse,
        int dbver,
        *,
        bint ignore_data,
        frontend.AbstractFrontendConnection fe_conn = None,
    ):
        cdef WriteBuffer buf = None

        result = None
        while True:
            if not self.buffer.take_message():
                await self.wait_for_message()
            mtype = self.buffer.get_message_type()

            try:
                if mtype == b'D':
                    # DataRow
                    if ignore_data:
                        self.buffer.discard_message()
                    elif fe_conn is None:
                        ncol = self.buffer.read_int16()
                        row = []
                        for i in range(ncol):
                            coll = self.buffer.read_int32()
                            if coll == -1:
                                row.append(None)
                            else:
                                row.append(self.buffer.read_bytes(coll))
                        if result is None:
                            result = []
                        result.append(row)
                    else:
                        if buf is None:
                            buf = WriteBuffer.new()

                        self.buffer.redirect_messages(buf, b'D', 0)
                        if buf.len() >= DATA_BUFFER_SIZE:
                            fe_conn.write(buf)
                            buf = None

                elif mtype == b'C':  ## result
                    # CommandComplete
                    self.buffer.discard_message()
                    if buf is not None:
                        fe_conn.write(buf)
                        buf = None
                    return result

                elif mtype == b'1':
                    # ParseComplete
                    self.buffer.discard_message()
                    if parse:
                        self.prep_stmts[query_unit.sql_hash] = dbver

                elif mtype == b'E':  ## result
                    # ErrorResponse
                    er_cls, er_fields = self.parse_error_message()
                    raise er_cls(fields=er_fields)

                elif mtype == b'n':
                    # NoData
                    self.buffer.discard_message()

                elif mtype == b's':  ## result
                    # PortalSuspended
                    self.buffer.discard_message()
                    return result

                elif mtype == b'2':
                    # BindComplete
                    self.buffer.discard_message()

                elif mtype == b'3':
                    # CloseComplete
                    self.buffer.discard_message()

                elif mtype == b'I':  ## result
                    # EmptyQueryResponse
                    self.buffer.discard_message()

                else:
                    self.fallthrough()

            finally:
                self.buffer.finish_message()

    async def _describe(
        self,
        query: bytes,
        param_type_oids: Optional[list[int]],
    ):
        cdef:
            WriteBuffer out

        out = WriteBuffer.new()

        buf = WriteBuffer.new_message(b"P")  # Parse
        buf.write_bytestring(b"")
        buf.write_bytestring(query)
        if param_type_oids:
            buf.write_int16(len(param_type_oids))
            for oid in param_type_oids:
                buf.write_int32(<int32_t>oid)
        else:
            buf.write_int16(0)
        out.write_buffer(buf.end_message())

        buf = WriteBuffer.new_message(b"D")  # Describe
        buf.write_byte(b"S")
        buf.write_bytestring(b"")
        out.write_buffer(buf.end_message())

        out.write_bytes(FLUSH_MESSAGE)

        self.write(out)

        param_desc = None
        result_desc = None

        try:
            buf = None
            while True:
                if not self.buffer.take_message():
                    await self.wait_for_message()
                mtype = self.buffer.get_message_type()

                try:
                    if mtype == b'1':
                        # ParseComplete
                        self.buffer.discard_message()

                    elif mtype == b't':
                        # ParameterDescription
                        param_desc = self._decode_param_desc(self.buffer)

                    elif mtype == b'T':
                        # RowDescription
                        result_desc = self._decode_row_desc(self.buffer)
                        break

                    elif mtype == b'n':
                        # NoData
                        self.buffer.discard_message()
                        param_desc = []
                        result_desc = []
                        break

                    elif mtype == b'E':  ## result
                        # ErrorResponse
                        er_cls, er_fields = self.parse_error_message()
                        raise er_cls(fields=er_fields)

                    else:
                        self.fallthrough()

                finally:
                    self.buffer.finish_message()
        except Exception:
            self.send_sync()
            await self.wait_for_sync()
            raise

        if param_desc is None:
            raise RuntimeError(
                "did not receive ParameterDescription from backend "
                "in response to Describe"
            )

        if result_desc is None:
            raise RuntimeError(
                "did not receive RowDescription from backend "
                "in response to Describe"
            )

        return param_desc, result_desc

    def _decode_param_desc(self, buf: ReadBuffer):
        cdef:
            int16_t nparams
            uint32_t p_oid
            list result = []

        nparams = buf.read_int16()

        for _ in range(nparams):
            p_oid = <uint32_t>buf.read_int32()
            result.append(p_oid)

        return result

    def _decode_row_desc(self, buf: ReadBuffer):
        cdef:
            int16_t nfields

            bytes f_name
            uint32_t f_table_oid
            int16_t f_column_num
            uint32_t f_dt_oid
            int16_t f_dt_size
            int32_t f_dt_mod
            int16_t f_format

            list result

        nfields = buf.read_int16()

        result = []
        for _ in range(nfields):
            f_name = buf.read_null_str()
            f_table_oid = <uint32_t>buf.read_int32()
            f_column_num = buf.read_int16()
            f_dt_oid = <uint32_t>buf.read_int32()
            f_dt_size = buf.read_int16()
            f_dt_mod = buf.read_int32()
            f_format = buf.read_int16()

            result.append((f_name.decode("utf-8"), f_dt_oid))

        return result

    async def sql_describe(
        self,
        query: bytes,
        param_type_oids: Optional[list[int]] = None,
    ) -> tuple[list[int], list[tuple[str, int]]]:
        self.before_command()
        started_at = time.monotonic()
        try:
            return await self._describe(query, param_type_oids)
        finally:
            await self.after_command()

    async def _parse_execute(
        self,
        query,
        frontend.AbstractFrontendConnection fe_conn,
        WriteBuffer bind_data,
        bint use_prep_stmt,
        bytes state,
        int dbver,
        bint use_pending_func_cache,
        tx_isolation,
        list param_data_types,
        bytes query_prefix,
        bint needs_commit_state,
    ):
        cdef:
            WriteBuffer out
            WriteBuffer buf
            bytes stmt_name
            bytes sql
            tuple sqls
            bytes prologue_sql
            bytes epilogue_sql

            int32_t dat_len

            bint parse = 1
            bint state_sync = 0

            bint has_result = query.cardinality is not CARD_NO_RESULT
            bint discard_result = (
                fe_conn is not None and query.output_format == FMT_NONE)

            uint64_t msgs_num
            uint64_t msgs_executed = 0
            uint64_t i

        out = WriteBuffer.new()

        if state is not None:
            self._build_apply_state_req(state, out)
            if (
                query.tx_id
                or not query.is_transactional
                or query.run_and_rollback
                or tx_isolation is not None
                or needs_commit_state
                or self.state_reset_needs_commit
            ):
                # This query has START TRANSACTION or non-transactional command
                # like CREATE DATABASE in it.
                # Restoring state must be performed in a separate
                # implicit transaction (otherwise START TRANSACTION DEFERRABLE
                # or CREATE DATABASE (since PG 14.7) would fail).
                # Hence - inject a SYNC after a state restore step.
                state_sync = 1
                self.write_sync(out)

        if query.run_and_rollback or tx_isolation is not None:
            if self.in_tx():
                sp_name = f'_edb_{time.monotonic_ns()}'
                prologue_sql = f'SAVEPOINT {sp_name}'.encode('utf-8')
            else:
                sp_name = None
                prologue_sql = b'START TRANSACTION'
                if tx_isolation is not None:
                    prologue_sql += (
                        f' ISOLATION LEVEL {tx_isolation._value_}'
                        .encode('utf-8')
                    )

            buf = WriteBuffer.new_message(b'P')
            buf.write_bytestring(b'')
            buf.write_bytestring(prologue_sql)
            buf.write_int16(0)
            out.write_buffer(buf.end_message())

            buf = WriteBuffer.new_message(b'B')
            buf.write_bytestring(b'')  # portal name
            buf.write_bytestring(b'')  # statement name
            buf.write_int16(0)  # number of format codes
            buf.write_int16(0)  # number of parameters
            buf.write_int16(0)  # number of result columns
            out.write_buffer(buf.end_message())

            buf = WriteBuffer.new_message(b'E')
            buf.write_bytestring(b'')  # portal name
            buf.write_int32(0)  # limit: 0 - return all rows
            out.write_buffer(buf.end_message())

            # Insert a SYNC as a boundary of the parsing logic later
            self.write_sync(out)

        if use_pending_func_cache and query.cache_func_call:
            sql, stmt_name = query.cache_func_call
            sqls = (query_prefix + sql,)
        else:
            sqls = (query_prefix + query.sql,) + query.db_op_trailer
            stmt_name = query.sql_hash

        msgs_num = <uint64_t>(len(sqls))

        if use_prep_stmt:
            parse = self.before_prepare(stmt_name, dbver, out)
        else:
            stmt_name = b''

        if parse:
            if len(self.last_parse_prep_stmts):
                for stmt_name_to_clean in self.last_parse_prep_stmts:
                    out.write_buffer(
                        self.make_clean_stmt_message(stmt_name_to_clean))
                self.last_parse_prep_stmts.clear()

            if stmt_name == b'' and msgs_num > 1:
                i = 0
                for sql in sqls:
                    pname = b'__p%d__' % i
                    self.last_parse_prep_stmts.append(pname)
                    buf = WriteBuffer.new_message(b'P')
                    buf.write_bytestring(pname)
                    buf.write_bytestring(sql)
                    buf.write_int16(0)
                    out.write_buffer(buf.end_message())
                    i += 1
                    metrics.query_size.observe(
                        len(sql), self.get_tenant_label(), 'compiled'
                    )
            else:
                if len(sqls) != 1:
                    raise errors.InternalServerError(
                        'cannot PARSE more than one SQL query '
                        'in non-anonymous mode')
                msgs_num = 1
                buf = WriteBuffer.new_message(b'P')
                buf.write_bytestring(stmt_name)
                buf.write_bytestring(sqls[0])
                if param_data_types:
                    buf.write_int16(len(param_data_types))
                    for oid in param_data_types:
                        buf.write_int32(<int32_t>oid)
                else:
                    buf.write_int16(0)
                out.write_buffer(buf.end_message())
                metrics.query_size.observe(
                    len(sqls[0]), self.get_tenant_label(), 'compiled'
                )

        assert bind_data is not None
        if stmt_name == b'' and msgs_num > 1:
            for s in self.last_parse_prep_stmts:
                buf = WriteBuffer.new_message(b'B')
                buf.write_bytestring(b'')  # portal name
                buf.write_bytestring(s)  # statement name
                buf.write_buffer(bind_data)
                out.write_buffer(buf.end_message())

                buf = WriteBuffer.new_message(b'E')
                buf.write_bytestring(b'')  # portal name
                buf.write_int32(0)  # limit: 0 - return all rows
                out.write_buffer(buf.end_message())
        else:
            buf = WriteBuffer.new_message(b'B')
            buf.write_bytestring(b'')  # portal name
            buf.write_bytestring(stmt_name)  # statement name
            buf.write_buffer(bind_data)
            out.write_buffer(buf.end_message())

            buf = WriteBuffer.new_message(b'E')
            buf.write_bytestring(b'')  # portal name
            buf.write_int32(0)  # limit: 0 - return all rows
            out.write_buffer(buf.end_message())

        if query.run_and_rollback or tx_isolation is not None:
            if query.run_and_rollback:
                if sp_name:
                    sql = f'ROLLBACK TO SAVEPOINT {sp_name}'.encode('utf-8')
                else:
                    sql = b'ROLLBACK'
            else:
                sql = b'COMMIT'

            buf = WriteBuffer.new_message(b'P')
            buf.write_bytestring(b'')
            buf.write_bytestring(sql)
            buf.write_int16(0)
            out.write_buffer(buf.end_message())

            buf = WriteBuffer.new_message(b'B')
            buf.write_bytestring(b'')  # portal name
            buf.write_bytestring(b'')  # statement name
            buf.write_int16(0)  # number of format codes
            buf.write_int16(0)  # number of parameters
            buf.write_int16(0)  # number of result columns
            out.write_buffer(buf.end_message())

            buf = WriteBuffer.new_message(b'E')
            buf.write_bytestring(b'')  # portal name
            buf.write_int32(0)  # limit: 0 - return all rows
            out.write_buffer(buf.end_message())
        elif query.append_tx_op:
            if query.tx_commit:
                sql = b'COMMIT'
            elif query.tx_rollback:
                sql = b'ROLLBACK'
            else:
                raise errors.InternalServerError(
                    "QueryUnit.append_tx_op is set but none of the "
                    "Query.tx_<foo> properties are"
                )

            buf = WriteBuffer.new_message(b'P')
            buf.write_bytestring(b'')
            buf.write_bytestring(sql)
            buf.write_int16(0)
            out.write_buffer(buf.end_message())

            buf = WriteBuffer.new_message(b'B')
            buf.write_bytestring(b'')  # portal name
            buf.write_bytestring(b'')  # statement name
            buf.write_int16(0)  # number of format codes
            buf.write_int16(0)  # number of parameters
            buf.write_int16(0)  # number of result columns
            out.write_buffer(buf.end_message())

            buf = WriteBuffer.new_message(b'E')
            buf.write_bytestring(b'')  # portal name
            buf.write_int32(0)  # limit: 0 - return all rows
            out.write_buffer(buf.end_message())

        self.write_sync(out)
        self.write(out)

        result = None

        try:
            if state is not None:
                await self.wait_for_state_resp(
                    state, state_sync, needs_commit_state)

            if query.run_and_rollback or tx_isolation is not None:
                await self.wait_for_sync()

            buf = None
            while True:
                if not self.buffer.take_message():
                    await self.wait_for_message()
                mtype = self.buffer.get_message_type()

                try:
                    if mtype == b'D':
                        # DataRow
                        if discard_result:
                            self.buffer.discard_message()
                            continue
                        if not has_result and fe_conn is not None:
                            raise errors.InternalServerError(
                                f'query that was inferred to have '
                                f'no data returned received a DATA package; '
                                f'query: {sqls}')

                        if fe_conn is None:
                            ncol = self.buffer.read_int16()
                            row = []
                            for i in range(ncol):
                                dat_len = self.buffer.read_int32()
                                if dat_len == -1:
                                    row.append(None)
                                else:
                                    row.append(
                                        self.buffer.read_bytes(dat_len))
                            if result is None:
                                result = []
                            result.append(row)
                        else:
                            if buf is None:
                                buf = WriteBuffer.new()

                            self.buffer.redirect_messages(buf, b'D', 0)
                            if buf.len() >= DATA_BUFFER_SIZE:
                                fe_conn.write(buf)
                                buf = None

                    elif mtype == b'C':  ## result
                        # CommandComplete
                        self.buffer.discard_message()
                        if buf is not None:
                            fe_conn.write(buf)
                            buf = None
                        msgs_executed += 1
                        if msgs_executed == msgs_num:
                            break

                    elif mtype == b'1' and parse:
                        # ParseComplete
                        self.buffer.discard_message()
                        self.prep_stmts[stmt_name] = dbver

                    elif mtype == b'E':  ## result
                        # ErrorResponse
                        er_cls, er_fields = self.parse_error_message()
                        raise er_cls(fields=er_fields)

                    elif mtype == b'n':
                        # NoData
                        self.buffer.discard_message()

                    elif mtype == b's':  ## result
                        # PortalSuspended
                        self.buffer.discard_message()
                        break

                    elif mtype == b'2':
                        # BindComplete
                        self.buffer.discard_message()

                    elif mtype == b'I':  ## result
                        # EmptyQueryResponse
                        self.buffer.discard_message()
                        break

                    elif mtype == b'3':
                        # CloseComplete
                        self.buffer.discard_message()

                    else:
                        self.fallthrough()

                finally:
                    self.buffer.finish_message()
        finally:
            await self.wait_for_sync()

        return result

    async def parse_execute(
        self,
        *,
        query,
        WriteBuffer bind_data = NO_ARGS,
        list param_data_types = None,
        frontend.AbstractFrontendConnection fe_conn = None,
        bint use_prep_stmt = False,
        bytes state = None,
        int dbver = 0,
        bint use_pending_func_cache = 0,
        tx_isolation = None,
        query_prefix = None,
        bint needs_commit_state = False,
    ):
        self.before_command()
        started_at = time.monotonic()
        try:
            return await self._parse_execute(
                query,
                fe_conn,
                bind_data,
                use_prep_stmt,
                state,
                dbver,
                use_pending_func_cache,
                tx_isolation,
                param_data_types,
                query_prefix or b'',
                needs_commit_state,
            )
        finally:
            metrics.backend_query_duration.observe(
                time.monotonic() - started_at, self.get_tenant_label()
            )
            await self.after_command()

    async def sql_fetch(
        self,
        sql: bytes,
        *,
        args: tuple[bytes, ...] | list[bytes] = (),
        use_prep_stmt: bool = False,
        state: Optional[bytes] = None,
        tx_isolation: defines.TxIsolationLevel | None = None,
    ) -> list[tuple[bytes, ...]]:
        if use_prep_stmt:
            sql_digest = hashlib.sha1()
            sql_digest.update(sql)
            sql_hash = sql_digest.hexdigest().encode('latin1')
        else:
            sql_hash = None

        query = compiler.QueryUnit(
            sql=sql,
            sql_hash=sql_hash,
            status=b"",
        )

        return await self.parse_execute(
            query=query,
            bind_data=args_ser.combine_raw_args(args),
            use_prep_stmt=use_prep_stmt,
            state=state,
            tx_isolation=tx_isolation,
        )

    async def sql_fetch_val(
        self,
        sql: bytes,
        *,
        args: tuple[bytes, ...] | list[bytes] = (),
        use_prep_stmt: bool = False,
        state: Optional[bytes] = None,
        tx_isolation: defines.TxIsolationLevel | None = None,
    ) -> bytes:
        data = await self.sql_fetch(
            sql,
            args=args,
            use_prep_stmt=use_prep_stmt,
            state=state,
            tx_isolation=tx_isolation,
        )
        if data is None or len(data) == 0:
            return None
        elif len(data) > 1:
            raise RuntimeError(
                f"received too many rows for sql_fetch_val({sql!r})")
        row = data[0]
        if len(row) != 1:
            raise RuntimeError(
                f"received too many columns for sql_fetch_val({sql!r})")
        return row[0]

    async def sql_fetch_col(
        self,
        sql: bytes,
        *,
        args: tuple[bytes, ...] | list[bytes] = (),
        use_prep_stmt: bool = False,
        state: Optional[bytes] = None,
        tx_isolation: defines.TxIsolationLevel | None = None,
    ) -> list[bytes]:
        data = await self.sql_fetch(
            sql,
            args=args,
            use_prep_stmt=use_prep_stmt,
            state=state,
            tx_isolation=tx_isolation,
        )
        if not data:
            return []
        else:
            if len(data[0]) != 1:
                raise RuntimeError(
                    f"received too many columns for sql_fetch_col({sql!r})")
            return [row[0] for row in data]

    async def _sql_execute(self, bytes sql):
        cdef:
            WriteBuffer out
            WriteBuffer buf

        out = WriteBuffer.new()

        buf = WriteBuffer.new_message(b'Q')
        buf.write_bytestring(sql)
        out.write_buffer(buf.end_message())
        self.waiting_for_sync += 1

        self.write(out)

        exc = None
        result = None

        while True:
            if not self.buffer.take_message():
                await self.wait_for_message()
            mtype = self.buffer.get_message_type()

            try:
                if mtype == b'D':
                    self.buffer.discard_message()

                elif mtype == b'T':
                    # RowDescription
                    self.buffer.discard_message()

                elif mtype == b'C':
                    # CommandComplete
                    self.buffer.discard_message()

                elif mtype == b'E':
                    # ErrorResponse
                    exc = self.parse_error_message()

                elif mtype == b'I':
                    # EmptyQueryResponse
                    self.buffer.discard_message()

                elif mtype == b'Z':
                    self.parse_sync_message()
                    break

                else:
                    self.fallthrough()

            finally:
                self.buffer.finish_message()

        if exc is not None:
            raise exc[0](fields=exc[1])
        else:
            return result

    async def sql_execute(self, sql: bytes | tuple[bytes, ...]) -> None:
        self.before_command()
        started_at = time.monotonic()

        if isinstance(sql, tuple):
            sql_string = b";\n".join(sql)
        else:
            sql_string = sql

        try:
            return await self._sql_execute(sql_string)
        finally:
            metrics.backend_query_duration.observe(
                time.monotonic() - started_at, self.get_tenant_label()
            )
            await self.after_command()

    async def sql_apply_state(
        self,
        dbv: pg_ext.ConnectionView,
    ):
        self.before_command()
        try:
            state = dbv.serialize_state()
            if state is not None:
                buf = WriteBuffer.new()
                self._build_apply_sql_state_req(state, buf)
                self.write_sync(buf)
                self.write(buf)

                await self._parse_apply_state_resp(
                    2 if state != EMPTY_SQL_STATE else 1
                )
                await self.wait_for_sync()
                self.last_state = state
                self.state_reset_needs_commit = (
                    dbv.needs_commit_after_state_sync())
        finally:
            await self.after_command()

    async def sql_extended_query(
        self,
        actions,
        fe_conn: frontend.AbstractFrontendConnection,
        dbver: int,
        dbv: pg_ext.ConnectionView,
    ) -> tuple[bool, bool]:
        self.before_command()
        try:
            state = self._sql._write_sql_extended_query(actions, dbver, dbv)
            if state is not None:
                await self._parse_apply_state_resp(
                    2 if state != EMPTY_SQL_STATE else 1
                )
                await self.wait_for_sync()
                self.last_state = state
                self.state_reset_needs_commit = (
                    dbv.needs_commit_after_state_sync())
            try:
                return await self._sql._parse_sql_extended_query(
                    actions,
                    fe_conn,
                    dbver,
                    dbv,
                )
            finally:
                if not dbv.in_tx():
                    self.last_state = dbv.serialize_state()
                    self.state_reset_needs_commit = (
                        dbv.needs_commit_after_state_sync())
        finally:
            await self.after_command()

    def _write_error_position(
        self,
        msg_buf: WriteBuffer,
        query: bytes,
        pos_bytes: bytes,
        source_map: Optional[pg_codegen.SourceMap],
        offset: int = 0,
    ):
        if source_map:
            pos = int(pos_bytes.decode('utf8'))
            if offset > 0 or pos + offset > 0:
                pos += offset
            pos = source_map.translate(pos)
            # pg uses 1-based indexes
            pos += 1
            pos_bytes = str(pos).encode('utf8')
            msg_buf.write_byte(b'P') # Position
        else:
            msg_buf.write_byte(b'q')  # Internal query
            msg_buf.write_bytestring(query)
            msg_buf.write_byte(b'p')  # Internal position
        msg_buf.write_bytestring(pos_bytes)

    def load_last_ddl_return(self, object query_unit):
        if query_unit.ddl_stmt_id:
            data = self.last_indirect_return
            if data:
                ret = json.loads(data)
                if ret['ddl_stmt_id'] != query_unit.ddl_stmt_id:
                    raise RuntimeError(
                        'unrecognized data notice after a DDL command: '
                        'data_stmt_id do not match: expected '
                        f'{query_unit.ddl_stmt_id!r}, got '
                        f'{ret["ddl_stmt_id"]!r}'
                    )
                return ret
            else:
                raise RuntimeError(
                    'missing the required data notice after a DDL command'
                )

    async def _dump(self, block, output_queue, fragment_suggested_size):
        cdef:
            WriteBuffer buf
            WriteBuffer qbuf
            WriteBuffer out

        qbuf = WriteBuffer.new_message(b'Q')
        qbuf.write_bytestring(block.sql_copy_stmt)
        qbuf.end_message()

        self.write(qbuf)
        self.waiting_for_sync += 1

        er = None
        out = None
        i = 0
        while True:
            if not self.buffer.take_message():
                await self.wait_for_message()
            mtype = self.buffer.get_message_type()

            if mtype == b'H':
                # CopyOutResponse
                self.buffer.discard_message()

            elif mtype == b'd':
                # CopyData
                if out is None:
                    out = WriteBuffer.new()

                    if i == 0:
                        # The first COPY IN message is prefixed with
                        # `COPY_SIGNATURE` -- strip it.
                        first = self.buffer.consume_message()
                        if first[:len(COPY_SIGNATURE)] != COPY_SIGNATURE:
                            raise RuntimeError('invalid COPY IN message')

                        buf = WriteBuffer.new_message(b'd')
                        buf.write_bytes(first[len(COPY_SIGNATURE) + 8:])
                        buf.end_message()
                        out.write_buffer(buf)

                        if out._length >= fragment_suggested_size:
                            await output_queue.put((block, i, out))
                            i += 1
                            out = None

                        if (not self.buffer.take_message() or
                                self.buffer.get_message_type() != b'd'):
                            continue

                self.buffer.redirect_messages(
                    out, b'd', fragment_suggested_size)

                if out._length >= fragment_suggested_size:
                    self.transport.pause_reading()
                    await output_queue.put((block, i, out))
                    self.transport.resume_reading()
                    i += 1
                    out = None

            elif mtype == b'c':
                # CopyDone
                self.buffer.discard_message()

            elif mtype == b'C':
                # CommandComplete
                if out is not None:
                    await output_queue.put((block, i, out))
                self.buffer.discard_message()

            elif mtype == b'E':
                er = self.parse_error_message()

            elif mtype == b'Z':
                self.parse_sync_message()
                break

            else:
                self.fallthrough()

        if er is not None:
            raise er[0](fields=er[1])

    async def dump(self, input_queue, output_queue, fragment_suggested_size):
        self.before_command()
        try:
            while True:
                try:
                    block = input_queue.pop()
                except IndexError:
                    await output_queue.put(None)
                    return

                await self._dump(block, output_queue, fragment_suggested_size)
        finally:
            # In case we errored while the transport was suspended.
            self.transport.resume_reading()
            await self.after_command()

    async def _restore(self, restore_block, bytes data, dict type_map):
        cdef:
            WriteBuffer buf
            WriteBuffer qbuf
            WriteBuffer out

            char* cbuf
            ssize_t clen
            ssize_t ncols

        qbuf = WriteBuffer.new_message(b'Q')
        qbuf.write_bytestring(restore_block.sql_copy_stmt)
        qbuf.end_message()

        self.write(qbuf)
        self.waiting_for_sync += 1

        er = None
        while True:
            if not self.buffer.take_message():
                await self.wait_for_message()
            mtype = self.buffer.get_message_type()

            if mtype == b'G':
                # CopyInResponse
                self.buffer.read_byte()
                ncols = self.buffer.read_int16()
                self.buffer.discard_message()
                break

            elif mtype == b'E':
                er = self.parse_error_message()

            elif mtype == b'Z':
                self.parse_sync_message()
                break

            else:
                self.fallthrough()

        if er is not None:
            raise er[0](fields=er[1])

        buf = WriteBuffer.new()
        cpython.PyBytes_AsStringAndSize(data, &cbuf, &clen)
        if (
            restore_block.compat_elided_cols
            or any(desc for desc in restore_block.data_mending_desc)
        ):
            self._rewrite_copy_data(
                buf,
                cbuf,
                clen,
                ncols,
                restore_block.data_mending_desc,
                type_map,
                restore_block.compat_elided_cols,
            )
        else:
            if cbuf[0] != b'd':
                raise RuntimeError('unexpected dump data message structure')
            ln = <uint32_t>hton.unpack_int32(cbuf + 1)
            buf.write_byte(b'd')
            buf.write_int32(ln + len(COPY_SIGNATURE) + 8)
            buf.write_bytes(COPY_SIGNATURE)
            buf.write_int32(0)
            buf.write_int32(0)
            buf.write_cstr(cbuf + 5, clen - 5)

        self.write(buf)

        qbuf = WriteBuffer.new_message(b'c')
        qbuf.end_message()
        self.write(qbuf)

        while True:
            if not self.buffer.take_message():
                await self.wait_for_message()
            mtype = self.buffer.get_message_type()

            if mtype == b'C':
                # CommandComplete
                self.buffer.discard_message()

            elif mtype == b'E':
                er = self.parse_error_message()

            elif mtype == b'Z':
                self.parse_sync_message()
                break

        if er is not None:
            raise er[0](fields=er[1])

    cdef _rewrite_copy_data(
        self,
        WriteBuffer wbuf,
        char* data,
        ssize_t data_len,
        ssize_t ncols,
        tuple data_mending_desc,
        dict type_id_map,
        tuple elided_cols,
    ):
        """Rewrite the binary COPY stream."""
        cdef:
            FRBuffer rbuf
            FRBuffer datum_buf
            ssize_t i
            ssize_t real_ncols
            int8_t *elide
            int8_t elided
            int32_t datum_len
            char copy_msg_byte
            int16_t copy_msg_ncols
            const char *datum
            bint first = True
            bint received_eof = False

        real_ncols = ncols + len(elided_cols)
        frb_init(&rbuf, data, data_len)

        elide = <int8_t*>cpythonx.PyMem_Calloc(
            <size_t>real_ncols, sizeof(int8_t))

        try:
            for col in elided_cols:
                elide[col] = 1

            mbuf = WriteBuffer.new()

            while frb_get_len(&rbuf):
                if received_eof:
                    raise RuntimeError('received CopyData after EOF')
                mbuf.start_message(b'd')

                copy_msg_byte = frb_read(&rbuf, 1)[0]
                if copy_msg_byte != b'd':
                    raise RuntimeError(
                        'unexpected dump data message structure')
                frb_read(&rbuf, 4)

                if first:
                    mbuf.write_bytes(COPY_SIGNATURE)
                    mbuf.write_int32(0)
                    mbuf.write_int32(0)
                    first = False

                copy_msg_ncols = hton.unpack_int16(frb_read(&rbuf, 2))
                if copy_msg_ncols == -1:
                    # BINARY COPY EOF marker
                    mbuf.write_int16(copy_msg_ncols)
                    received_eof = True
                    mbuf.end_message()
                    wbuf.write_buffer(mbuf)
                    mbuf.reset()
                    continue
                else:
                    mbuf.write_int16(<int16_t>ncols)

                # Tuple data
                for i in range(real_ncols):
                    datum_len = hton.unpack_int32(frb_read(&rbuf, 4))
                    elided = elide[i]
                    if not elided:
                        mbuf.write_int32(datum_len)
                    if datum_len != -1:
                        datum = frb_read(&rbuf, datum_len)

                        if not elided:
                            datum_mending_desc = data_mending_desc[i]
                            if (
                                datum_mending_desc is not None
                                and datum_mending_desc.needs_mending
                            ):
                                frb_init(&datum_buf, datum, datum_len)
                                self._mend_copy_datum(
                                    mbuf,
                                    &datum_buf,
                                    datum_mending_desc,
                                    type_id_map,
                                )
                            else:
                                mbuf.write_cstr(datum, datum_len)

                mbuf.end_message()
                wbuf.write_buffer(mbuf)
                mbuf.reset()
        finally:
            cpython.PyMem_Free(elide)

    cdef _mend_copy_datum(
        self,
        WriteBuffer wbuf,
        FRBuffer *rbuf,
        object mending_desc,
        dict type_id_map,
    ):
        cdef:
            ssize_t remainder
            int32_t ndims
            int32_t i
            int32_t nelems
            int32_t dim
            const char *buf
            FRBuffer elem_buf
            int32_t elem_len
            object elem_mending_desc

        kind = mending_desc.schema_object_class

        if kind is qltypes.SchemaObjectClass.ARRAY_TYPE:
            # Dimensions and flags
            buf = frb_read(rbuf, 8)
            ndims = hton.unpack_int32(buf)
            wbuf.write_cstr(buf, 8)
            elem_mending_desc = mending_desc.elements[0]
            # Discard the original element OID.
            frb_read(rbuf, 4)
            # Write the correct element OID.
            elem_type_id = elem_mending_desc.schema_type_id
            elem_type_oid = type_id_map[elem_type_id]
            wbuf.write_int32(<int32_t>elem_type_oid)

            if ndims == 0:
                # Empty array
                return

            if ndims != 1:
                raise ValueError(
                    'unexpected non-single dimension array'
                )

            if mending_desc.needs_mending:
                # dim and lbound
                buf = frb_read(rbuf, 8)
                nelems = hton.unpack_int32(buf)
                wbuf.write_cstr(buf, 8)

                for i in range(nelems):
                    elem_len = hton.unpack_int32(frb_read(rbuf, 4))
                    wbuf.write_int32(elem_len)
                    frb_slice_from(&elem_buf, rbuf, elem_len)
                    self._mend_copy_datum(
                        wbuf,
                        &elem_buf,
                        mending_desc.elements[0],
                        type_id_map,
                    )

        elif kind is qltypes.SchemaObjectClass.TUPLE_TYPE:
            nelems = hton.unpack_int32(frb_read(rbuf, 4))
            wbuf.write_int32(nelems)

            for i in range(nelems):
                elem_mending_desc = mending_desc.elements[i]
                if elem_mending_desc is not None:
                    # Discard the original element OID.
                    frb_read(rbuf, 4)
                    # Write the correct element OID.
                    elem_type_id = elem_mending_desc.schema_type_id
                    elem_type_oid = type_id_map[elem_type_id]
                    wbuf.write_int32(<int32_t>elem_type_oid)

                    elem_len = hton.unpack_int32(frb_read(rbuf, 4))
                    wbuf.write_int32(elem_len)

                    if elem_len != -1:
                        frb_slice_from(&elem_buf, rbuf, elem_len)

                        if elem_mending_desc.needs_mending:
                            self._mend_copy_datum(
                                wbuf,
                                &elem_buf,
                                elem_mending_desc,
                                type_id_map,
                            )
                        else:
                            wbuf.write_frbuf(&elem_buf)
                else:
                    buf = frb_read(rbuf, 8)
                    wbuf.write_cstr(buf, 8)
                    elem_len = hton.unpack_int32(buf + 4)
                    if elem_len != -1:
                        wbuf.write_cstr(frb_read(rbuf, elem_len), elem_len)

        wbuf.write_frbuf(rbuf)

    async def restore(self, restore_block, bytes data, dict type_map):
        self.before_command()
        try:
            await self._restore(restore_block, data, type_map)
        finally:
            await self.after_command()

    def is_healthy(self):
        return (
            self.connected and
            self.idle and
            self.cancel_fut is None and
            not self.waiting_for_sync and
            not self.in_tx()
        )

    cdef before_command(self):
        if not self.connected:
            raise RuntimeError(
                'pgcon: cannot issue new command: not connected')

        if self.waiting_for_sync:
            raise RuntimeError(
                'pgcon: cannot issue new command; waiting for sync')

        if not self.idle:
            raise RuntimeError(
                'pgcon: cannot issue new command; '
                'another command is in progress')

        if self.cancel_fut is not None:
            raise RuntimeError(
                'pgcon: cannot start new command while cancelling the '
                'previous one')

        self.idle = False
        self.last_indirect_return = None

    async def after_command(self):
        if self.idle:
            raise RuntimeError('pgcon: idle while running a command')

        if self.cancel_fut is not None:
            await self.cancel_fut
            self.cancel_fut = None
            self.idle = True

            # If we were cancelling a command in Postgres there can be a
            # race between us calling `pg_cancel_backend()` and us receiving
            # the results of the successfully executed command.  If this
            # happens, we might get the *next command* cancelled. To minimize
            # the chance of that we do another SYNC.
            await self.sync()

        else:
            self.idle = True

    cdef write(self, buf):
        self.transport.write(memoryview(buf))

    cdef fallthrough(self):
        if self.parse_notification():
            return

        cdef:
            char mtype = self.buffer.get_message_type()
        raise RuntimeError(
            f'unexpected message type {chr(mtype)!r}')

    cdef fallthrough_idle(self):
        cdef char mtype

        while self.buffer.take_message():
            if self.parse_notification():
                continue

            mtype = self.buffer.get_message_type()
            if mtype != b'E':  # ErrorResponse
                raise RuntimeError(
                    f'unexpected message type {chr(mtype)!r} '
                    f'in IDLE state')

            # We have an error message sent to us by the backend.
            # It is not safe to assume that the connection
            # is alive. We assume that it's dead and should be
            # marked as "closed".

            try:
                er_cls, fields = self.parse_error_message()
                self.aborted_with_error = er_cls(fields=fields)

                pgcode = fields['C']
                metrics.backend_connection_aborted.inc(
                    1.0, self.get_tenant_label(), pgcode
                )

                if pgcode in POSTGRES_SHUTDOWN_ERR_CODES:
                    pgreason = POSTGRES_SHUTDOWN_ERR_CODES[pgcode]
                    pgmsg = fields.get('M', pgreason)

                    logger.debug(
                        'backend connection aborted with a shutdown '
                        'error code %r(%s): %s',
                        pgcode, pgreason, pgmsg
                    )

                    if self.is_system_db:
                        self.tenant.set_pg_unavailable_msg(pgmsg)
                        self.tenant.on_sys_pgcon_failover_signal()

                else:
                    pgmsg = fields.get('M', '<empty message>')
                    logger.debug(
                        'backend connection aborted with an '
                        'error code %r: %s',
                        pgcode, pgmsg
                    )
            finally:
                self.abort()

    cdef parse_notification(self):
        cdef:
            char mtype = self.buffer.get_message_type()

        if mtype == b'S':
            # ParameterStatus
            name, value = self.parse_parameter_status_message()
            if self.is_system_db:
                self.tenant.on_sys_pgcon_parameter_status_updated(name, value)
            self.parameter_status[name] = value
            return True

        elif mtype == b'A':
            # NotificationResponse
            self.buffer.read_int32()  # discard pid
            channel = self.buffer.read_null_str().decode()
            payload = self.buffer.read_null_str().decode()
            self.buffer.finish_message()

            if not self.is_system_db:
                # The server is still initializing, or we're getting
                # notification from a non-system-db connection.
                return True

            if channel == '__edgedb_sysevent__':
                event_data = json.loads(payload)
                event = event_data.get('event')

                server_id = event_data.get('server_id')
                if server_id == self.server._server_id:
                    # We should only react to notifications sent
                    # by other edgedb servers. Reacting to events
                    # generated by this server must be implemented
                    # at a different layer.
                    return True

                logger.debug("received system event: %s", event)

                event_payload = event_data.get('args')
                if event == 'schema-changes':
                    dbname = event_payload['dbname']
                    self.tenant.on_remote_ddl(dbname)
                elif event == 'database-config-changes':
                    dbname = event_payload['dbname']
                    self.tenant.on_remote_database_config_change(dbname)
                elif event == 'system-config-changes':
                    self.tenant.on_remote_system_config_change()
                elif event == 'global-schema-changes':
                    self.tenant.on_global_schema_change()
                elif event == 'database-changes':
                    self.tenant.on_remote_database_changes()
                elif event == 'ensure-database-not-used':
                    dbname = event_payload['dbname']
                    self.tenant.on_remote_database_quarantine(dbname)
                elif event == 'query-cache-changes':
                    dbname = event_payload['dbname']
                    keys = event_payload.get('keys')
                    self.tenant.on_remote_query_cache_change(dbname, keys=keys)
                else:
                    raise AssertionError(f'unexpected system event: {event!r}')

            return True

        elif mtype == b'N':
            # NoticeResponse
            _, fields = self.parse_error_message()
            severity = fields.get('V')
            message = fields.get('M')
            detail = fields.get('D')
            if (
                severity == "NOTICE"
                and message.startswith("edb:notice:indirect_return")
            ):
                self.last_indirect_return = detail
            elif self.log_listeners:
                for listener in self.log_listeners:
                    self.loop.call_soon(listener, severity, message)
            return True

        return False

    cdef parse_error_message(self):
        cdef:
            char code
            str value
            dict fields = {}
            object err_cls

        while True:
            code = self.buffer.read_byte()
            if code == 0:
                break
            value = self.buffer.read_null_str().decode()
            fields[chr(code)] = value

        self.buffer.finish_message()

        err_cls = pgerror.get_error_class(fields)
        if self.debug:
            self.debug_print('ERROR', err_cls.__name__, fields)

        return err_cls, fields

    cdef char parse_sync_message(self):
        cdef char status

        if not self.waiting_for_sync:
            raise RuntimeError('unexpected sync')
        self.waiting_for_sync -= 1

        assert self.buffer.get_message_type() == b'Z'

        status = self.buffer.read_byte()

        if status == b'I':
            self.xact_status = PQTRANS_IDLE
        elif status == b'T':
            self.xact_status = PQTRANS_INTRANS
        elif status == b'E':
            self.xact_status = PQTRANS_INERROR
        else:
            self.xact_status = PQTRANS_UNKNOWN

        if self.debug:
            self.debug_print('SYNC MSG', self.xact_status)

        self.buffer.finish_message()
        return status

    cdef parse_parameter_status_message(self):
        cdef:
            str name
            str value
        assert self.buffer.get_message_type() == b'S'
        name = self.buffer.read_null_str().decode()
        value = self.buffer.read_null_str().decode()
        self.buffer.finish_message()
        if self.debug:
            self.debug_print('PARAMETER STATUS MSG', name, value)
        return name, value

    cdef make_clean_stmt_message(self, bytes stmt_name):
        cdef WriteBuffer buf
        buf = WriteBuffer.new_message(b'C')
        buf.write_byte(b'S')
        buf.write_bytestring(stmt_name)
        return buf.end_message()

    async def wait_for_message(self):
        if self.buffer.take_message():
            return
        if self.transport is None:
            raise ConnectionAbortedError()
        self.msg_waiter = self.loop.create_future()
        await self.msg_waiter

    def connection_made(self, transport):
        if self.transport is not None:
            raise RuntimeError('connection_made: invalid connection status')
        self.transport = transport
        self.connected = True
        self.connected_fut.set_result(True)
        self.connected_fut = None

    def connection_lost(self, exc):
        # Mark the connection as disconnected, so that `self.is_healthy()`
        # surely returns False for this connection.
        self.connected = False

        self.transport = None

        if self.pinned_by is not None:
            pinned_by = self.pinned_by
            self.pinned_by = None
            pinned_by.on_aborted_pgcon(self)

        if self.is_system_db:
            self.tenant.on_sys_pgcon_connection_lost(exc)
        elif self.tenant is not None:
            if not self.close_requested:
                self.tenant.on_pgcon_broken()
            else:
                self.tenant.on_pgcon_lost()

        if self.connected_fut is not None and not self.connected_fut.done():
            self.connected_fut.set_exception(ConnectionAbortedError())
            return

        if self.msg_waiter is not None and not self.msg_waiter.done():
            self.msg_waiter.set_exception(ConnectionAbortedError())
            self.msg_waiter = None

    def pause_writing(self):
        pass

    def resume_writing(self):
        pass

    def data_received(self, data):
        self.buffer.feed_data(data)

        if self.connected and self.idle:
            assert self.msg_waiter is None
            self.fallthrough_idle()

        elif (self.msg_waiter is not None and
                self.buffer.take_message() and
                not self.msg_waiter.cancelled()):
            self.msg_waiter.set_result(True)
            self.msg_waiter = None

    def eof_received(self):
        pass


# Underscored name for _SYNC_MESSAGE because it should always be emitted
# using write_sync(), which properly counts them
cdef bytes _SYNC_MESSAGE = bytes(WriteBuffer.new_message(b'S').end_message())
cdef bytes FLUSH_MESSAGE = bytes(WriteBuffer.new_message(b'H').end_message())

cdef EdegDBCodecContext DEFAULT_CODEC_CONTEXT = EdegDBCodecContext()

cdef inline int16_t read_int16(data: bytes):
    return int.from_bytes(data[0:2], "big", signed=True)

cdef inline int32_t read_int32(data: bytes):
    return int.from_bytes(data[0:4], "big", signed=True)
