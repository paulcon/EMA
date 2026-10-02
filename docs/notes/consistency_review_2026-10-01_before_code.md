# Consistency check of the accepted specs, before the first line of code (2026-10-01)

Eight independent reviewers each read the whole set of accepted specs (`docs/design/`, the diagnostics, the
guides, the plan template, and the records as their focus needed), each going deepest on one area:
terminology, ids and cross-references, records against specs, numbers, the run path (M, G, Q/W/I), the
diagnostics (S, PT–PM, V, R), architecture with trust, export and the guides, and readiness for build step 01.
Their full reports were working files, not kept; this note merges them, and cites each finding by its
reviewer's id (TERM-1 … BUILD-13). Findings raised by one
reviewer only were checked by hand against the cited lines; the C6 point-run claim was recomputed (5 distinct
replicates become 1 after the offset).

## Outcome

A's plain errors corrected in place (0052). C answered by the owner the same day: "user"; a `seed` row for the
point run and coordinate lines; golden points as suggested. B and C became record 0061, accepted and applied. D left
to the plans named there.

Round 2 (three independent reviewers on the diff: 10, 11, and 12 findings): its plain errors corrected in place
(stale second copies, an off-by-one bound, citations, missing "amended by" marks); two of 0061's rules found
wrong (golden points "within 1 ulp" can't hold when `log` differs too; a replay that errors on a point mismatch
fails U8 on another machine), with five details for step 01, as record 0062, accepted and applied.

Round 3 (one reviewer on 0062's diff: 9 findings): plain errors corrected in place (C20's sampler version,
lines through a log range compared in unit coordinates, the reuse key's `versions` keys, the approval's
`asked_for`); 0062's unit-coordinate tolerance confirmed for the golden requests (margin about 2.8 at worst).
Three findings change 0062, drafted as record 0063 (proposed): a replay across generator versions has no design
structure to give the diagnostic (store it with the result); the rebuild check needs a per-range tolerance; and
`duration()`'s edges. 0063 accepted and applied.

Round 4 (one reviewer on 0063's diff: 7 findings, none needing a record): corrected in place (`replay_batch`
builds a replay's design; the identity's "rebuilt without today's code" reworded; `duration()`'s known answers
and its rounding on the decimal `repr`; the registry's two-version fixture; the rebuild check's wording; export
names the structure). Line budget: 0061–0063 add an estimated 173–343 lines to `architecture.md` §11's 7,940,
so 8,113–8,283 against `scope.md`'s 8,000: record 0064 raised the budget to 8,300, with §11 at about 8,200.

## Overall

- **Ids:** sound. 277 ids, each defined once with no gaps; 4,240 id citations and 1,272 record mentions all
  resolve; the decisions index matches all 60 records.
- **Numbers:** sound. Every price, design size, run count, convergent size, and mock-report number
  recomputes. Three numbers flagged at the earlier review for step 11 were never corrected (A6–A8).
- **Records:** applied well. The usual defect is a rule updated in its home but restated unchanged
  elsewhere: P3, P4, P5, P7, C11, `export.md`, and U5.
- **Real contradictions:** about ten, listed in B and C. None is large. Four touch build step 01 directly:
  the seed of unseeded diagnostics and designs (B1), how a generator is called (B2), integers vs doubles in
  hashes (B4), and the map back to unit coordinates (B8).

Counts by reviewer: TERM 10, IDS 6, REC 11, NUM 8, RUN 9, DIAG 10, ARCH 9, BUILD 13 (76 in all, about 55
distinct after merging).

## A. Plain errors (0052: corrected in place, without a record, listed in the commit message)

Applied in the working tree (uncommitted) by `fix.py`: 64 exact replacements across 20 files, each checked to
match exactly once, then the touched paragraphs rewrapped to 115 columns.

