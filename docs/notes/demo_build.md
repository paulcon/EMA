# Demo build log (2026-10-01 onward)

> The coordinating session's log of the autonomous build on the `demo` branch (record 0066): the waves, each
> step's record, and each review round's findings and fixes. A note, not a spec.

## Goal

A working demo of EMA through its MCP server (`ema mcp --root DIR`, U9) by the end of 2026-10-02: an MCP client
loads a reference model, is shown the price, approves, runs the diagnostics, and reads the report with its
figures.

## Waves

Steps are the roadmap's (`docs/notes/build_roadmap.md`), with T added (0066 item 2). Steps in one wave are built
at once, in worktrees on `demo-NN-<topic>`, and merged into `demo`.

| Wave | Steps | Records |
|---|---|---|
| 1 | 01 scaffolding and designs; 02's first task (BLAS determinism, measured beside it) | 0067; 02a in 0068 |
| 2 | 02 numerics; 03 model specs and loading; T the rest of `ema.types` | 0068; 0069; 0070 |
| 3 | 04 and 05 running a model (command line, then Python); 06 the store; 08 figures and reports | 0071; 0072; 0073 |
| 4 | 07 runner and approval; 09 diagnostics base, the point run, and the reference models | 0074; 0075 |
| 5 | 10 scatter; 11 coordinate lines and lines; 12 linear model; 13 polynomial model | 0076; 0077; 0078; 0079 |
| 6 | 14 the workspace | 0080 |
| 7 | 15 the MCP server; 16 the CLI | 0081; 0082 |
| 8 | 17 the demo, guides, and a last review | 0083 |

## Rounds

Each wave's review rounds: the findings (counted by severity), what was fixed, and what was left, with why.

### Wave 1

- **Step 01, review round 1** (independent agent, on 7727695): 0 blockers, 1 major, 8 minor, 10 nits; all
  checks green; G7, G12, G13 recomputed independently and agreeing; every broken toy failing for its reason;
  31 mutants, 26 killed. Major: convergent's `size()` hangs on a large level near alpha 1 (a request could hang
  the MCP server). Minor: a float seed crashing random lines; non-canonical identities (handed to step 09); the
  far-end face rule untested; the meta-test accepting any exception; the sampler hash check a tautology; a
  lines block costing the whole design; `size()` accepting what `build()` refuses; the size budget (the
  coordinator's: a budget record after wave 2's counts). Fixing round 1 started.
- **BLAS determinism** (02's first task): QR, lstsq, and matrix products bit-for-bit repeatable on Accelerate;
  the Lanczos process varies through `np.linalg.norm` (a 1-D dot product whose bits depend on memory
  alignment). Adopted in step 02 (record 0068): `dot` and `norm` through `np.sum`, banned 1-D BLAS calls, an
  alignment test.

### Wave 2

- **Step T** built (683e90c on `demo-T-types`): 128 new tests; `ema.types` at about 1,304 code lines. Review
  round 1 started.
- **Step T, review round 1** (on 683e90c): 0 blockers, 2 major, 10 minor, 6 nits; ids, C17's round trip, the
  shown text, and the counts' invariants verified independently. Major: the provenance's JSON forms held the run
  ids that `data_model.md` §5.9 and §5.12 keep in their own columns (a 10⁷-row design would pass SQLite's
  limit); `Reproduction` named the replayed result's id, not the original's. Fixing round 1 started.
- **Step 02** built (778cd84 on `demo-02-numerics`): 148 tests; the scatter mock report reproduced through the
  numerics to four digits; 341 code lines against 553; v1's `core/legendre.py` ported. Review round 1 started.
- **Step 03** built (f28b3c6 on `demo-03-model-specs`): 224 tests; a fuzz of 8,000 one-field spec mutations
  raised only `SpecError`; about 665 lines against the roadmap's 450. Review round 1 started.
- **Step 02, review round 1** (on 778cd84): 0 blockers, 0 major, 5 minor, 5 nits; every number recomputed
  independently and agreeing (Legendre, R7's rates in exact arithmetic, PRESS, Sobol, the binned index, the
  scatter mock report's 16 bounds within 1.1e-16). Minor: gaps in the no-vector-BLAS enforcement (`x @ y`,
  `.dot`, `vecdot` uncaught; the fits' test without power); `Bootstrap.settings` not encodable; Sobol indices
  on a constant y unguarded; the rank-from-R rule untested; 0035's second half untested. Fixing round 1
  started.
- **Step 03, review round 1** (on f28b3c6): 0 blockers, 2 major, 9 minor, 8 nits; the version hash recomputed
  independently from `data_model.md` §3.4 on 7 specs and agreeing; about 40 refusal probes (paths, links to
  credentials files, hidden characters, environment) holding. Major: credentials-file names not refused on
  `writes` and a parser's `file` (ruled: follow `model_interface.md`'s broader wording, refuse them); names that
  aren't NFKC-stable or ASCII failing as keyword arguments and template names after runs are paid for (ruled:
  ASCII identifiers, a provisional clarification in 0069). Minor: the case probe one directory too high, the
  spec's path not resolved, aliases refused, a FIFO hanging EMA, stray exception types, no frozen version-hash
  answer, `writes` collisions compared by case. Fixing round 1 started.
