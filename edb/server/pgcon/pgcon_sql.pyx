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

cdef class PGMessage:
    def __init__(
        self,
        PGAction action,
        bytes stmt_name=None,
        str portal_name=None,
        args=None,
        query_unit=None,
        fe_settings=None,
        injected=False,
        bytes force_portal_name=None,
    ):
        self.action = action
        self.stmt_name = stmt_name
        self.orig_portal_name = portal_name
        if force_portal_name is not None:
            self.portal_name = force_portal_name
        elif portal_name:
            self.portal_name = b'u' + portal_name.encode("utf-8")
        else:
            self.portal_name = b''
        self.args = args
        self.query_unit = query_unit

        self.fe_settings = fe_settings
        self.valid = True
        self.injected = injected
        if self.query_unit is not None:
            self.frontend_only = self.query_unit.frontend_only
        else:
            self.frontend_only = False

    cdef inline bint is_frontend_only(self):
        return self.frontend_only

    def invalidate(self):
        self.valid = False

    cdef inline bint is_valid(self):
        return self.valid

    cdef inline bint is_injected(self):
        return self.injected

    def as_injected(self) -> PGMessage:
        return PGMessage(
            action=self.action,
            stmt_name=self.stmt_name,
            portal_name=self.orig_portal_name,
            args=self.args,
            query_unit=self.query_unit,
            fe_settings=self.fe_settings,
            injected=True,
        )

    def __repr__(self):
        rv = []
        if self.action == PGAction.START_IMPLICIT_TX:
            rv.append("START_IMPLICIT_TX")
        elif self.action == PGAction.PARSE:
            rv.append("PARSE")
        elif self.action == PGAction.BIND:
            rv.append("BIND")
        elif self.action == PGAction.DESCRIBE_STMT:
            rv.append("DESCRIBE_STMT")
        elif self.action == PGAction.DESCRIBE_STMT_ROWS:
            rv.append("DESCRIBE_STMT_ROWS")
        elif self.action == PGAction.DESCRIBE_PORTAL:
            rv.append("DESCRIBE_PORTAL")
        elif self.action == PGAction.EXECUTE:
            rv.append("EXECUTE")
        elif self.action == PGAction.CLOSE_STMT:
            rv.append("CLOSE_STMT")
        elif self.action == PGAction.CLOSE_PORTAL:
            rv.append("CLOSE_PORTAL")
        elif self.action == PGAction.FLUSH:
            rv.append("FLUSH")
        elif self.action == PGAction.SYNC:
            rv.append("SYNC")
        if self.stmt_name is not None:
            rv.append(f"stmt_name={self.stmt_name}")
        if self.orig_portal_name is not None:
            rv.append(f"portal_name={self.orig_portal_name!r}")
        if self.args is not None:
            rv.append(f"args={self.args}")
        rv.append(f"frontend_only={self.is_frontend_only()}")
        rv.append(f"injected={self.is_injected()}")
        if self.query_unit is not None:
            rv.append(f"query_unit={self.query_unit}")
        if len(rv) > 1:
            rv.insert(1, ":")
        return " ".join(rv)