| # | File | Correction | Found by |
|---|---|---|---|
| A1 | `contracts.md` C11 | the point run's Space row holding every model parameter, no Held row (0049), not a "Point row" | TERM-4, NUM-2, REC-1, DIAG-2 |
| A2 | `principles.md` P4 | golden reports compared by structure and numbers within one unit in the 4th digit (0044), not "exactly" | BUILD-5, REC-2, DIAG-3 |
| A3 | `principles.md` P3 | "the scheduler" → the runner (`ema.runner`, AR4), three places | IDS-3 |
| A4 | `principles.md` P3 | a new run needs approval of a diagnostic evaluation's new runs, or of the test run (0049) | REC-6 |
| A5 | `principles.md` P5 | "Tested by" follows C51: replay the provenance; records differ in the field and in what it decides (0054, 0055) | RUN-2, REC-3 |
| A6 | `uncertainty.md` | `BOOTSTRAP_RESAMPLES`: each end varies by about 3% of the width, not "0.01" (recomputed: 3.0%) | NUM-3 |
| A7 | `polynomial_model.md` | hyperbolic cross at d = 8, p = 3 has 53 terms (Π(αᵢ+1) ≤ p+1), not 65 | NUM-4 |
| A8 | linear, polynomial | "8P" and "8(d + 1)" at level 2 are "about" (exact for P ≤ 237); G7's formula decides (the spec's own 14161 × 1771) | NUM-5 |
| A9 | `principles.md` P7 | the store test's exceptions add a retry of a failed run (0010), as C46 has | RUN-6 |
| A10 | `principles.md` P7 | the noisy note is on results made after the measurement; a stored earlier result is returned unchanged (C50, C52) | REC-10 |
| A11 | `export.md` | the design's identity includes the generator version (0046); `result.json` holds the full `Provenance` with run ids in design order (0055) | TERM-2, ARCH-6b, RUN-8, REC-5 |
| A12 | `export.md` E4 | R5's z is missing where b > 0.8 on `ok` runs, not b > 0.5 (the contract model's); failed runs have an empty `ema_missing` | NUM-1 |
| A13 | `use_cases.md` U5 | the CSV has one row per design row (E2), not per run | ARCH-9, REC-9 |
| A14 | `point_run.md` | R6's χ² bound 1.3603, as `reference_models.md` and `point_run.out` (two places) | NUM-6 |
| A15 | `point_run.md`, `uncertainty.md` | `POINT_RUN_MIN_RUNS` = 1, the named minimum P6 requires | NUM-7, DIAG-7 |
| A16 | `trust.md` | "§11's 500 lines": §11 says ~435; reword so the arithmetic follows | NUM-8 |
| A17 | `model_interface.md` | the model version id is the full hash; `name@` + 12 hex is its label (`data_model.md`, `model_version_label`) | TERM-1 |
| A18 | `glossary.md` | "failed run" adds 0057's cause: EMA couldn't write its own file in the run or batch directory | TERM-8 |
| A19 | `data_model.md` §8 | Q5/Q6 return `DiagnosticResult`, Q7 `RunColumns` (0056; there is no `Result` class) | ARCH-4 |
| A20 | `data_model.md`, `architecture.md` | Q13–Q15 copied in `architecture.md` and drifting: one home in `data_model.md` §8 | IDS-6 |
| A21 | `data_model.md` §9 | "each store promise cites it" is false for I1, I6, I11, I12: reword, and I1's Contract column is C49 | IDS-1 |
| A22 | `polynomial_model.md` | the progress hook is `on_progress(Progress)`, not `(done, total)` | ARCH-8 |
| A23 | `contracts.md` C49, PM10 | a rerun after an interrupt gives the same estimates; its counts and approval are the rerun's (0054) | RUN-4 |
| A24 | `contracts.md` | M21 joins M17 and M18 as the model spec's own tests | RUN-9 |
| A25 | `contracts.md` | "corrections listed in STATUS's step-7 entry" → commit 80ecf5c | REC-8 |
| A26 | `architecture.md` | bare "§3.4", "§5.12", "§10's" mean `data_model.md`'s sections: say so | IDS-2 |
| A27 | `architecture.md` AR2 | drop "(or an AST test, §10)" (0059 item 9) | BUILD-6 |
| A28 | `architecture.md` | the generator's argument `request: DesignIdentity` → `identity` ("request" is the glossary's word for something else) | TERM-2 |
| A29 | `architecture.md`, `contracts.md`, `scope.md` | "Updated" lines add 0059 | IDS-4 |
| A30 | `README.md` | the file tree lists `docs/checks/` and the consistency reviews | IDS-5, BUILD-13 |
| A31 | `designs.md` | "the 10⁻¹² is a named constant" gives no name: `SHARED_ANCHOR_TOL` | BUILD-13, DIAG-5 |
| A32 | `reference_models.md`, `shared.md` S5 | R4b gives estimates in each diagnostic that has them, not "every diagnostic" | DIAG-6 |
| A33 | `shared.md` S4, S9 | S4's test also lacks the Estimates sentence for coordinate lines; S9 exempts points drawn from computed numbers (C12) | DIAG-10 |
| A34 | `scatter.md` | `SCATTER_HIST_BINS` is ⌊√n_u⌋, as used everywhere | DIAG-10 |
| A35 | `shared.md` | every mock is a golden report except the point run's, as `point_run.md` says | DIAG-9 |
| A36 | linear, polynomial, `uncertainty.md` | the y-constant undefined cases "added here" move to the fit specs, their home (0052) | DIAG-8 |
| A37 | `docs/plans/_template.md` | checks add the docs build with `-W` and the package's lines against §11 | BUILD-12 |

