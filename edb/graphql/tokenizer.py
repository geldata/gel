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

from __future__ import annotations
from typing import Any, Optional, Sequence

import hashlib
import struct

from graphql.language import lexer as gql_lexer

from edb import _graphql_rewrite as graphql_rewrite  # type: ignore


def deserialize(
    serialized: bytes,
    text: str,
) -> Source:
    match serialized[0]:
        case 0:
            text = serialized[1:].decode('utf-8')
            return Source(text, serialized)
        case 1:
            entry = graphql_rewrite.unpack(serialized)
            assert isinstance(entry, graphql_rewrite.Entry)
            return NormalizedSource(entry, text, serialized)

    raise ValueError(f"Invalid type/version byte: {serialized[0]}")


class Source:
    def __init__(
        self,
        text: str,
        serialized: bytes,
    ) -> None:
        self._cache_key = hashlib.blake2b(serialized).digest()
        self._text = text
        self._serialized = serialized

    def text(self) -> str:
        return self._text

    def cache_key(self) -> bytes:
        return self._cache_key

    def variables(self) -> dict[str, Any]:
        return {}

    def substitutions(self) -> dict[str, Any]:
        return {}

    def tokens(self) -> Optional[list[Any]]:
        return None

    def first_extra(self) -> Optional[int]:
        return None

    def extra_counts(self) -> Sequence[int]:
        return ()

    def extra_blobs(self) -> list[bytes]:
        return []

    def extra_formatted_as_text(self) -> bool:
        return False

    def extra_type_oids(self) -> Sequence[int]:
        return ()

    def serialize(self) -> bytes:
        return self._serialized

    @staticmethod
    def from_string(text: str, operation_name: Optional[str]=None) -> Source:
        return Source(text=text, serialized=b'\x00' + text.encode('utf-8'))

    def __repr__(self):
        return f'<edgeql.Source text={self._text!r}>'


class NormalizedSource(Source):
    def __init__(
        self,
        # TODO: type it?
        normalized: Any,
        text: str,
        serialized: bytes,
    ) -> None:
        self._text = text
        self._cache_key = normalized.key.encode('utf-8')  # or hash?
        self._tokens = normalized.tokens(gql_lexer.TokenKind)
        self._variables = normalized.variables
        self._substitutions = normalized.substitutions

        self._first_extra = (
            normalized.num_variables if normalized.substitutions else None
        )
        self._extra_counts = (len(normalized.substitutions),)
        self._serialized = serialized

    def text(self) -> str:
        return self._text

    def cache_key(self) -> bytes:
        return self._cache_key

    def variables(self) -> dict[str, Any]:
        return self._variables

    def substitutions(self) -> dict[str, Any]:
        return self._substitutions

    def tokens(self) -> Optional[list[Any]]:
        return self._tokens

    def first_extra(self) -> Optional[int]:
        return self._first_extra

    def extra_counts(self) -> Sequence[int]:
        return self._extra_counts

    def extra_blobs(self) -> list[bytes]:
        out = b''
        # Q: Or should we use `variables` instead and reencode it?
        # (We'd need to use a DecimalEncoder.)
        # I think the token encodings in substitutions are legit json?
        # N.B: This relies on the substitutions being in the right order.
        for v, _, _ in self._substitutions.values():
            ev = b'\x01' + v.encode('utf-8')
            out += struct.pack('!I', len(ev))
            out += ev

        return [out]

    @staticmethod
    def from_string(text: str, operation_name: Optional[str]=None) -> Source:
        rewritten = graphql_rewrite.rewrite(operation_name, text)
        return NormalizedSource(rewritten, text, rewritten.pack())
