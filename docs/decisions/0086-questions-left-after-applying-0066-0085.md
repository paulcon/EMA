# 0086. Settle the questions left after applying records 0066–0085

**Date:** 2026-10-02. **Status:** accepted (2026-10-03, by the owner; each item answered in an interview, 2026-10-02).
**Resolves:** none.

## Context

The owner accepted records 0066–0085 (55c8ae6), and their "Spec edits on acceptance" were applied (f012505). An
independent review then checked the edits against the records, the specs against each other, and both against the
code: one fresh reviewer per area in round 1 (`architecture.md`; the data, model, and trust specs; the contracts and
diagnostics specs; record 0085's code), then two on round 1's fixes in round 2 (`docs/notes/demo_build.md`, after
"The owner accepted records 0066–0085"). The plain errors were corrected in place. What was left needed a choice
that no accepted record makes, including two budgets, which `CLAUDE.md` says are decisions, not drift. The owner
answered each item in an interview, one at a time; each item below gives the question, the options put, and the
answer.

## Decision

### Budgets

1. **The source-line budget is 12,000** (`scope.md`). `architecture.md` §11 and `scope.md` gave 10,957 lines, 43
   under 11,000 (0084). The code has 11,034, counted by §11's rule (no docstrings, comments, or blank lines; the
   same counter gives 10,957 at the commit 0084 counted). The lines came after that count, from 0081 items 28–32
   (`models/spec.py` +57 for the signature check; `report/pdf.py` +7; `workspace` +16, items 28, 31, and 32;
   `cli` and `mcp` +3) and 0085 (−6). The code was already at 11,040 when the owner set 11,000 (55c8ae6), so that
   budget was chosen against a count that was out of date. Put: 11,100; keep 11,000 and cut 34 lines; another
   number. **The owner chose 12,000,** room for this record's code and the fixes before v2.0 without another
   budget record.
