"""``python -m ema.mcp --root DIR [--workspace DIR]``: run the stdio MCP server (records 0081 item 3, 0086 item 11).

The same as ``ema mcp`` (architecture.md §8): ``--root`` is required and absolute; a relative ``--workspace``
resolves against it. A root refused (``PathRefused``: relative, ``/``, or inside a workspace; T5, 0061) is a usage
error, exit 2, with the message on stderr; nothing ever goes to stdout but the protocol (T9). Without the ``ema[mcp]``
extra it prints ``ema mcp``'s message, exit 2 (0086 item 11): ``EXTRA_MISSING`` mirrors ``ema.cli``'s, which this
layer may not import (AR1; a test checks the two are equal).
"""

import argparse
import sys

from ema.types.errors import PathRefused

EXTRA_MISSING = "ema mcp needs the ema[mcp] extra: uv sync --extra mcp (or pip install 'ema[mcp]')"


def main(argv: list[str] | None = None) -> int:
    """Parse the arguments and serve until the client disconnects; return 0, or 2 (a root refused; no extra; 0086)."""
    parser = argparse.ArgumentParser(prog="python -m ema.mcp", description="EMA's MCP server, over stdio.")
    parser.add_argument("--root", required=True, help="the one directory path arguments may name; absolute")
    parser.add_argument("--workspace", default="ema_workspace", help="the workspace; relative to the root")
    args = parser.parse_args(argv)
    try:
        from ema.mcp.server import serve
    except ImportError as error:
        print(f"{EXTRA_MISSING} ({error})", file=sys.stderr)
        return 2
    try:
        serve(root=args.root, workspace=args.workspace)
    except PathRefused as error:
        print(f"ema mcp: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
