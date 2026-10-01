# 0056. Make the layers architecture rules, use a Workspace object, serve figures as MCP resources, type the use cases against the workspace, add three store reads, and allow a Store per thread

**Date:** 2026-10-01. **Status:** accepted. **Resolves:** OD-16; the held candidate principle "One-way layers"
(TODO step 9).

## Context

- **"One-way layers"** has been a held candidate in `../design/principles.md` since step 1 (0007), waiting for
  `architecture.md`. P1–P7 each protect something a user sees (numbers from EMA, approvals, determinism,
  provenance); the layers protect the code. Either way, the enforcement is the same import-linter contracts,
  and 0052 gives each rule one home.
- **OD-16** asks whether the workspace is an object or module functions. Every use case types
  `ws = ema.open_workspace(...)` and calls methods on it. The workspace holds an open store and one
  long-lived child per model version (0026).
- **The MCP tools.** 0016 lists the tools ("list and describe models and diagnostics; propose a model spec and
  save it; test a model; estimate; run a diagnostic; get a diagnostic result, a report, or a figure. At most 10
  tools"), and 0053 adds export within the cap. Written as tools, that is 11: `models`, `diagnostics`,
  `propose_model`, `save_model`, `test_model`, `price`, `run_diagnostic`, `results`, `failed_runs`,
  `get_figure`, `export`. U9 already reads the report through a resource, `ema://results/{id}/report`.
- **The use cases' typed lines** are "provisional until [`architecture.md`] is accepted" (`use_cases.md`). They
  call `result.report()`, which would make a layer-0 data class render a report (layer 3a), against the rule
  that a layer imports only from below; and `ws.estimate`, which 0049 left for step 9 to name (the price).
  U9's client calls `get_result`, which the tool set above names `results`.
- **The data model** (`data_model.md` §10) names one record class per table, including `Run`, `Prediction`,
  and `Result`, which `ema.types` also needs (`Run` with its model predictions, `DiagnosticResult`); calls the
  design's JSON shape `DesignIdentity`; and leaves W6's public name to step 9.
- **P3's enforcement** says the scheduler "refuses a new run unless an approval matches its model version hash
  and point". In `data_model.md`, coverage is checked only by W4's precondition, which runs after a call is
  collected, so an uncovered run would already have run; no read returns an approval's points.
- **Missing reads.** A result's report, export (`result.json` holds "the model version's spec"), and replay need
  the spec of the result's own model version, but `data_model.md` reads `model_versions` only through a name's
  latest loading (Q3) and the listing (Q8); U6 requires "the old diagnostic result's report is unchanged". A
  replay of a deleted result (U8, C51, §9 there) needs the runs its provenance names, but Q7 reads them through
  `result_runs`, which W6 deletes, and Q9 reads one run at a time.
- **Connections and concurrent requests.** `data_model.md` §10 allows "one `Store` per process", but the MCP
  server needs a second connection so reads answer during a long run, and SQLite keeps a connection on its
  thread. Two processes with the same request can both finish their analysis and reach W5 with one result id.
- **Exceptions in the use cases.** A declined approval raises `ApprovalDeclined` and a changed file
  `ModelChanged` (`architecture.md` §7). U4's typed line declined at level 2, and U6's refused line, are
  followed by more lines, so as typed a script would stop there; C53 says each use case "runs as written".

## Decision

We will:

1. **Write "One-way layers" as architecture rules, not a principle:** AR1–AR7 in `../design/architecture.md` §1
   (one-way imports; no I/O in layers 0–1; interfaces with no logic; only the runner runs a model; only the
   store opens the database; no LLM SDK; the root package only re-exports), enforced by import-linter
   contracts and one AST test in the fast tier (and a second for standard-library imports, if import-linter
   can't see them). The candidate leaves `principles.md`; the id prefix AR joins the README (not A: P3 already
   cites "v1's bug A1").
2. **Use a `Workspace` object (OD-16):** `ema.open_workspace(path)` returns it; its methods are the front door
   (`architecture.md` §7); it is a context manager, and `close()` stops the model children.
3. **Serve figures as MCP resources:** `ema://results/{id}/figures/{name}.png` and `.json` (its data card),
   beside the report's resource. The 10 tools are `models`, `diagnostics`, `propose_model`, `save_model`,
   `test_model`, `price`, `run_diagnostic`, `results`, `failed_runs`, and `export`.
4. **Type the use cases against `architecture.md` §7:** `print(x.report())` becomes `print(ws.report(x))`;
   `estimate` becomes `price`; U9's `get_result` becomes the `results` tool; the typed steps are no longer
   provisional.
5. **Give the data model's classes one home:** the store returns `ema.types`'s `Run` (its model predictions
   folded in, for §10's `Run` and `Prediction`), `DiagnosticResult` (§10's `Result`), `MeasuredNoisy`, and
   `DesignIdentity`; `records.py` holds the store's other rows. W6 (`delete_result`) has no public name in
   v2.0.
6. **Add three store reads:**
   - Q13 `approval_coverage(approval_id, keys)`: the approval's model version and answer, and which of one
     call's keys it covers and has no run for yet, by key lookups (`approval_points`' primary key, the runs'
     unique key); the runner reads it before every
     call and refuses a key it doesn't cover; W4's precondition stays as the second check;
   - Q14 `model_version(model_version_id)`: its spec and tracked files;
   - Q15 `runs_by_id(run_ids)`: the runs, in the order given, with their model predictions.
