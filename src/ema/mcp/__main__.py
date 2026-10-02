"""``python -m ema.mcp --root DIR [--workspace DIR]``: run the stdio MCP server (record 0081 item 3, provisional).

The same as ``ema mcp`` (architecture.md §8): ``--root`` is required and absolute; a relative ``--workspace``
resolves against it. A root refused (``PathRefused``: relative, ``/``, or inside a workspace; T5, 0061) is a usage
error, exit 2, with the message on stderr; nothing ever goes to stdout but the protocol (T9).
"""

import argparse
import sys

from ema.types.errors import PathRefused


def main(argv: list[str] | None = None) -> int:
    """Parse the arguments and serve until the client disconnects; return the exit code (0, or 2 for a root refused)."""
    parser = argparse.ArgumentParser(prog="python -m ema.mcp", description="EMA's MCP server, over stdio.")
    parser.add_argument("--root", required=True, help="the one directory path arguments may name; absolute")
    parser.add_argument("--workspace", default="ema_workspace", help="the workspace; relative to the root")
    args = parser.parse_args(argv)
    from ema.mcp.server import serve

    try:
        serve(root=args.root, workspace=args.workspace)
    except PathRefused as error:
        print(f"ema mcp: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