2. **The fast tier's budget is 90 s wall-clock with `-n auto`, with 30 s kept as a goal for a later step**
   (`scope.md`). 0084 item 5 measured 41.5 s and 67.6 s with every wave merged and left the budget to the end of
   the build; the end-of-build measurement (0084 item 6) settled only the source lines. Measured after round 1's
   fixes, three runs in a row on this Mac (8 cores, no other agent running): 61, 68, and 66 s wall (2,042 passed,
   62 skipped), with 240–275 s of CPU; a fourth, by a reviewer, 56 s. No test dominates: the longest take
   3–5.5 s (the polynomial model's R5 and units tests, C7's determinism checks, the bootstrap's determinism
   tests, the MCP server's stdio tests). The CPU time alone is about 34 s per core, so 30 s can't be met
   without moving more than half the tier to the slow tier, out of the loop that runs after every edit. Put:
   90 s with 30 s as a goal; move tests to the slow tier until 30 s holds; keep 30 s, written as exceeded.

### Behavior users see

3. **A model's name starts with a lowercase letter or a digit:** `[a-z0-9][a-z0-9_-]*` (was `[a-z0-9_-]+`, 0069).
   `-rf` or `--help` loaded, and `ema model test -rf` then read the name as an option; figure and diagnostic
   names already need a letter or digit first. Loading refuses such a name with the rule in its message. Put:
   letter or digit first; keep the rule; a letter first (refusing `3d-plate`). (0069, Questions for the owner.)
4. **`files` and `pass_env` are sorted before hashing,** `files` by path and `pass_env` by name, in the hashed
   form only; the spec file and the model's description show them as written. Listing the same files or the
   same variables in another order was a new model version, its runs not reused and its first approval asked
   again, though no order changes what a run does. Only a spec whose lists are out of order gets a new id; no
   reference model's or demo model's spec has either list. Put: sort both; keep them as written; sort
   `pass_env` only. (0069, Questions for the owner.)
5. **The "Runs not usable" note's lines each end in a hard line break** (a trailing `\`) but the last, in the
   report's Markdown only; the stored note is unchanged. Its later lines rendered as one paragraph in
   CommonMark and in the PDF (lazy continuation lines; `report/render.py` `_note`), so the reasons and their
   counts ran together. 0075 item 9 gives the note's text and line breaks, not how they render. The counts'
   alignment is lost either way. Put: hard breaks; a nested list; leave it.
6. **No record ids in text users see:** the parameters' meanings (`info()`, `ema diagnostic describe`, the MCP
   tools' JSON schema) and the messages a user can cause (loading, requests, the CLI and the MCP server), for
   example "the sampler (0032)." and "a batch function takes one positional argument, the points' array (0025)".
   The diagnostic specs' Parameters tables, whose Meaning column is the code's text, drop the ids from that
   column and cite the record elsewhere in the row. Docstrings, comments, tests, and errors that only a
   programming error raises (`ValueError`) keep theirs. A test checks the meanings and the messages for an id.
   Put: no ids in text users see; the meanings only; keep them.
7. **0085's line stays under every per-level table,** as now. It also prints where the result has no
   leave-one-out interval to point to (too few usable runs for estimates, no fit, an undefined leave-one-out
   error, estimates not allowed; a constant prediction too, in the polynomial model, whose linear model writes
   no per-level table then, 0078 item 3); its first clause, why the in-sample measures have no interval, holds
   in every case, and the notes say why there is no estimate. Put: always; only with the leave-one-out
   estimate; a shorter line without it.
8. **The per-level row of the relative residual has the key `relative_residual` in both fits** (the polynomial
   model's was `rel_residual`). Since 0085 that row is the measure's only place in a result's JSON. Done now,
   before v2.0 and before the demo root is rebuilt. Put: one key; leave them.
9. **EMA's version is raised whenever a change alters a diagnostic's stored or printed output,** starting with
   `2.0.0.dev1` for 0085 and this record's items 5, 6, and 8. A result's provenance and reuse key hold the version
   (0062), so a reproduce of an older result (U8) then names the version difference, and a repeated request
   computes the result again instead of returning the older one. Under `2.0.0.dev0` a pre-0085 result
   reproduced with differences and no version line, and a repeated request returned it, old intervals and all.
   Put: raise it, as a rule; raise it once now; leave it and note it.
10. **`Stopped` stays not retryable** (`architecture.md` §3). Its docstring says a rerun reuses the stored runs,
    which argued for retryable, as `ApprovalDeclined` and `WorkspaceBusy` are. The owner's reason: the caller
    chose to stop, so trying again isn't what they want; the flag is about failures that may pass. Put:
    retryable; not retryable.
11. **`python -m ema.mcp` is kept** (0081 item 3 left it to the owner), no longer provisional. Without the
    `ema[mcp]` extra it prints the same message as `ema mcp` and exits 2, instead of an `ImportError`'s traceback.
    `docs/notes/demo_mcp.md` uses it. Put: keep it, with the missing extra handled; keep it as it is; remove it
    (and change the demo's setup).

### The specs' detail

12. **`_values` and `_vector` are private to EMA, not to their package** (`architecture.md` §2, one sentence):
    `ema.types._values` is read by layers 0–1 and by `ema.diagnostics.base`, which no record allowed;
    `ema.numerics._vector` by every computation (0067 item 8, 0068). No code change. Put: the sentence; make the
    two public; re-export the names they give.
13. **`architecture.md` lists what other packages use:** its preamble says that constants and helpers only their
    own package (and its tests) use aren't listed. About 25 such names weren't, for example `Precheck` and
    `NOTE_MAX_REASONS` (`diagnostics/base.py`), `READER` (`report/pdf.py`), `TOOLS` (`mcp/server.py`), and
    `SCHEMA_VERSION` (the store); none is used outside its package. Put: the preamble line; list them all;
    prefix them with `_`.
14. **`designs.md` keeps the detail added from 0067** (items 12, 21, 22, 25, 31, 33, 39): the refusals users can
    meet, the maps' clamps, and how convergent sizes are computed (a float path, fixed-point bounds, the 80-digit
    reference), though 0067 asked for no spec edit. So the spec describes the size computation fully, and a
    reviewer can check the code without reading 0067. Put: keep the refusals and clamps and point to 0067 for the
    sizes; keep all; remove all.

## Alternatives considered

- **Decide these in the review's fixing rounds:** each is a choice no accepted record makes, and two are budgets;
  the working rules leave them to the owner.
- **One record per item:** fourteen small records for one review's leftovers; one record, accepted as a whole,
  is easier to review. The options put for each item are listed with it.

## Consequences

- Spec edits on acceptance:
  - item 1: `scope.md` (Source lines, 12,000) and `architecture.md` §11 (the rows recounted at the commit that
    applies this record; at f012505: types 2,167; numerics 390; designs 586; models 1,420; store 1,235; plotting
    and report 715; runner, approval, and root 488; diagnostics 2,276; workspace 931; cli and mcp 826);
  - item 2: `scope.md` (Fast test tier) and `contracts.md` (Test tiers);
  - item 3: `model_interface.md` (the name's rule), and the glossary if it gives the pattern;
  - item 4: `model_interface.md` and `data_model.md` (what the model version hashes);
  - item 5: `shared.md` (the note's form in the report);
  - item 6: the diagnostic specs' Parameters tables; `CLAUDE.md`'s "Cite ids" if it needs the exception said;
  - item 8: `polynomial_model.md` (its per-level keys, if named, and its mock's JSON if shown);
  - item 9: `architecture.md` (where the version is set, and the rule);
  - item 11: `architecture.md` §8;
  - items 12 and 13: `architecture.md` §2 and its preamble.
  Items 7, 10, and 14 change nothing.
- Code: items 3, 4, 5, 6, 8, 9, and 11 change code, each by a few lines, with tests: item 3 one pattern and a
  refusal test; item 4 a sort in the hashed form, and a test that reordering keeps the id; item 5 `_note`, and
  the golden reports; item 6 five meanings and the messages, with a test; item 8 one key, its tests and mocks;
  item 9 `pyproject.toml`; item 11 `__main__.py` and a test.
- Items 4, 5, 6, 8, and 9 change stored or printed bytes (item 4 only for a spec whose lists are out of order),
  so the demo root's results are recomputed after them (`docs/notes/demo_mcp.md`'s setup).
- Item 1's count moves with every code change: the commit that applies this record recounts.
