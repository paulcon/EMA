# 0087. Settle three follow-ups from applying record 0086

**Date:** 2026-10-03. **Status:** accepted (2026-10-03, by the owner). **Resolves:** none.

## Context

Record 0086 was accepted and applied on `demo`. An independent review of the change found three points that 0086
doesn't decide; the owner answered each.

## Decision

1. **The model's description shows `files` and `pass_env` as the first loading of its model version wrote them.**
   0086 item 4 sorts them in the hashed form only, and says the description shows them "as written". The store
   keeps one spec per model version, the first loading's (`data_model.md` §3.4), so a later loading that only
   reorders them is the same model version and is described in the first loading's order (`describe_model`'s
   `spec`, the first approval's lists; the description's text shows neither). `model_interface.md` says so; no
   code change. Put: say "as first loaded"; store the order per loading.
2. **No ids of any kind in text users see:** 0086 item 6's rule covers spec ids too (P, U, M, G, S, V, C, Q, W, I,
   T, E, R, AR, and the like), in the same texts: the parameters' meanings, the MCP server's instructions and
   descriptions, and the messages and lines a user can cause (about 15 today: "(G9)", "(P3)", "(T5)", "(W1)",
   "(U9)", "(C55)", and others in the runner, the evaluation's lines, and export's column descriptions). The specs'
   Parameters tables cite them outside the Meaning column; docstrings, comments, tests, and the errors only a
   programming error raises keep them. `tests/unit/test_record_ids.py` checks both kinds. Put: no ids of any kind;
   keep spec ids.
3. **A workspace made before `2.0.0.dev1` is rebuilt, not read:** a stored spec whose lists are out of order has an
   id the store no longer recomputes, and a stored name like `-x` is refused when its spec is read back. Only
   development workspaces exist; a development version has no migration. `data_model.md` (§11, the schema's
   versions) says so. The demo root's workspace is moved aside and rebuilt. Put: rebuild and say so; migrate;
   refuse them through the schema version.

## Alternatives considered

Listed with each item ("Put:").

## Consequences

- Spec edits on acceptance: item 1, `model_interface.md` (Versions); item 2, the diagnostic specs' Parameters
  tables where a Meaning cell holds a spec id, and `docs/design/diagnostics/_template.md`; item 3, `data_model.md`
  §11.
- Code: item 2's strings (no code lines added) and the test's pattern.
- The demo root: `~/ema_demo/ema_workspace` and `exports/` moved aside, the four models loaded again
  (`docs/notes/demo_mcp.md`).
