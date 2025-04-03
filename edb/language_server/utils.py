from lsprotocol import types as lsp_types

from edb.edgeql import tokenizer


# Convert a Span to LSP Range
def span_to_lsp(source: str, span: tuple[int, int | None]) -> lsp_types.Range:
    (start, end) = tokenizer.inflate_span(source, span)
    assert end

    return lsp_types.Range(
        start=lsp_types.Position(
            line=start.line - 1,
            character=start.column - 1,
        ),
        end=lsp_types.Position(
            line=end.line - 1,
            character=end.column - 1,
        ),
    )
