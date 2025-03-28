from typing import Any, Optional

class Entry:
    key: str
    key_vars: list[str]
    variables: dict[str, Any]
    substitutions: dict[str, tuple[str, int, int]]

    def tokens(self) -> list[tuple[Any, int, int, int, int, Any]]: ...

def rewrite(operation: Optional[str], text: str) -> Entry: ...
