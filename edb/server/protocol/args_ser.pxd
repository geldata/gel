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


cimport cython

from edb.server.dbview cimport dbview
from edb.server.pgproto.pgproto cimport WriteBuffer


cdef WriteBuffer recode_bind_args(
    dbview.DatabaseConnectionView dbv,
    dbview.CompiledQuery compiled,
    bytes bind_args,
    list converted_args,
    list positions = ?,
    list data_types = ?,
)


cdef recode_bind_args_for_script(
    dbview.DatabaseConnectionView dbv,
    dbview.CompiledQuery compiled,
    bytes bind_args,
    object converted_args,
    ssize_t start,
    ssize_t end,
)

cdef bytes recode_global(
    dbview.DatabaseConnectionView dbv,
    bytes glob,
    object glob_descriptor,
)

cdef WriteBuffer combine_raw_args(object args = ?)

@cython.final
cdef class ParamConversion:
    cdef:
        str param_name
        str conversion_name
        tuple additional_info
        bytes encoded_data
        object constant_value

cdef list[ParamConversion] get_param_conversions(
    dbview.DatabaseConnectionView dbv,
    list server_param_conversions,
    bytes bind_args,
    list[bytes] extra_blobs,
)

cdef dict[int, bytes] get_args_data_for_indexes(
    bytes args,
    list[int] target_indexes,
    args_needs_recoding: bool,
)

cdef class ConvertedArg:
    cdef:
        int bind_format_code

@cython.final
cdef class ConvertedArgStr(ConvertedArg):
    cdef:
        str data

    @staticmethod
    cdef ConvertedArgStr new(str data)

@cython.final
cdef class ConvertedArgFloat64(ConvertedArg):
    cdef:
        float data

    @staticmethod
    cdef ConvertedArgFloat64 new(float data)

@cython.final
cdef class ConvertedArgListFloat32(ConvertedArg):
    cdef:
        list data

    @staticmethod
    cdef ConvertedArgListFloat32 new(list data)
