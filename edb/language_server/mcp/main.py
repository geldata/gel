from mcp.server import FastMCP
import click

from .code_examples import code_examples


mcp = FastMCP("gel-mcp")


@mcp.resource("code://list-examples")
async def list_code_examples() -> list[str]:
    """List all available code examples and their slugs"""
    return [f"{e.slug}: {e.description}" for e in code_examples]


@mcp.resource("code://{slug}")
async def fetch_code_example(slug: str) -> str | None:
    """Fetch a code example by its slug"""
    return next((e for e in code_examples if e.slug == slug), None)


@click.command()
@click.option("--version", is_flag=True, help="Show the version and exit.")
@click.option(
    "--stdio",
    is_flag=True,
    help="Use stdio for LSP. This is currently the only transport.",
)
def main(*, version: bool, stdio: bool):
    mcp.run()


if __name__ == "__main__":
    main()
