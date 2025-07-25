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


# All EdgeDB types support ordering and comparison.
# The below definitions of abstract operators declare this fact
# for the benefit of generic expressions (e.g. in abstract constraints).

CREATE ABSTRACT INFIX OPERATOR
std::`>=` (l: anytype, r: anytype) -> std::bool {
    CREATE ANNOTATION std::identifier := 'ge';
};

CREATE ABSTRACT INFIX OPERATOR
std::`>` (l: anytype, r: anytype) -> std::bool {
    CREATE ANNOTATION std::identifier := 'gt';
};

CREATE ABSTRACT INFIX OPERATOR
std::`<=` (l: anytype, r: anytype) -> std::bool {
    CREATE ANNOTATION std::identifier := 'le';
};

CREATE ABSTRACT INFIX OPERATOR
std::`<` (l: anytype, r: anytype) -> std::bool {
    CREATE ANNOTATION std::identifier := 'lt';
};

CREATE ABSTRACT INFIX OPERATOR
std::`=` (l: anytype, r: anytype) -> std::bool {
    CREATE ANNOTATION std::identifier := 'eq';
};

CREATE ABSTRACT INFIX OPERATOR
std::`?=` (l: OPTIONAL anytype, r: OPTIONAL anytype) -> std::bool {
    CREATE ANNOTATION std::identifier := 'coal_eq';
};

CREATE ABSTRACT INFIX OPERATOR
std::`!=` (l: anytype, r: anytype) -> std::bool {
    CREATE ANNOTATION std::identifier := 'ne';
};

CREATE ABSTRACT INFIX OPERATOR
std::`?!=` (l: OPTIONAL anytype, r: OPTIONAL anytype) -> std::bool {
    CREATE ANNOTATION std::identifier := 'coal_neq';
};
