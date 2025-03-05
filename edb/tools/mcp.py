import sys
import click

from edb import buildmeta
from edb.tools.edb import edbcommands


@edbcommands.command("mcp")
@click.option("--version", is_flag=True, help="Show the version and exit.")
@click.option(
    "--stdio",
    is_flag=True,
    help="Use stdio for MCP. This is currently the only transport.",
)
def main(*, version: bool, stdio: bool):
    # import language_server only if we are using this command
    # otherwise this breaks when pygls is not installed
    from edb.language_server.mcp.main import mcp

    if version:
        print(f"gel-mcp, version {buildmeta.get_version()}")
        sys.exit(0)

    mcp.run()
