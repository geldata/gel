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

from edb.server.pgproto.pgproto cimport (
    WriteBuffer,
    ReadBuffer,
    FRBuffer,
)

cdef enum PGAction:
    START_IMPLICIT_TX = 0
    PARSE = 1
    BIND = 2
    DESCRIBE_STMT = 3
    DESCRIBE_STMT_ROWS = 4
    DESCRIBE_PORTAL = 5
    EXECUTE = 6
    CLOSE_STMT = 7
    CLOSE_PORTAL = 8
    FLUSH = 9
    SYNC = 10


cdef class PGMessage:
    cdef:
        PGAction action
        bytes stmt_name
        bytes portal_name
        str orig_portal_name
        object args
        object query_unit
        bint frontend_only
        bint valid
        bint injected

        object orig_query
        object fe_settings

    cdef inline bint is_frontend_only(self)
    cdef inline bint is_valid(self)
    cdef inline bint is_injected(self)


cdef class PGSQLConnection:
    cdef:
        PGConnection con

    cdef _rewrite_sql_error_response(self, PGMessage action, WriteBuffer buf)
