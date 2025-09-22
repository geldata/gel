#
# This source file is part of the EdgeDB open source project.
#
# Copyright 2022-present MagicStack Inc. and the EdgeDB authors.
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


## Bitwise numeric functions
## -------------------------


CREATE FUNCTION
std::bit_and(l: std::int16, r: std::int16) -> std::int16
{
    CREATE ANNOTATION std::description :=
        'Bitwise AND operator for 16-bit integers.';
    SET volatility := 'Immutable';
    USING SQL $$
    SELECT l & r
    $$;
};


CREATE FUNCTION
std::bit_and(l: std::int32, r: std::int32) -> std::int32
{
    CREATE ANNOTATION std::description :=
        'Bitwise AND operator for 32-bit integers.';
    SET volatility := 'Immutable';
    USING SQL $$
    SELECT l & r
    $$;
};


CREATE FUNCTION
std::bit_and(l: std::int64, r: std::int64) -> std::int64
{
    CREATE ANNOTATION std::description :=
        'Bitwise AND operator for 64-bit integers.';
    SET volatility := 'Immutable';
    USING SQL $$
    SELECT l & r
    $$;
};


CREATE FUNCTION
std::bit_or(l: std::int16, r: std::int16) -> std::int16
{
    CREATE ANNOTATION std::description :=
        'Bitwise OR operator for 16-bit integers.';
    SET volatility := 'Immutable';
    USING SQL $$
    SELECT l | r
    $$;
};


CREATE FUNCTION
std::bit_or(l: std::int32, r: std::int32) -> std::int32
{
    CREATE ANNOTATION std::description :=
        'Bitwise OR operator for 32-bit integers.';
    SET volatility := 'Immutable';
    USING SQL $$
    SELECT l | r
    $$;
};


CREATE FUNCTION
std::bit_or(l: std::int64, r: std::int64) -> std::int64
{
    CREATE ANNOTATION std::description :=
        'Bitwise OR operator for 64-bit integers.';
    SET volatility := 'Immutable';
    USING SQL $$
    SELECT l | r
    $$;
};


CREATE FUNCTION
std::bit_xor(l: std::int16, r: std::int16) -> std::int16
{
    CREATE ANNOTATION std::description :=
        'Bitwise exclusive OR operator for 16-bit integers.';
    SET volatility := 'Immutable';
    USING SQL $$
    SELECT l # r
    $$;
};


CREATE FUNCTION
std::bit_xor(l: std::int32, r: std::int32) -> std::int32
{
    CREATE ANNOTATION std::description :=
        'Bitwise exclusive OR operator for 32-bit integers.';
    SET volatility := 'Immutable';
    USING SQL $$
    SELECT l # r
    $$;
};


CREATE FUNCTION
std::bit_xor(l: std::int64, r: std::int64) -> std::int64
{
    CREATE ANNOTATION std::description :=
        'Bitwise exclusive OR operator for 64-bit integers.';
    SET volatility := 'Immutable';
    USING SQL $$
    SELECT l # r
    $$;
};


CREATE FUNCTION
std::bit_not(r: std::int16) -> std::int16
{
    CREATE ANNOTATION std::description :=
        'Bitwise NOT operator for 16-bit integers.';
    SET volatility := 'Immutable';
    USING SQL $$
    SELECT ~r
    $$;
};


CREATE FUNCTION
std::bit_not(r: std::int32) -> std::int32
{
    CREATE ANNOTATION std::description :=
        'Bitwise NOT operator for 32-bit integers.';
    SET volatility := 'Immutable';
    USING SQL $$
    SELECT ~r
    $$;
};


CREATE FUNCTION
std::bit_not(r: std::int64) -> std::int64
{
    CREATE ANNOTATION std::description :=
        'Bitwise NOT operator for 64-bit integers.';
    SET volatility := 'Immutable';
    USING SQL $$
    SELECT ~r
    $$;
};


# In Postgres bitwise shift operators accept a 32-bit integer as the number of
# bit positions that need to be shifted. However, in EdgeDB the default
# integer literal is int64, so we should accept that and cast it down inside
# the function body.
#
# In Postgres the number of bits shifted gets truncated using a positive mod
# 32 (or mod 64 for int8). We do not want such truncation in EdgeDB. Shifting by 20 bits 2 times
# should bethe same as shifting by 40 bits once.
CREATE FUNCTION
std::bit_rshift(val: std::int16, n: std::int64) -> std::int16
{
    CREATE ANNOTATION std::description :=
        'Bitwise right-shift operator for 16-bit integers.';
    SET volatility := 'Immutable';
    USING SQL $$
    SELECT (
        CASE
            WHEN n < 0 THEN
                edgedb_VER.raise(
                    NULL::int8,
                    'invalid_parameter_value',
                    msg => (
                        'bit_rshift(): cannot shift by negative amount'
                    )
                )
            WHEN n > 31 THEN
                CASE
                    WHEN val < 0 THEN -1
                    ELSE 0
                END
            ELSE val >> n::int4
        END
    )
    $$;
};


