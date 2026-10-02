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
