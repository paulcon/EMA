"""EMA's MCP server (layer 5; architecture.md §8; records 0016, 0019, 0056, 0057, 0081).

Needs the ``ema[mcp]`` extra. ``ema.mcp.server.serve(root=..., workspace=...)`` runs it over stdio; ``ema mcp --root DIR``
starts it (``ema.cli`` imports it lazily; AR3, 0061), as does ``python -m ema.mcp --root DIR`` (0081 item 3). This
package imports nothing at import, so ``import ema.mcp`` needs no SDK.
"""
