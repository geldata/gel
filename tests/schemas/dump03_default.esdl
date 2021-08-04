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


scalar type MyStr extending str;
scalar type MySeq extending sequence;
scalar type MyPristineSeq extending sequence;

type Test {
    required property name -> str {
        constraint exclusive;
    };
    property array_of_tuples -> array<tuple<int64, MyStr, int64>>;
    property tuple_of_arrays ->
        tuple<
            MyStr,
            array<MyStr>,
            tuple<int64, int64, array<MyStr>>,
        >;
    property seq -> MySeq;
};