CREATE FUNCTION
std::bit_rshift(val: std::int32, n: std::int64) -> std::int32
{
    CREATE ANNOTATION std::description :=
        'Bitwise right-shift operator for 32-bit integers.';
    SET volatility := 'Immutable';
    USING SQL $$
    SELECT (
        CASE
            WHEN n < 0 THEN
                edgedb_VER.raise(
                    NULL::int8,
                    'invalid_parameter_value',
                    msg => (
                        'bit_rshift(): cannot shift by negative amount'
                    )
                )
            WHEN n > 31 THEN
                CASE
                    WHEN val < 0 THEN -1
                    ELSE 0
                END
            ELSE val >> n::int4
        END
    )
    $$;
};


CREATE FUNCTION
std::bit_rshift(val: std::int64, n: std::int64) -> std::int64
{
    CREATE ANNOTATION std::description :=
        'Bitwise right-shift operator for 64-bit integers.';
    SET volatility := 'Immutable';
    USING SQL $$
    SELECT (
        CASE
            WHEN n < 0 THEN
                edgedb_VER.raise(
                    NULL::int8,
                    'invalid_parameter_value',
                    msg => (
                        'bit_rshift(): cannot shift by negative amount'
                    )
                )
            WHEN n > 63 THEN
                CASE
                    WHEN val < 0 THEN -1
                    ELSE 0
                END
            ELSE val >> n::int4
        END
    )
    $$;
};


CREATE FUNCTION
std::bit_lshift(val: std::int16, n: std::int64) -> std::int16
{
    CREATE ANNOTATION std::description :=
        'Bitwise left-shift operator for 16-bit integers.';
    SET volatility := 'Immutable';
    USING SQL $$
    SELECT (
        CASE
            WHEN n < 0 THEN
                edgedb_VER.raise(
                    NULL::int8,
                    'invalid_parameter_value',
                    msg => (
                        'bit_lshift(): cannot shift by negative amount'
                    )
                )
            WHEN n > 31 THEN 0
            ELSE val << n::int4
        END
    )
    $$;
};


CREATE FUNCTION
std::bit_lshift(val: std::int32, n: std::int64) -> std::int32
{
    CREATE ANNOTATION std::description :=
        'Bitwise left-shift operator for 32-bit integers.';
    SET volatility := 'Immutable';
    USING SQL $$
    SELECT (
        CASE
            WHEN n < 0 THEN
                edgedb_VER.raise(
                    NULL::int8,
                    'invalid_parameter_value',
                    msg => (
                        'bit_lshift(): cannot shift by negative amount'
                    )
                )
            WHEN n > 31 THEN 0
            ELSE val << n::int4
        END
    )
    $$;
};


CREATE FUNCTION
std::bit_lshift(val: std::int64, n: std::int64) -> std::int64
{
    CREATE ANNOTATION std::description :=
        'Bitwise left-shift operator for 64-bit integers.';
    SET volatility := 'Immutable';
    USING SQL $$
    SELECT (
        CASE
            WHEN n < 0 THEN
                edgedb_VER.raise(
                    NULL::int8,
                    'invalid_parameter_value',
                    msg => (
                        'bit_lshift(): cannot shift by negative amount'
                    )
                )
            WHEN n > 63 THEN 0
            ELSE val << n::int4
        END
    )
    $$;
};

CREATE FUNCTION
std::bit_count(val: std::int16) -> std::int64
{
    CREATE ANNOTATION std::description :=
        'Count the number of set bits in a 16-bit integer.';
    SET volatility := 'Immutable';
    USING SQL $$
    SELECT bit_count(val::int4::bit(16))
    $$;
};

CREATE FUNCTION
std::bit_count(val: std::int32) -> std::int64
{
    CREATE ANNOTATION std::description :=
        'Count the number of set bits in a 32-bit integer.';
    SET volatility := 'Immutable';
    USING SQL $$
    SELECT bit_count(val::bit(32))
    $$;
};

