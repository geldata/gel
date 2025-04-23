import typing

class SyntaxError(Exception): ...

class ParserResult:
    out: typing.Optional[CSTNode | list[OpaqueToken]]
    errors: list[
        tuple[
            str,
            tuple[int, typing.Optional[int]],
            typing.Optional[str],
            typing.Optional[str],
        ]
    ]

    def pack(self) -> bytes: ...

class Hasher:
    @staticmethod
    def start_migration(parent_id: str) -> Hasher: ...
    def add_source(self, data: str) -> None: ...
    def make_migration_id(self) -> str: ...

unreserved_keywords: frozenset[str]
partial_reserved_keywords: frozenset[str]
future_reserved_keywords: frozenset[str]
current_reserved_keywords: frozenset[str]

class Entry:
    key: bytes

    tokens: list[OpaqueToken]

    extra_blobs: list[bytes]

    first_extra: typing.Optional[int]

    extra_counts: list[int]

    def get_variables(self) -> dict[str, typing.Any]: ...
    def pack(self) -> bytes: ...

def normalize(text: str) -> Entry: ...
def parse(
    start_token_name: str, tokens: list[OpaqueToken]
) -> tuple[
    ParserResult, list[tuple[type, typing.Callable]]
]: ...
def suggest_next_keywords(
    start_token_name: str, tokens: list[OpaqueToken]
) -> tuple[list[str], bool]: ...
def preload_spec(spec_filepath: str) -> None: ...
def save_spec(spec_json: str, dst: str) -> None: ...

class CSTNode:
    production: typing.Optional[Production]
    terminal: typing.Optional[Terminal]

class Production:
    id: int
    args: list[CSTNode]

class Terminal:
    text: str
    value: typing.Any
    start: int
    end: int

class SourcePoint:
    line: int
    zero_based_line: int
    column: int
    utf16column: int
    offset: int
    char_offset: int

    @staticmethod
    def from_offsets(
        data: bytes, offsets: list[int]
    ) -> list[SourcePoint]: ...

    @staticmethod
    def from_lines_cols(
        data: bytes, lines_cols: list[tuple[int, int]]
    ) -> list[SourcePoint]: ...

def offset_of_line(text: str, target: int) -> int: ...

class OpaqueToken:

    def span_start(self) -> int: ...
    def span_end(self) -> int: ...

def tokenize(s: str) -> ParserResult: ...
def unpickle_token(bytes: bytes) -> OpaqueToken: ...
def unpack(serialized: bytes) -> Entry | list[OpaqueToken]: ...