cdef class PGSQLConnection:
    def __init__(self, con):
        self.con = con

    def _write_sql_extended_query(
        self,
        actions,
        dbver: int,
        dbv: pg_ext.ConnectionView,
    ) -> bytes:
        cdef:
            WriteBuffer buf, msg_buf
            PGMessage action
            bint be_parse

        buf = WriteBuffer.new()
        state = None
        if not dbv.in_tx():
            state = dbv.serialize_state()
            self.con._build_apply_sql_state_req(state, buf)
            # We need to close the implicit transaction with a SYNC here
            # because the next command may be e.g. "BEGIN DEFERRABLE".
            self.con.write_sync(buf)
        prepared = set()
        for action in actions:
            if action.is_frontend_only():
                continue

            be_parse = True
            if action.action == PGAction.PARSE:
                sql_text, data = action.args[:2]
                if action.stmt_name in prepared:
                    action.frontend_only = True
                else:
                    if action.stmt_name:
                        be_parse = self.con.before_prepare(
                            action.stmt_name, dbver, buf
                        )
                    if not be_parse:
                        if self.con.debug:
                            self.con.debug_print(
                                'Parse cache hit', action.stmt_name, sql_text)
                        action.frontend_only = True
                if not action.is_frontend_only():
                    prepared.add(action.stmt_name)
                    msg_buf = WriteBuffer.new_message(b'P')
                    msg_buf.write_bytestring(action.stmt_name)
                    msg_buf.write_bytestring(sql_text)
                    msg_buf.write_bytes(data)
                    buf.write_buffer(msg_buf.end_message())
                    metrics.query_size.observe(
                        len(sql_text), self.con.get_tenant_label(), 'compiled'
                    )
                    if self.con.debug:
                        self.con.debug_print(
                            'Parse', action.stmt_name, sql_text, data
                        )

            elif action.action == PGAction.BIND:
                if action.query_unit is not None and action.query_unit.prepare:
                    be_stmt_name = action.query_unit.prepare.be_stmt_name
                    if be_stmt_name in prepared:
                        action.frontend_only = True
                    else:
                        if be_stmt_name:
                            be_parse = self.con.before_prepare(
                                be_stmt_name, dbver, buf
                            )
                        if not be_parse:
                            if self.con.debug:
                                self.con.debug_print(
                                    'Parse cache hit', be_stmt_name)
                            action.frontend_only = True
                            prepared.add(be_stmt_name)

                if action.is_frontend_only():
                    pass
                elif action.query_unit is not None and isinstance(
                    action.query_unit.command_complete_tag, dbstate.TagUnpackRow
                ):
                    # in this case we are intercepting the only result row so
                    # we want to set its encoding to be binary
                    msg_buf = WriteBuffer.new_message(b'B')
                    msg_buf.write_bytestring(action.portal_name)
                    msg_buf.write_bytestring(action.stmt_name)

                    # skim over param format codes
                    param_formats = read_int16(action.args[0:2])
                    offset = 2 + param_formats * 2

                    # skim over param values
                    params = read_int16(action.args[offset:offset+2])
                    offset += 2
                    for p in range(params):
                        size = read_int32(action.args[offset:offset+4])
                        if size == -1:  # special case: NULL
                            size = 0
                        offset += 4 + size
                    msg_buf.write_bytes(action.args[0:offset])

                    # set the result formats
                    msg_buf.write_int16(1)  # number of columns
                    msg_buf.write_int16(1)  # binary encoding
                    buf.write_buffer(msg_buf.end_message())
                else:
                    msg_buf = WriteBuffer.new_message(b'B')
                    msg_buf.write_bytestring(action.portal_name)
                    msg_buf.write_bytestring(action.stmt_name)
                    msg_buf.write_bytes(action.args)
                    buf.write_buffer(msg_buf.end_message())

            elif (
                action.action
                in (PGAction.DESCRIBE_STMT, PGAction.DESCRIBE_STMT_ROWS)
            ):
                msg_buf = WriteBuffer.new_message(b'D')
                msg_buf.write_byte(b'S')
                msg_buf.write_bytestring(action.stmt_name)
                buf.write_buffer(msg_buf.end_message())

            elif action.action == PGAction.DESCRIBE_PORTAL:
                msg_buf = WriteBuffer.new_message(b'D')
                msg_buf.write_byte(b'P')
                msg_buf.write_bytestring(action.portal_name)
                buf.write_buffer(msg_buf.end_message())

            elif action.action == PGAction.EXECUTE:
                if action.query_unit is not None and action.query_unit.prepare:
                    be_stmt_name = action.query_unit.prepare.be_stmt_name

                    if be_stmt_name in prepared:
                        action.frontend_only = True
                    else:
                        if be_stmt_name:
                            be_parse = self.con.before_prepare(
                                be_stmt_name, dbver, buf
                            )
                        if not be_parse:
                            if self.con.debug:
                                self.con.debug_print(
                                    'Parse cache hit', be_stmt_name)
                            action.frontend_only = True
                            prepared.add(be_stmt_name)

                if (
                    action.query_unit is not None
                    and action.query_unit.deallocate is not None
                    and self.con.before_prepare(
                        action.query_unit.deallocate.be_stmt_name, dbver, buf
                    )
                ):
                    # This prepared statement does not actually exist
                    # on this connection, so there's nothing to DEALLOCATE.
                    action.frontend_only = True

                if action.is_frontend_only():
                    pass
                elif action.query_unit is not None and isinstance(
                    action.query_unit.command_complete_tag,
                    (dbstate.TagCountMessages, dbstate.TagUnpackRow),
                ):
                    # when executing TagUnpackRow, don't pass the limit through
                    msg_buf = WriteBuffer.new_message(b'E')
                    msg_buf.write_bytestring(action.portal_name)
                    msg_buf.write_int32(0)
                    buf.write_buffer(msg_buf.end_message())
                else:
                    # base case
                    msg_buf = WriteBuffer.new_message(b'E')
                    msg_buf.write_bytestring(action.portal_name)
                    msg_buf.write_int32(action.args)
                    buf.write_buffer(msg_buf.end_message())

            elif action.action == PGAction.CLOSE_PORTAL:
                if action.query_unit is not None and action.query_unit.prepare:
                    be_stmt_name = action.query_unit.prepare.be_stmt_name
                    if be_stmt_name in prepared:
                        action.frontend_only = True

                if not action.is_frontend_only():
                    msg_buf = WriteBuffer.new_message(b'C')
                    msg_buf.write_byte(b'P')
                    msg_buf.write_bytestring(action.portal_name)
                    buf.write_buffer(msg_buf.end_message())

            elif action.action == PGAction.CLOSE_STMT:
                if action.query_unit is not None and action.query_unit.prepare:
                    be_stmt_name = action.query_unit.prepare.be_stmt_name
                    if be_stmt_name in prepared:
                        action.frontend_only = True

                if not action.is_frontend_only():
                    msg_buf = WriteBuffer.new_message(b'C')
                    msg_buf.write_byte(b'S')
                    msg_buf.write_bytestring(action.stmt_name)
                    buf.write_buffer(msg_buf.end_message())

            elif action.action == PGAction.FLUSH:
                msg_buf = WriteBuffer.new_message(b'H')
                buf.write_buffer(msg_buf.end_message())

            elif action.action == PGAction.SYNC:
                self.con.write_sync(buf)

        if action.action not in (PGAction.SYNC, PGAction.FLUSH):
            # Make sure _parse_sql_extended_query() complete by sending a FLUSH
            # to the backend, but we won't flush the results to the frontend
            # because it's not requested.
            msg_buf = WriteBuffer.new_message(b'H')
            buf.write_buffer(msg_buf.end_message())

        self.con.write(buf)
        return state

    async def _parse_sql_extended_query(
        self,
        actions,
        fe_conn: frontend.AbstractFrontendConnection,
        dbver: int,
        dbv: pg_ext.ConnectionView,
    ) -> tuple[bool, bool]:
        cdef:
            WriteBuffer buf, msg_buf
            PGMessage action
            bint ignore_till_sync = False
            int32_t row_count

        buf = WriteBuffer.new()
        rv = True

        for action in actions:
            if self.con.debug:
                self.con.debug_print(
                    'ACTION', action, 'ignore_till_sync=', ignore_till_sync
                )

            if ignore_till_sync and action.action != PGAction.SYNC:
                continue
            elif action.action == PGAction.FLUSH:
                if buf.len() > 0:
                    fe_conn.write(buf)
                    fe_conn.flush()
                    buf = WriteBuffer.new()
                continue
            elif action.action == PGAction.START_IMPLICIT_TX:
                dbv.start_implicit()
                continue
            elif action.is_frontend_only():
                if action.action == PGAction.PARSE:
                    if not action.is_injected():
                        msg_buf = WriteBuffer.new_message(b'1')
                        buf.write_buffer(msg_buf.end_message())
                elif action.action == PGAction.BIND:
                    dbv.create_portal(
                        action.orig_portal_name, action.query_unit
                    )
                    if not action.is_injected():
                        msg_buf = WriteBuffer.new_message(b'2')  # BindComplete
                        buf.write_buffer(msg_buf.end_message())
                elif action.action == PGAction.DESCRIBE_STMT:
                    # ParameterDescription
                    if not action.is_injected():
                        msg_buf = WriteBuffer.new_message(b't')
                        msg_buf.write_int16(0)  # number of parameters
                        buf.write_buffer(msg_buf.end_message())
                elif action.action == PGAction.EXECUTE:
                    if action.query_unit.set_vars is not None:
                        assert len(action.query_unit.set_vars) == 1
                        # CommandComplete
                        msg_buf = WriteBuffer.new_message(b'C')
                        if next(
                            iter(action.query_unit.set_vars.values())
                        ) is None:
                            msg_buf.write_bytestring(b'RESET')
                        else:
                            msg_buf.write_bytestring(b'SET')
                        buf.write_buffer(msg_buf.end_message())
                    elif not action.is_injected():
                        # NoData
                        msg_buf = WriteBuffer.new_message(b'n')
                        buf.write_buffer(msg_buf.end_message())
                        # CommandComplete
                        msg_buf = WriteBuffer.new_message(b'C')
                        assert isinstance(
                            action.query_unit.command_complete_tag,
                            dbstate.TagPlain,
                        ), "emulated SQL unit has no command_tag"
                        plain = action.query_unit.command_complete_tag
                        msg_buf.write_bytestring(plain.tag)
                        buf.write_buffer(msg_buf.end_message())

                    dbv.on_success(action.query_unit)
                    fe_conn.on_success(action.query_unit)
                elif action.action == PGAction.CLOSE_PORTAL:
                    dbv.close_portal_if_exists(action.orig_portal_name)
                    if not action.is_injected():
                        msg_buf = WriteBuffer.new_message(b'3') # CloseComplete
                        buf.write_buffer(msg_buf.end_message())
                elif action.action == PGAction.CLOSE_STMT:
                    if not action.is_injected():
                        msg_buf = WriteBuffer.new_message(b'3')  # CloseComplete
                        buf.write_buffer(msg_buf.end_message())
                if (
                    action.action == PGAction.DESCRIBE_STMT or
                    action.action == PGAction.DESCRIBE_PORTAL
                ):
                    if action.query_unit.set_vars is not None:
                        msg_buf = WriteBuffer.new_message(b'n')  # NoData
                        buf.write_buffer(msg_buf.end_message())
                continue

            row_count = 0
            while True:
                if not self.con.buffer.take_message():
                    if buf.len() > 0:
                        fe_conn.write(buf)
                        fe_conn.flush()
                        buf = WriteBuffer.new()
                    await self.con.wait_for_message()

                mtype = self.con.buffer.get_message_type()
                if self.con.debug:
                    self.con.debug_print(f'recv backend message: {chr(mtype)!r}')
                    if ignore_till_sync:
                        self.con.debug_print("ignoring until SYNC")

                if ignore_till_sync and mtype != b'Z':
                    self.con.buffer.discard_message()
                    continue

                if (
                    mtype == b'3'
                    and action.action != PGAction.CLOSE_PORTAL
                    and action.action != PGAction.CLOSE_STMT
                ):
                    # before_prepare() initiates LRU cleanup for
                    # prepared statements, so CloseComplete may
                    # appear here.
                    self.con.buffer.discard_message()
                    continue

                # ParseComplete
                if mtype == b'1' and action.action == PGAction.PARSE:
                    self.con.buffer.finish_message()
                    if self.con.debug:
                        self.con.debug_print('PARSE COMPLETE MSG')
                    if action.stmt_name:
                        self.con.prep_stmts[action.stmt_name] = dbver
                    if not action.is_injected():
                        msg_buf = WriteBuffer.new_message(mtype)
                        buf.write_buffer(msg_buf.end_message())
                    break

                # BindComplete
                elif mtype == b'2' and action.action == PGAction.BIND:
                    self.con.buffer.finish_message()
                    if self.con.debug:
                        self.con.debug_print('BIND COMPLETE MSG')
                    if action.query_unit is not None:
                        dbv.create_portal(
                            action.orig_portal_name, action.query_unit
                        )
                    if not action.is_injected():
                        msg_buf = WriteBuffer.new_message(mtype)
                        buf.write_buffer(msg_buf.end_message())
                    break

                elif (
                    # RowDescription or NoData
                    mtype == b'T' or mtype == b'n'
                ) and (
                    action.action == PGAction.DESCRIBE_STMT or
                    action.action == PGAction.DESCRIBE_STMT_ROWS or
                    action.action == PGAction.DESCRIBE_PORTAL
                ):
                    data = self.con.buffer.consume_message()
                    if self.con.debug:
                        self.con.debug_print('END OF DESCRIBE', mtype)
                    if (
                        mtype == b'T'
                        and action.query_unit is not None
                        and isinstance(
                            action.query_unit.command_complete_tag,
                            dbstate.TagUnpackRow,
                        )
                    ):
                        # TagUnpackRow converts RowDescription into NoData
                        msg_buf = WriteBuffer.new_message(b'n')
                        buf.write_buffer(msg_buf.end_message())

                    elif not action.is_injected() and not (
                        mtype == b'n' and
                        action.action == PGAction.DESCRIBE_STMT_ROWS
                    ):
                        msg_buf = WriteBuffer.new_message(mtype)
                        msg_buf.write_bytes(data)
                        buf.write_buffer(msg_buf.end_message())
                    break

                elif (
                    mtype == b't'  # ParameterDescription
                    and action.action == PGAction.DESCRIBE_STMT_ROWS
                ):
                    self.con.buffer.consume_message()

                elif (
                    mtype == b't'  # ParameterDescription
                ):
                    # remap parameter descriptions

                    # The "external" parameters (that are visible to the user)
                    # don't include the internal params for globals and
                    # extracted constants.
                    # This chunk of code remaps the descriptions of internal
                    # params into external ones.
                    self.con.buffer.read_int16()  # count_internal
                    data_internal = self.con.buffer.consume_message()

                    msg_buf = WriteBuffer.new_message(b't')
                    external_params: int64_t = 0
                    if (
                        action.query_unit is not None
                        and action.query_unit.params
                    ):
                        for index, param in enumerate(action.query_unit.params):
                            if not isinstance(param, dbstate.SQLParamExternal):
                                break
                            external_params = index + 1

                    msg_buf.write_int16(external_params)
                    msg_buf.write_bytes(data_internal[0:external_params * 4])

                    buf.write_buffer(msg_buf.end_message())

                elif (
                    mtype == b'T'  # RowDescription
                    and action.action == PGAction.EXECUTE
                    and action.query_unit is not None
                    and isinstance(
                        action.query_unit.command_complete_tag,
                        dbstate.TagUnpackRow,
                    )
                ):
                    data = self.con.buffer.consume_message()

                    # tell the frontend connection that there is NoData
                    # because we intercept and unpack the DataRow.
                    msg_buf = WriteBuffer.new_message(b'n')
                    buf.write_buffer(msg_buf.end_message())
                elif (
                    mtype == b'D'  # DataRow
                    and action.action == PGAction.EXECUTE
                    and action.query_unit is not None
                    and isinstance(
                        action.query_unit.command_complete_tag,
                        dbstate.TagUnpackRow,
                    )
                ):
                    # unpack a single row with a single column
                    data = self.con.buffer.consume_message()

                    field_size = read_int32(data[2:6])
                    val_bytes = data[6:6 + field_size]

                    row_count = int.from_bytes(val_bytes, "big", signed=True)
                elif (
                    # CommandComplete, EmptyQueryResponse, PortalSuspended
                    mtype == b'C' or mtype == b'I' or mtype == b's'
                ) and action.action == PGAction.EXECUTE:
                    data = self.con.buffer.consume_message()
                    if self.con.debug:
                        self.con.debug_print('END OF EXECUTE', mtype)
                    if action.query_unit is not None:
                        fe_conn.on_success(action.query_unit)
                        dbv.on_success(action.query_unit)

                        if action.query_unit.prepare is not None:
                            be_stmt_name = action.query_unit.prepare.be_stmt_name
                            if be_stmt_name:
                                if self.con.debug:
                                    self.con.debug_print(
                                        f"remembering ps {be_stmt_name}, "
                                        f"dbver {dbver}"
                                    )
                                self.con.prep_stmts[be_stmt_name] = dbver

                    if (
                        not action.is_injected()
                        and action.query_unit is not None
                        and action.query_unit.command_complete_tag
                    ):
                        tag = action.query_unit.command_complete_tag

                        msg_buf = WriteBuffer.new_message(mtype)
                        if isinstance(tag, dbstate.TagPlain):
                            msg_buf.write_bytestring(tag.tag)

                        elif isinstance(tag, (dbstate.TagCountMessages, dbstate.TagUnpackRow)):
                            msg_buf.write_bytes(bytes(tag.prefix, "utf-8"))

                            # This should return the number of modified rows by
                            # the top-level query, but we are returning the
                            # count of rows in the response. These two will
                            # always match because our compiled DML with always
                            # have a top-level SELECT with same number of rows
                            # as the DML stmt somewhere in the the CTEs.
                            msg_buf.write_str(str(row_count), "utf-8")

                        buf.write_buffer(msg_buf.end_message())

                    elif not action.is_injected():
                        msg_buf = WriteBuffer.new_message(mtype)
                        msg_buf.write_bytes(data)
                        buf.write_buffer(msg_buf.end_message())
                    break

                # CloseComplete
                elif mtype == b'3' and action.action == PGAction.CLOSE_PORTAL:
                    self.con.buffer.finish_message()
                    if self.con.debug:
                        self.con.debug_print('CLOSE COMPLETE MSG (PORTAL)')
                    dbv.close_portal_if_exists(action.orig_portal_name)
                    if not action.is_injected():
                        msg_buf = WriteBuffer.new_message(mtype)
                        buf.write_buffer(msg_buf.end_message())
                    break

                elif mtype == b'3' and action.action == PGAction.CLOSE_STMT:
                    self.con.buffer.finish_message()
                    if self.con.debug:
                        self.con.debug_print('CLOSE COMPLETE MSG (STATEMENT)')
                    if not action.is_injected():
                        msg_buf = WriteBuffer.new_message(mtype)
                        buf.write_buffer(msg_buf.end_message())
                    break

                elif mtype == b'E':  # ErrorResponse
                    rv = False
                    if self.con.debug:
                        self.con.debug_print('ERROR RESPONSE MSG')
                    if action.query_unit is not None:
                        fe_conn.on_error(action.query_unit)
                    dbv.on_error()
                    self._rewrite_sql_error_response(action, buf)
                    fe_conn.write(buf)
                    fe_conn.flush()
                    buf = WriteBuffer.new()
                    ignore_till_sync = True
                    break

                elif mtype == b'Z':  # ReadyForQuery
                    ignore_till_sync = False
                    dbv.end_implicit()
                    status = self.con.parse_sync_message()
                    msg_buf = WriteBuffer.new_message(b'Z')
                    msg_buf.write_byte(status)
                    buf.write_buffer(msg_buf.end_message())

                    fe_conn.write(buf)
                    fe_conn.flush()
                    return True, True

                else:
                    if not action.is_injected():
                        if self.con.debug:
                            self.con.debug_print('REDIRECT OTHER MSG', mtype)
                        messages_redirected = self.con.buffer.redirect_messages(
                            buf, mtype, 0
                        )

                        # DataRow
                        if mtype == b'D':
                            row_count += messages_redirected
                    else:
                        logger.warning(
                            f"discarding unexpected backend message: "
                            f"{chr(mtype)!r}"
                        )
                        self.con.buffer.discard_message()

        if buf.len() > 0:
            fe_conn.write(buf)
        return rv, False

    cdef _rewrite_sql_error_response(self, PGMessage action, WriteBuffer buf):
        cdef WriteBuffer msg_buf

        if action.action == PGAction.PARSE:
            msg_buf = WriteBuffer.new_message(b'E')
            while True:
                field_type = self.con.buffer.read_byte()
                if field_type == b'P':  # Position
                    if action.query_unit is None:
                        source_map = None
                        offset = 0
                    else:
                        qu = action.query_unit
                        source_map = qu.source_map
                        offset = -qu.prefix_len
                    self.con._write_error_position(
                        msg_buf,
                        action.args[0],
                        self.con.buffer.read_null_str(),
                        source_map,
                        offset,
                    )
                    continue
                else:
                    msg_buf.write_byte(field_type)
                    if field_type == b'\0':
                        break
                msg_buf.write_bytestring(
                    self.con.buffer.read_null_str()
                )
            self.con.buffer.finish_message()
            buf.write_buffer(msg_buf.end_message())
        elif action.action in (
            PGAction.BIND,
            PGAction.EXECUTE,
            PGAction.DESCRIBE_PORTAL,
            PGAction.CLOSE_PORTAL,
        ):
            portal_name = action.orig_portal_name
            msg_buf = WriteBuffer.new_message(b'E')
            message = None
            while True:
                field_type = self.con.buffer.read_byte()
                if field_type == b'C':  # Code
                    msg_buf.write_byte(field_type)
                    code = self.con.buffer.read_null_str()
                    msg_buf.write_bytestring(code)
                    if code == b'34000':
                        message = f'cursor "{portal_name}" does not exist'
                    elif code == b'42P03':
                        message = f'cursor "{portal_name}" already exists'
                elif field_type == b'M' and message:
                    msg_buf.write_byte(field_type)
                    msg_buf.write_bytestring(
                        message.encode('utf-8')
                    )
                elif field_type == b'P':
                    if action.query_unit is not None:
                        qu = action.query_unit
                        query_text = qu.query.encode("utf-8")
                        if qu.prepare is not None:
                            offset = -55
                            source_map = qu.prepare.source_map
                        else:
                            offset = 0
                            source_map = qu.source_map
                        offset -= qu.prefix_len
                    else:
                        query_text = b""
                        source_map = None
                        offset = 0

                    self.con._write_error_position(
                        msg_buf,
                        query_text,
                        self.con.buffer.read_null_str(),
                        source_map,
                        offset,
                    )
                else:
                    msg_buf.write_byte(field_type)
                    if field_type == b'\0':
                        break
                    msg_buf.write_bytestring(
                        self.con.buffer.read_null_str()
                    )
            self.con.buffer.finish_message()
            buf.write_buffer(msg_buf.end_message())
        else:
            data = self.con.buffer.consume_message()
            msg_buf = WriteBuffer.new_message(b'E')
            msg_buf.write_bytes(data)
            buf.write_buffer(msg_buf.end_message())
