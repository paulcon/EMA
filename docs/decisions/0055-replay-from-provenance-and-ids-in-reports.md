# 0055. Replay a diagnostic result from a provenance that survives its deletion; write ids in reports at a fixed length; correct 0054's example

**Date:** 2026-10-01. **Status:** accepted. **Resolves:** none (an independent review of the draft
`../design/data_model.md`, after 0054).

## Context

- **0054's example is wrong.** Its item 1 says that after `r4`, `r3`'s request gives a new result from the
  retries. But `r4` is `r3`'s request with `retry_failed`, which is not part of the request. So after `r4`,
  `r3`'s request resolves to `r4`'s runs, has `r4`'s reuse key, and returns `r4`'s stored result, with `r4`'s
  header counts (34 new, 266 reused). The rule is right; only the example is wrong. The example that shows it
  is `r1` (n = 200): its request again after `r4` resolves to retries at its failed points, and gives a new
  result.
- **0054's item 4** says to replay "the stored provenance". After `delete_result`, the provenance is no longer
  stored, so P5's test ("delete a stored diagnostic result, rerun it from its provenance and the stored runs")
  and U8's ("a deleted diagnostic result is recomputed identical from its provenance") have nothing to replay.
  A later result's notes also read a point run's measured-noisy record, which goes when that point run's result
  is deleted.
- **Ids in reports.** Showing an id by its shortest unique prefix, which grows as a workspace grows, would
  make a report rebuilt later differ from the first (P1's test, S10). Reports hold a diagnostic result's id
  (`ws.failed_runs("3f2a")`, `shared.md`), a point run's (`point_run.md`'s note), and an approval's (the
  Provenance line). The mocks show 4 hex digits, which would collide at about 300 diagnostic results.
- **"Reuse key"** is new in 0054 and C50's wording, and has no glossary row.

## Decision

We will:

1. **Correct 0054's example:** after `r4`, `r3`'s request returns `r4`'s stored result; `r1`'s request gives a
   new result, from stored runs, with the retries at its failed points. 0054's rule is unchanged.
2. **Replay a diagnostic result from its `Provenance`, not from the store's copy of it.** The `Provenance`
   that `get_result` returns, and that an export's `result.json` holds, includes the ids of the runs used, in
   design order, and each measured-noisy record read, in full. `reproduce` and C51's check replay from it and
   the stored runs; `delete_result` keeps every run, so a deleted result can be replayed.
3. **Write ids in reports at a fixed length:** a diagnostic result's or an approval's id as its first 12 hex
   digits (a model version, as always, as `name@` and 12). Data cards and exports hold ids in full. The CLI,
   the MCP server, and printed summaries show the shortest unique prefix of at least 4 hex digits, and accept
   any unique prefix of at least 4. The mock reports' 4-digit ids stay as placeholders: golden reports don't
   compare ids (0044).
4. **Add a glossary row** for "reuse key".

## Alternatives considered

- **Keep a deleted result's provenance in the store** (a "deleted" mark, or a table of tombstones): replay
  from the store alone, but deletion then isn't deletion, and the store gains an updated row or a table.
- **Refuse to delete a point run's result that later results read:** simpler replay, but deletion gets a rule
  that depends on other results.
- **Shortest unique prefixes in reports:** shorter ids, but a report changes as the workspace grows.
- **Full ids in reports:** never ambiguous, but 64 hex digits in a note or a Provenance line.

## Consequences

- **0054's status:** "accepted; its example and item 4 amended by 0055".
- **`../design/contracts.md`** (accepted; C46–C56 provisional): C51's "deleting a result and replaying its
  provenance" (0054) reads "deleting a result and replaying the provenance it had (from `get_result` or an
  export)".
- **`../design/diagnostics/shared.md`** (accepted): Numbers adds "Ids are written as their first 12 hex digits
  (a model version as `name@` and 12); the mocks' shorter ids are placeholders."
- **`../design/glossary.md`** (accepted): a row for **reuse key**: "what makes a request a repeat: its model
  version, the request, the runs its design resolves to, and EMA's and the libraries' versions; a request whose
  reuse key has a stored diagnostic result gets that result (C50, 0054)". Standard terms: cache key.
- **`../design/data_model.md`:** §3.4 (ids shown), §5.9 and §5.11 (provenance holds the run ids and the
  measured-noisy records), §9 (replay).
- **`../design/architecture.md`** (step 9): `Provenance` holds the run ids and the measured-noisy records
  read; `reproduce` takes a result id or a `Provenance`.
- **`../design/use_cases.md`:** unchanged; U8's "recomputed identical from its provenance" now has a
  provenance to recompute from.