CREATE FUNCTION
std::bit_count(val: std::int64) -> std::int64
{
    CREATE ANNOTATION std::description :=
        'Count the number of set bits in a 64-bit integer.';
    SET volatility := 'Immutable';
    USING SQL $$
    SELECT bit_count(val::bit(64))
    $$;
};


## Bitwise bytes functions
## ----------------------

CREATE FUNCTION
std::bytes_and(a: bytes, b: bytes) -> bytes
{
    CREATE ANNOTATION std::description := 
        'Bitwise AND operator for bytes.';
    SET volatility := 'Immutable';
    USING SQL $$
    SELECT CASE 
        WHEN octet_length($1) != octet_length($2) THEN
            edgedb_VER.raise(
                NULL::bytea,
                'invalid_parameter_value',
                msg => 'bytes_and: bytes must be of equal length'
            )
        ELSE (
            WITH splits AS (
                SELECT generate_series(1, octet_length($1)) AS i
            )
            SELECT string_agg(
                decode(
                    lpad(
                        to_hex(
                            (get_byte($1, i-1) & get_byte($2, i-1))::int
                        ),
                        2,
                        '0'
                    ),
                    'hex'
                ),
                ''
            )::bytea
            FROM splits
        )
    END
    $$;
};

CREATE FUNCTION
std::bytes_or(a: bytes, b: bytes) -> bytes
{
    CREATE ANNOTATION std::description := 
        'Bitwise OR operator for bytes.';
    SET volatility := 'Immutable';
    USING SQL $$
    SELECT CASE 
        WHEN octet_length($1) != octet_length($2) THEN
            edgedb_VER.raise(
                NULL::bytea,
                'invalid_parameter_value',
                msg => 'bytes_or: bytes must be of equal length'
            )
        ELSE (
            WITH splits AS (
                SELECT generate_series(1, octet_length($1)) AS i
            )
            SELECT string_agg(
                decode(
                    lpad(
                        to_hex(
                            (get_byte($1, i-1) | get_byte($2, i-1))::int
                        ),
                        2,
                        '0'
                    ),
                    'hex'
                ),
                ''
            )::bytea
            FROM splits
        )
    END
    $$;
};

CREATE FUNCTION
std::bytes_xor(a: bytes, b: bytes) -> bytes
{
    CREATE ANNOTATION std::description := 
        'Bitwise XOR operator for bytes.';
    SET volatility := 'Immutable';
    USING SQL $$
    SELECT CASE 
        WHEN octet_length($1) != octet_length($2) THEN
            edgedb_VER.raise(
                NULL::bytea,
                'invalid_parameter_value',
                msg => 'bytes_xor: bytes must be of equal length'
            )
        ELSE (
            WITH splits AS (
                SELECT generate_series(1, octet_length($1)) AS i
            )
            SELECT string_agg(
                decode(
                    lpad(
                        to_hex(
                            (get_byte($1, i-1) # get_byte($2, i-1))::int
                        ),
                        2,
                        '0'
                    ),
                    'hex'
                ),
                ''
            )::bytea
            FROM splits
        )
    END
    $$;
};

CREATE FUNCTION
std::bytes_not(a: bytes) -> bytes
{
    CREATE ANNOTATION std::description :=
        'Bitwise NOT operator for bytes.';
    SET volatility := 'Immutable';
    USING SQL $$
    WITH splits AS (
        SELECT generate_series(1, octet_length($1)) AS i
    )
    SELECT string_agg(
        decode(
            lpad(
                to_hex(
                    (~get_byte($1, i-1) & 255)::int
                ),
                2,
                '0'
            ),
            'hex'
        ),
        ''
    )::bytea
    FROM splits
    $$;
};

CREATE FUNCTION
std::bytes_overlap(l: std::bytes, r: std::bytes) -> std::bool
{
    CREATE ANNOTATION std::description :=
        'Check if two bytes have any overlapping bits (bitwise AND is non-zero).';
    SET volatility := 'Immutable';
    USING SQL $$
    SELECT (
        CASE
            WHEN octet_length(l) != octet_length(r) THEN
                edgedb_VER.raise(
                    NULL::bool,
                    'invalid_parameter_value',
                    msg => (
                        'bytes_overlap(): bytes must be of equal length'
                    )
                )
            ELSE (
                WITH splits AS (
                    SELECT generate_series(1, octet_length(l)) AS i
                )
                SELECT EXISTS (
                    SELECT 1 FROM splits
                    WHERE (get_byte(l, i-1) & get_byte(r, i-1)) != 0
                )
            )
        END
    )
    $$;
};