7. **Write the exceptions into the use cases:** U4's declined level-2 line and U6's refused line become
   `try: … except ema.ApprovalDeclined:` and `except ema.ModelChanged:`, so the steps run as written (C53).
8. **One `Store` per thread,** in place of one per process (the MCP server holds two), and **W5 on a result id
   already stored writes nothing and returns the stored result.**

## Alternatives considered

- **"One-way layers" as P9:** citable as a principle, with the same enforcement; not chosen, since it protects
  maintainers rather than anything a user sees, and its one home is the architecture spec.
- **Dropping "One-way layers":** the contracts would remain as configuration with nothing to cite.
- **Module functions (OD-16):** no object to keep, but every call reopens the store and restarts model
  children, and every use case's typed lines change.
- **Merging `propose_model` into `save_model`:** keeps `get_figure` a tool, but the agent can't preview a spec
  without asking the analyst, and U9's calls change.
- **Dropping the `price` tool:** keeps `get_figure`, but the agent can't learn a price without asking for an
  approval; 0016 listed it.
- **Folding `failed_runs` into `results`:** one tool with two jobs and two shapes of result, harder for an agent
  to call correctly.
- **Returning `None` from a declined `run`:** no exception in U4, but every caller must check for `None`, and a
  script that forgets fails later and less clearly.
- **Checking coverage only in W4:** no new read, but P3's "refuses a new run" would hold only after the run.
- **A comment naming the exception in U4 and U6:** shorter, but a script still stops at the line, so the use
  case wouldn't run as written.
- **`result.report()` on a workspace-layer wrapper:** keeps the use cases' line, but adds a second result type
  beside `DiagnosticResult`, and printed ids would need the workspace anyway (shortest unique prefixes, Q11).

## Consequences

- **`../design/architecture.md`:** §1 (AR1–AR7), §5 (Q13–Q15, one `Store` per thread), §7 (the object, the
  names, W5 on a stored id), §8 (the tools and resources), §12.
- **`../design/principles.md`** (accepted): the candidate "One-way layers" is removed; P2's "`architecture.md`
  §11" becomes §10, which says P2's contract is added with `ema.experimental` (none in v2.0, 0017).
- **`../../README.md`:** the id prefix AR, "architecture rule", defined in `docs/design/architecture.md`.
- **`../design/use_cases.md`** (accepted): `print(result.report())` → `print(ws.report(result))` in U1 and U2,
  `print(r1.report())` → `print(ws.report(r1))` in U3, `print(p.report())` and `print(r.report())` likewise in
  U7; U1's "`estimate` exists for an analyst who wants the price" → "`price` exists …"; the asks' "`estimate`" →
  "`price`"; U4's `r3 = ws.run(…, level=2, …)` inside `try: … except ema.ApprovalDeclined: pass  # declined:
  no runs made`, and U6's refused `ws.run(…)` inside `try: … except ema.ModelChanged as e: print(e)`; U9's
  `get_result` → `results`; the introduction's "so they are provisional until that spec is
  accepted" and U7's sentence on `run`'s signature go.
- **`../design/data_model.md`** (accepted): §2 and §8 gain Q13 (which of one call's keys an approval covers and has no run for yet, for which
  model version: the runner, before each call), Q14 (a model version's spec and tracked files, by its id:
  `report`, export, `reproduce`), and Q15 (runs by id, in the order given: every run batch, and `reproduce`);
  §2's Q7 is asked by export and `failed_runs`, and Q7 and Q15 return `ema.types.RunColumns`, with no object
  per row; W5 on a result id already stored writes nothing and returns the stored result (two identical
  requests at once, I7); §6: a result directory already in place with a row is kept, and the new temporary one
  discarded; I9 is enforced by `read_batch`'s order (Q15) as well as Q7's `ORDER BY row`; §10:
  one `Store` per thread that uses it (the MCP server holds two) in place of "one `Store` per process",
  `records.py` holds the store's own rows rather than one class per table, the Read-by column gains Q13
  (`approvals`, `approval_points`, `runs`), Q14 (`model_versions`), and Q15 (`runs`, `predictions`), and the
  table names
  `ema.types.Run` (for `Run` and `Prediction`), `ema.types.DiagnosticResult`, `ema.types.MeasuredNoisy`, and
  `ema.types.DesignIdentity`, and adds `Coverage`; W6's "a public name is step 9's" → "no public name in
  v2.0".
- **`../design/contracts.md`** (accepted): C53–C55 provisional until the guides (step 13) only;
  "`architecture.md` §10" → §9 (three places: the contract list, the workspace section, and the asks); C54's
  Generalizes, "the held principle 'One-way layers'", → AR3.
- **`../design/model_interface.md`** (accepted): the opening note says `architecture.md`'s stubs follow this
  spec.
- **0016's status,** in the record and in `README.md`'s index row: "accepted; its live evals amended by 0050
  (later); its tool list amended by 0053 (export) and 0056 (figures as resources)".
- **`../../STATUS.md`:** OD-16 moves to "Decided", naming this record.
- **Harder later:** an eleventh tool needs a record raising the cap, or another merge; an MCP client whose agent
  can't read resources shows figures only when the analyst attaches them.