## B. Decided unless the owner objects (record 0061; nothing applied until it is accepted)

Internals, per your delegation; each is my choice, with the reason.

| # | What | Choice | Found by |
|---|---|---|---|
| B1 | Design identity for unseeded kinds | `DesignIdentity.seed` holds the request's seed for every kind (0 by default; unused by point, coordinate lines, and given lines); `params` holds only what isn't already a field (no `seed`, `sampler`) | ARCH-3, BUILD-1 |
| B2 | How a generator is called | stateless: `size(identity, spec)` and `build(identity, spec, …)` only; G's tests call it through an identity; it refuses an identity of another `generator_version`, naming both. The design contract's inputs (seeded or not, nesting claimed, an example identity, one over the cap) come from a table keyed by generator name in `tests/contracts/design.py` | BUILD-1, BUILD-2, RUN-3 |
| B3 | Replay against stored points | a replay checks each rebuilt row's point hash against its run's; a mismatch is an error naming the row, never a silent "differs" | RUN-3 |
| B4 | Integers vs doubles in hashes | every value in model parameter units (nominal values, limits, range ends, held values, a point's x, anchors, directions) becomes a double when parsed, so `45` and `45.0`, or a CLI space file and its Python form, give one model version and one reuse key; integer diagnostic parameters stay integers; alpha keeps its decimal string. The run id hashes the two ids as hex text | RUN-1, BUILD-11 |
| B5 | `ema mcp` and AR1/AR3 | `ema.cli` sits in a layer above `ema.mcp` and imports `ema.mcp.server` lazily, in the `mcp` command only (it needs the `ema[mcp]` extra); AR3's text and the layers contract say so. The command stays `ema mcp` | ARCH-1 |
| B6 | The stderr tail 0057 shows | `RunInfo` gains `stderr_tail: str \| None` (in its `text`), and Q7 returns the tails beside the reasons, so `failed_runs` returns them as `trust.md` says | ARCH-2 |
| B7 | Deleting run directories without following links (T9) | one helper, `remove_tree`, in `ema.models.files`, used by `prepare` (which clears a leftover directory) and by `ema.runner`; `trust.md`'s row moves there | ARCH-5 |
| B8 | The map back to unit coordinates | `designs.md` states it: linear z = (2x − (lo + hi))/(hi − lo), log the same in ln x, clamped to [−1, 1], each end exactly ±1; fits, the shared-anchor test, and given lines' anchors use it. Amends 0047's maps | DIAG-5 |
| B9 | C6 and the point run | the point run joins C6's exceptions: 10⁶ + 10⁻³·f merges its replicates (5 distinct values → 1; computed). C5 still holds | DIAG-1 |
| B10 | A root inside a workspace (T5) | `open_workspace(root=)` raises `PathRefused`; `ema mcp` maps it at start to exit 2 | ARCH-7 |
| B11 | `result.json`'s keys | `export_format`, `design`, `spec`, `columns`, `result`; `result` is `DiagnosticResult.to_json()`'s object, so `reproduce` reads `doc["result"]` | ARCH-6a |
| B12 | `ema.types`'s standard-library list | add `re`, `keyword`, `collections.abc`, which its own checks need | BUILD-9 |
| B13 | `duration()` | one rule: under 1 min in s, under 1 h in min, else "h min" ("about 1 h 20 min"); U4's "about 80 min" written that way | BUILD-10 |
| B14 | Mock titles and model names | the golden comparison also skips the model's name (the mocks write R ids; only R2 is named, `ishigami`, and the others are named by their build steps), as it skips ids | REC-7 |
| B15 | Glossary rows | "request" without the model version (as `Request`, the canonical request, and P5 have it); "approval" and "confirmation" as the user's answer, a yes letting runs happen (declined ones are stored); "observation" covering a cell that says why there is no number | TERM-5, 6, 7 |
| B16 | Record marks | 0028 amended (a rerun's run has the same id: the data model wins); the six partial amendments REC-11 lists get their "amended by" marks | RUN-7, REC-4, REC-11 |

## C. Questions for the owner (behavior a user would notice; answered, see Outcome)

**C1. "Analyst" or "user"?** The glossary, purpose, and principles say "user"; `trust.md` (20×) and
`use_cases.md` (23×) say "analyst", and both reach generated text (the MCP instructions, "this client can't
ask the analyst"). Suggested: "user" everywhere, since the glossary uses it; "analyst" only in the use cases'
prose, never in generated text.

**C2. May `seed` be given to the point run and coordinate lines?** Every request has a seed (C8, the canonical
request, `Request.params`), but those two parameter tables have no `seed` row, so `seed=5` could be refused or
accepted and ignored; C8's check needs it accepted. Suggested: add the row, as `lines.md` has ("recorded; no
random draws; doesn't change the design"). Four reviewers found this.

**C3. Which design points are promised bit for bit, and where?** `designs.md` and 0044 promise log-range points
and random-line directions only on one machine with the same libraries; 0059 runs the checks on two Linux
setups (latest numpy on 3.14, numpy 2.1.0 on 3.13), and you develop on a Mac. Suggested: unit rows and
linear-range points bit for bit everywhere; log-range points and random-line directions within 1 ulp across
machines, and bit for bit within one (golden reports already allow the 4th digit).

## D. For later plans (no decision now)

- **BLAS determinism (BUILD-4).** STATUS's Lanczos warning extends to the linear and polynomial fits' QR, their
  1000 bootstrap refits, and the Gram coefficients' `Q.T @ y`. Single-threaded BLAS needs either an
  environment variable before numpy loads (AR2/AR7 rule that out) or `threadpoolctl` (a new dependency, a
  record). STATUS's second remedy (the exact Gram basis) contradicts `coordinate_lines.md`'s "computed by the
  Lanczos process". Measure `qr`, `lstsq`, Lanczos, and `Q.T @ y` at the polynomial model's size on this Mac
  (50 calls, in and across processes) in the `ema.numerics` plan, then propose a record if any varies.
- **Plan 01 (BUILD-7, BUILD-8):** pytest's collection of `tests/contracts/*.py` and their `check_*` functions,
  and a `slow` marker; mypy's and Ruff's exclusion of `src/ema/reference_models/` (duplicate module names), in
  the step that adds them.
- **DIAG-10d:** the linear model's per-level table prints coefficients without units (`shared.md`'s rule).
  Not checked by hand; settle it when that diagnostic's build step writes its golden report.
- **TERM-10:** `space` and `prediction` are rows of each parameter table but not `Diagnostic.parameters`; the
  example in `DiagnosticParameterInfo.type` should not say "model parameter space". Fold into B15's record.