- **Step 01, fixing round 1:** M1 fixed (n_min + L over the cap refused at once; each size from a float estimate
  checked against a guard, exact fixed-point bounds otherwise; sizes equal to the exact rule over 17 alphas, 9
  n_min, and 3,000 levels; record 0067 item 31, which departs from `designs.md`'s "computed in exact rational
  arithmetic" in method only); m1, m3, m4, m5, m8 and every nit fixed; m2 fixed in convergent, the rest handed
  to step 09; m6 fixed for coordinate lines' 0051 check, a block's line segments deferred (1–2 h). Round 2
  review started.
- **Fixing round 1** for 02 (2840bbe), 03 (22b8781), and T (277752f): every blocker, major, and minor fixed but
  the size budget (the coordinator's); 03's majors ruled as above. Merged on `demo-wave2` (ea087eb), with
  conflicts in `identity.py` (both sides kept) and AR1's layers resolved; 1,090 tests pass, every check green.
  Round 2 review of the merged wave started.

### Wave 3

- Started from `demo-wave2` (ea087eb): steps 04 and 05 together (`demo-04-models`), 06 (`demo-06-store`), 08
  (`demo-08-reports`).
- **Wave 2, review round 2** (merged, ea087eb): 0 blockers, 0 major, 4 minor, 6 nits; the merge lost nothing; the
  column forms, the cross-checks (point runs, all-failed results, repeated runs, replays), and 03's refusals
  verified. Wave 2 done. Carried forward: m1 (a result's own measured-noisy `made_at`) ruled for step 06 (None
  inside a result; the table keeps it); m3 (library calls such as `np.cov`, `pearsonr` vary with alignment too)
  goes into step 09's diagnostic contract as a whole-`compute` alignment check, with more banned names; m2 (a
  caller's earlier writable view) documented as a limit; m4 the size budget record (the coordinator's).
- **Step 01, review round 2** (e148069): 0 blockers, 0 major, 3 minor, 3 nits; convergent's sizes against an
  independent high-precision reference on about 70,000 requests (adversarial near-integers included): 0
  mismatches; every meta-test pinned to its toy's reason. Step 01 done. Minors carried to a cleanup pass: an
  alpha text with a huge exponent stalls the request; the float path's precision and the exact refinement
  untested.
- **Step 08** built (6684ad9): all six mock reports rebuilt by hand and matched; 660 lines against 540. Review
  round 1 started.
- **Step 06** built (a8d3a85): every W and Q; the store contract with 13 broken toys; 1,103 lines against 715;
  Q1's 10⁶-point timing target deferred (about 20–25 s now; a key-only read for the runner, 1–2 h). Review round
  1 started.

### Wave 4 (started early)

- **Step 09** started from step 08's branch (`demo-09-diagnostics`), since it needs the reports but not the
  store or the runner; it carries the hand-offs: canonical identities (0067), a whole-`compute` alignment check
  in the diagnostic contract (0068), and step 08's result conventions (0073).
- **Cleanup pass** (waves 1–2's remaining minors): a huge alpha exponent read lazily and refused at once;
  the float path pinned against an 80-digit reference with a negative control; `_power_bounds` and the
  refinement tested; more banned library calls (`np.cov`, `pearsonr`, …) and `__matmul__` in the AST test; the
  wave 2 nits. Records 0067 (39–41), 0068, 0070 (28–30).
- **Step 08, review round 1** (6684ad9): 1 blocker, 3 major, 9 minor, 4 nits; rebuilds byte-identical after
  every round trip; PNGs identical across processes; no interpretation found. Blocker: the coordinate-lines
  Design row indexed varied-only unit coordinates by all model parameters (a crash with a held parameter
  first). Major: the user's rcParams reaching figures (`text.usetex` read `/etc/hosts` through a label;
  margins changed the data cards), and the PDF reader keeping TeX math (T10's second guard missing). Fixing
  round 1 started.
- **Step 06, review round 1** (a8d3a85): 0 blockers, 2 major, 5 minor, 8 nits; the lock (same Store, second
  Store, subprocess, SIGKILL), round trips (−0.0, subnormals), Q1's construction, and SQL safety verified.
  Major: two processes writing one result at once raised raw OS errors and leaked temporary directories
  (18 of 260 attempts); W5 let an approval's runs be split across results or cited by another request (I12).
  Fixing round 1 started.
- **Steps 04 and 05** built (3cc811a): the model adapter contract C31–C45 over Python, batch, and command-line
  toys with 15 broken toys; 1,210 lines of `ema.models` against 1,323; v1's `_sandbox.py` and `_worker.py`
  ported after re-review. Review round 1 started. The fast tier is near its 30 s budget (about 25 s under load).
- **Step 07** started (`demo-07-runner`, from `demo` with 04 and 06 merged, 3c26723), before 06's fixes land.

### Waves 3 and 4, later rounds

- **Step 06, fixing round 1** (d9affd4): both majors (the directory race: rename-only under BEGIN IMMEDIATE,
  4-process test; an approval tied to one result of its own request with every approved run used, three new
  broken toys) and every minor fixed; `current_keys` added for the runner. Round 2 review comes with wave 3's
  merged review.
- **Step 08, fixing round 1** (c895bec): the blocker, the three majors, and every minor fixed, each test shown
  failing on the old code; `lines_through_anchor` shared by the generator and the report. Round 2 with wave 3's
  merged review.
- **Steps 04+05, review round 1** (3cc811a): 0 blockers, 2 major, 6 minor, 11 nits; the environment (T2), stdout
  (T9), exact doubles, malicious replies, and the v1 port verified; the contract 8 of 8 runs green under load.
  Major: a Ctrl-C landing inside `Popen` leaked the program (21 of 40 tries); `pidfd_open` without a fallback on
  old Linux. Fixing round 1 started.
- **Fixing round 1** for 04+05 (9ef9b89): both majors (Ctrl-C held around `Popen` and re-delivered; pidfd
  fallback) and every minor fixed; a proposed M20 amendment (a finished program's group is killed) in 0071.
- **Step 07** built (0ce0886): runner and approval; the runner's contracts with broken toys; 364 lines against
  418. **Step 09** built (760584a): the diagnostic base and contract (C1–C19, with each compute at 8 memory
  offsets), the point run, the reference models (v1's ishigami and borehole ported, bit-identical to v1).
- **Merged into `demo`:** 04, 06, 08, 07, 09 (conflicts only in `pyproject.toml`'s import contracts and
  `docs/index.md`; AR1's layers set to 3b over 3a over 2 over 1 over 0). 1,635 tests pass; every check green.
  The fast tier takes 40–46 s serially, 19 s with `-n auto`: record 0084 (proposed) runs it in parallel and
  measures the size budget at the end (7,560 lines so far).

### Wave 5 (with step 14 alongside)

- Started from `demo` (a2e8226): 10 scatter, 11 coordinate lines and lines, 12 linear model, 13 polynomial model,
  and 14 the workspace (diagnostic-agnostic; it needs only the base), each in its own worktree. Reviews started
  on `demo`: step 07 (round 1), step 09 (round 1), and round 2 of 04+05, 06, 08, with an end-to-end probe.
- **Step 07, review round 1** (a2e8226): 0 blockers, 2 major, 6 minor, 5 nits; P3's paths (declined, another
  model version, a batch past the approved count, files changed, the cap at a call's start), pricing per
  distinct key, and the question's text (T7) verified. Major: a key already run under another approval could
  run again from a stale resolution (unreachable through the workspace's lock-then-resolve, but the runner is
  the one place that checks); a Ctrl-C right after W4's commit deleted stored runs' directories. Fixing round 1
  on `demo-07fix`.
- **Step 09, review round 1** (a2e8226): 0 blockers, 2 major, 5 minor, 5 nits; every point-run known answer and
  reference model recomputed and agreeing; counts, notes, refusals, and identities verified. Major: the point
  run's mean and standard deviation rounding for a constant value (a nonzero standard deviation for a
  deterministic model); the contract's batch builder deciding failures per row, not per run (coordinate lines'
  shared anchor broke C2). The builder's fix is handed to step 11's agent; the rest is fixing round 1 on
  `demo-09fix`.
- **Steps 04+05, 06, 08, review round 2** (merged, a2e8226): 06 and 08 done (round-1 fixes correct; W5 refused
  no valid case among nine tried: retries, test runs, interrupted evaluations, all-failed models, R8); 04+05's
  round-1 fixes correct but two new bugs (a 64 MiB reply cap too small for large batch calls, a major; `poll`'s
  timeout overflow). A point run went end to end through runner → store → diagnostics → report → W5 in a
  scratch script; its seams sent to step 14's agent. Fixing on `demo-wave3fix` (the cap, the overflow, a lock
  around styled drawing for the MCP server's two threads, W6's directory removal).
- **Step 07, fixing round 1** (fb0ad25, merged): both majors and every minor fixed (a key already run cut from
  the call; Ctrl-C after a commit keeps the runs; `current_keys` in `resolve`); its round 2 comes with the
  final integrated review.
- **Step 09, fixing round 1** (merged, acfed84): the point run's moments from replicate 0 (exact for a
  constant); decimal text kept as written; plain-text notes; C2, C6, C10 tightened; −0.0 kept distinct from 0.0
  per `data_model.md` §3.4. The four diagnostic agents and the workspace agent told of the tightened checks.
- **Step 10** built and merged (scatter; the mock reproduced to every printed digit). Review round 1 started.
- **Step 14** built and merged (the workspace; an evaluation end to end in §7's order). On merged `demo`, C53's
  U1, U6, U7, U8 pass with scatter; U2–U5 wait for coordinate lines and the linear and polynomial models.
  Review round 1 started.

### Wave 7 (started early)

- 15 the MCP server and 16 the CLI, from `demo` at the workspace's merge, in parallel; the seam between them
  fixed by the coordinator: `ema mcp` calls `ema.mcp.server.serve(root=..., workspace=...)`.
- **Step 11** built and merged (coordinate lines and lines; both mocks matched; R8 through the runner; the
  contract's batch builder per run). U2 passes on `demo`. Review round 1 started.
- **Step 12** built and merged (the linear model; the mock matched exactly). Review round 1 started. The
  bootstrapped diagnostics make the fast tier slow (about 2,000 fits per bootstrap); to settle at the end.
- **Round-2 fixes** for 04, 06, 08 merged (the reply limit scaled with a batch; waits capped at 60 s; a drawing
  lock for two threads; W6 under its transaction). Steps 04+05, 06, 08 done. Left for the final cleanup: under
  load averages of 30–67, the model contract's 0.25 s `TIMEOUT_S` and a 2 s timing test in designs fail
  intermittently (pass alone).
- **Step 14, review round 1** (04b3217): 0 blockers, 1 major, 5 minor, 6 nits; §7's order, the lock's release on
  every path, C50, two Workspaces on two threads (one holding the lock while its approver waits, the other
  pricing and reading), byte-identical drawing from two threads, replay, export verified. Major: T5 — a linked
  spec's files checked against the link's directory, letting a model file outside the root through
  `save_model`/`load_model`. Fixing round 1 on `demo-14fix`; the MCP agent told that a Workspace is bound to its
  thread.
- **Step 10, review round 1**: 0 blockers, 0 major, 3 minor, 3 nits; every known answer and all 16 mock
  interval ends recomputed independently (within 4.4e-16); `reduceat` deterministic across processes and
  offsets. Step 10 done. Minors to the diagnostics' cleanup pass: a parameter named `Histogram` colliding with
  the histogram on a case-insensitive disk; the one-usable-run figures untested; the fast tier's bootstrap cost.
- **Step 11, review round 1**: 0 blockers, 0 major, 1 minor, 3 nits; R7's rates at n = 17 and 33, R3's k* and
  rates, given and random lines, constant lines, and R11 recomputed in exact arithmetic and agreeing; C6's
  exemption of k* and rates confirmed by contracts.md's own wording. Step 11 done. To the cleanup pass: a test
  of the cells' precedence (constant line with runs not usable, and three more paths); C6's skip limited to
  named diagnostics.
- **Step 12, review round 1**: 0 blockers, 0 major, 7 minor, 4 nits; the mock's every value and 12 interval
  ends, and the known answers at 20,000 runs, recomputed independently; figures byte-identical under a user's
  rcParams and from 12 threads. Step 12 done. To the cleanup pass: units kept in the per-level cells' JSON;
  tests for the rank-deficient and LOO-undefined notes; the LOO note's wording; a lean interval method in the
  contract's checks that don't need the real bootstrap (the fast tier's cost: about 30 s of CPU per
  bootstrapped diagnostic).
- **Step 16** built and merged (the CLI, 13 commands, C54's check that each prints its workspace call's text;
  `ema mcp` importing the server lazily). One test fixed at the merge (it assumed only two diagnostics).
  Review comes with step 15's.
- **Step 13** built and merged (the polynomial model; the mock matched with zero differences; C29's deferred
  clause closed). All six diagnostics are now on `demo`. C18 at d = 20 missed its 60 s under load averages of
  20–150 (134 s alone); to re-time on a quiet machine. Review round 1 started.
- **All use cases on merged `demo`** (edf68e3): `pytest --slow tests/contracts/workspace.py`: 28 passed, 0
  skipped (U1–U8, the get-started guide, C54 over 15 CLI forms).
- **Step 14, fixing round 1** merged: the T5 hole closed (a linked spec's files checked beside its real path,
  before anything is read), concurrent rebuilds safe through the store's move-aside, `reproduce` never raising,
  no FIFO hang, a Workspace bound to its thread with an `EMAError`, C49's figures and C51 tested. Step 14 done
  (its round 2 with the final integrated review).
- **Step 15** built and merged (the MCP server; AR3 split into one contract for the CLI and one for the server;
  8 import contracts kept). Checked by the coordinator: `ema mcp --root ~/ema_demo` answers `initialize` and
  lists the 10 tools; a real MCP client over stdio priced and ran a scatter with one elicitation (the price and
  what each run starts), read the report resource, and a repeat asked nothing. The demo directory
  `~/ema_demo` set up per `docs/notes/demo_mcp.md` §1 (three models loaded with `ema model add`). Found:
  `save_model` refuses an existing spec file given its own text ("exists, with other text"), so a client can't
  load an existing spec; sent to the review.
- **Diagnostics cleanup** merged (the lean interval method in the contract: 36 s → 15 s; the minors of 10–12).
- Review of 15 and 16 started; step 13's review running.
- **Step 13, review round 1**: 0 blockers, 1 major, 7 minor, 6 nits; every mock number and interval end, the 45
  coefficients and their intervals recomputed independently; `dtrtrs` bit-identical to `solve_triangular` and
  offset-invariant. Major: C18 at d = 20 takes about 114 s against `D20_SECONDS` = 60 (its CPU cost suggests it
  misses idle too; contracts.md's 19 s counted only the as-drawn refits). Fixing round 1 on `demo-13fix`, with
  one sampler reader for the three diagnostics and one home for `SPECTRUM_YMIN`.
- **Steps 15 and 16, review round 1** (merged `demo`): 0 blockers, 2 major, 5 minor, 10 nits; P3 and T5 held
  under every probe (malformed and late answers, cancels, disconnects, two concurrent runs; every path argument
  and resource traversal); T9 held with a model writing to fd 1. Major: the docs' index left broken by the merge
  (fixed with step 13's fixes); `save_model` can't load a hand-written spec, and `tools.md` says it can (ruled:
  load when the existing file renders to the same text; reword `tools.md`). The approval form's `approve`
  defaults to checked (ruled; pressing Accept on the priced form is the yes).
- **Step 13, fixing round 1** merged: C18's bound measured and set to 180 s (both refits; LAPACK's time); one
  sampler reader; `basis`'s plain "no" with C14 tightened; the exact V = 0 fixture; the docs build passes.
- **Steps 15 and 16, fixing round 1** merged: a hand-written spec loads through `save_model` after a yes (file
  unchanged); the form's `approve` checked by default; SIGTERM handled; reserved `params` names refused; a
  malformed elicitation reply a no at once; cancel, disconnect, and SIGTERM tested over stdio; `tools.md`
  reworded. Checked again on a scratch copy of the demo root by the fixing agent. Lint, 8 import contracts,
  mypy, and the docs build pass on `demo`.
- **The whole suite on final `demo`** (ebeef8a): fast tier `-n auto` 2,016 passed, 61 skipped (slow tests) in
  61 s with the final review loading the machine; `--slow -n auto` 2,076 passed, 1 skipped (the point run's C6
  exemption), 0 failed, in 5 min. 10,957 code lines (record 0084, for the owner). Final integrated review and
  demo rehearsal (step 17) running.

- **Step 17, final integrated review and rehearsal**: 0 blockers, 1 major, 6 minor, 8 nits. All 13 prompts of
  `docs/notes/demo_mcp.md` ran over stdio in 12.5 s (the scatter of 200 in 4 s), with the doc's texts and ids;
  resources byte-identical; 55 PNGs valid; one result id for one request in three fresh workspaces;
  `reproduce` identical for six results; every diagnostic run once through MCP; no advice in any text (0017).
  Major, fixed by the coordinator: `tools.md` didn't say every model parameter and prediction needs a
  description, so prompt 11's draft was refused twice (now said, and the prompt asks for descriptions). Minor,
  fixed in the doc: a repeated run's line repeats the stored counts ("200 new"), so the presenter says nothing
  ran (no form, same id). The others are listed under "How to resume" as the owner's questions. Demo ready.

- **After the owner's rehearsals (2026-10-02, evening)**, each from what a rehearsal showed, each proposed in record
  0081: the server asks the client not to interpret (item 27); a repeated request's line says it is the stored
  result (28); loading refuses a spec whose parameters the function doesn't take (29); the PDF's figures fit the
  page (30); `export` can add the report's PDF (31); a model's description shows its runs' settings (32). The demo:
  a real beam model with a hand-written spec, preloaded; prompts 10 and 14 dropped (12 prompts). The owner ran
  the demo through Claude Code and it worked as expected.

- **The owner accepted records 0066–0085 (2026-10-02, night)**, with 0084's budget raised to 11,000 (55c8ae6).
  Four agents then applied the records' "Spec edits on acceptance" in place on `demo`, each owning its files:
  `architecture.md`; the data/model/trust group (data_model, trust, model_interface, export, use_cases, scope,
  principles, glossary, purpose, the guides, README, CLAUDE.md); the contracts/diagnostics group (contracts,
  uncertainty, designs, reference_models, diagnostics/*); and record 0085's code (`src/`, `tests/`).

- **Data/model/trust group applied** (model_interface, trust, data_model, export, use_cases, scope, principles,
  CLAUDE.md, two guides). For the review: left unapplied (no record names them): glossary, purpose, README (still
  says "there is no code yet"); 0069's questions for the owner (a name starting with "-"; ordering files and
  pass_env); 0081's elicitation details only in `architecture.md` §8, not trust.md; `--pdf` not in the
  run-a-diagnostic guide. Inconsistencies found: U2's transcript line vs `ResultSummary.make`'s text; the guides'
  approval-question lines vs 0074 item 11's text; a T10 test cell added from 0073 item 2 (confirm); U4 updated for
  0085 though 0085 doesn't name use_cases.

- **`architecture.md` applied** (§1–§12; §11 at 0084's final counts, 10,957 of 11,000). For the review:
  inconsistencies found: `Stopped` not retryable though its docstring says a rerun reuses the runs; the registries'
  `get` raising different errors on an unknown name (`RequestError` for the four seams, `NotFound` for
  diagnostics, `KeyError` for parsers); 0082 vs 0081 on AR3's shape (the code has two contracts; followed);
  0073 item 11's PDF reader without `-implicit_figures` (code and 0081 item 30 have it; followed); private modules
  imported across packages (`ema.types._values`, `ema.numerics._vector`) against 0080 item 24 / 0069 item 37's
  rule; `python -m ema.mcp` documented as kept. Not applied: 0073 item 18's interim §11 numbers (superseded by
  0084); the D20 bound (contracts.md's).

- **Contracts/diagnostics group applied** (contracts, uncertainty, designs, reference_models, the seven diagnostics
  specs; the mocks now carry 0073's and 0085's edits). For the review: `shared.md` says "Markdown with TeX math"
  while 0073 item 11 says the report writes no math (drop "with TeX math"?); the tests' now-no-op mock
  replacements (sent to the 0085 code agent); `polynomial_model.md`'s 2026-09-30 interval-width measurement
  counted the relative residual and R²; C18 runs in the fast tier on the degree-1 example request, the defaults
  at d = 20 in the slow tier.

- **Record 0085 in the code:** both fits' in-sample relative residual and R² are observations (level L of the
  per-level table), with the record's line in that table's title; every remaining interval bit-identical before
  and after (242 estimates over 8 evaluations, and two permanent tests); golden tests against the raw mocks. For
  the review: `polynomial_model.md` says R1's intervals are "about 10⁻¹⁵" wide, but the LOO error's reaches
  1.5·10⁻¹⁰ at 2P = 30 runs (leverages near 1); the specs may say the line sits in the per-level table's title.
- All checks pass on the combined changes (fast tier 2,042 passed; lint, mypy, 8 import contracts, docs).

- **Review of the applied records, round 1** (four fresh reviewers: `architecture.md`; the data, model, and trust
  specs; the contracts and diagnostics specs; 0085's code): 0 blockers, 2 major (both budgets: 11,034 source lines
  against 11,000, counted by §11's rule; the fast tier at 61–68 s against 30 s), 20 minor, 25 nits. The plain ones
  fixed in place (37: the pandoc reader's `-implicit_figures` in T10; U2's and the guides' approval and result
  lines as the code prints them; README on `demo`; C18's tiers; the exact fits' interval widths at the fewest runs,
  measured; "no math" in `shared.md`; `lines`' `m` default text; LM7's and R5's tests over the observations; stale
  docstrings; Depends-on lists). The 14 that need a choice went into record 0086 (proposed).
- **Round 2** (two reviewers on round 1's diff and on 0086): 0 blockers, 1 major (round 1's text said the root
  re-exports `Stopped`; it doesn't), 6 minor, 15 nits, fixed in place but one (Q3's sort, the store's choice, left); 0086's facts corrected (0081
  items 28–32, not 29–32; the acceptance commit 55c8ae6). The measured interval widths confirmed by the reviewer.
- **Record 0086 answered by the owner** in an interview, item by item: the source-line budget 12,000; the fast tier
  90 s, 30 s a goal; a model's name starting with a letter or digit; `files` and `pass_env` sorted before hashing;
  hard line breaks in the "Runs not usable" note; no record ids in text users see; 0085's line kept always;
  `relative_residual` in both fits; the version raised when a diagnostic's output changes (2.0.0.dev1);
  `Stopped` not retryable; `python -m ema.mcp` kept, the missing extra handled; private modules private to EMA;
  the preamble line for package-local names; `designs.md`'s added detail kept. Status proposed until the owner
  accepts it; then its spec edits and code are applied, and the demo root's results recomputed.

## How to resume (if the session stops)

State lives in git and on disk; nothing is only in the conversation.

1. `git worktree list` and, in each worktree under `../EMA-worktrees/`, `git status --short` and
   `git log --oneline -3`. A worktree with uncommitted changes was being built or fixed when the session stopped:
   run its checks (`uv run pytest -q && uv run lint-imports && uv run ruff check && uv run mypy`); if green and
   its plan/record look complete, commit it; otherwise hand it to a new agent with its plan
   (`docs/plans/NN-*.md`) and record, saying "finish this step".
2. The last entries in "Rounds" above say which step is at which stage (built, in review, fixing). A step whose
   fixing round is committed but not re-reviewed gets a round-2 review.
3. **Next:** the review of the applied records is done (rounds 1 and 2 above).
   Record 0086 is answered; once the owner accepts it, apply its spec edits and code (its Consequences), run every
   check, review the change once, and recompute the demo root (`docs/notes/demo_mcp.md`'s setup).
4. What is left is the owner's: review `demo` and records 0066–0084 (each lists its spec edits on acceptance),
   and decide on merging into `main`. Open questions from the final review, for the owner: the shared notes'
   "Most frequent reasons" list renders as one line in CommonMark, and the notes name Python calls
   (`ws.failed_runs`) that an MCP reader can't use (both spec wordings in `shared.md`); the spread row says |y|
   whatever the model prediction's name; `lines`' `m` has no default in its JSON schema; parameter meanings show
   record ids such as "(0032)".
- **After the rehearsals (owner's decision, 2026-10-02):** a model spec is written by hand for the demo; drafting
  one through MCP (`propose_model`, `save_model`, U9) stays in the product (option (a): the tools keep the human in
  the loop through the save form, and loading now checks the function's signature, record 0081 item 29) but isn't
  demonstrated. The demo's beam model is a hand-written spec, `docs/notes/demo/beam.json`, beside `beam.py`, loaded
  with the other three in setup; prompt 11 now runs it (a point run and a scatter, with units). `~/ema_demo` reset
  to that starting state, four models loaded.
