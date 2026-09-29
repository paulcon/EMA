# EMA v2

> Keep this file under about 1,500 words: it is loaded into every session. Put explanations in
> `docs/design/`, and point to them from here.

EMA runs diagnostics on computational models to find exploitable structure, and reports the results with
figures, numbers, and their intervals. Purpose: `docs/design/purpose.md`. Scope of this version:
`docs/design/scope.md`. The repository holds design documents only until the first build step; the order of
work is `TODO.md`, and where things stand is `STATUS.md`.

## Working rules

- **Build only from accepted specs.** Each file in `docs/design/` has a status line. If the spec for the task
  is `draft`, or silent or unclear on something the task needs, stop and ask. Don't decide for me.
- **Decisions are recorded, not assumed.** Before changing anything an accepted spec says, check
  `docs/decisions/`. If the change needs a new decision, draft a decision record with status `proposed`, and
  don't make the change until I accept it. Only I set a record to `accepted`.
- **Cite ids.** Docstrings, tests, and commit messages name the ids they implement (P3, M2, C5, W3, I4,
  D0007).
- **Tests first.** For a new module, write its contract checks and known-answer tests from the spec, show
  them to me, then write the code.
- **One step at a time.** Each step has a plan in `docs/plans/`. Stop at the plan's stop condition and wait for
  review.
- **Size budgets** (`docs/design/scope.md`) are constraints. Going over one is a decision to propose, not
  something to drift into.
- **Update `STATUS.md`** at the end of each step, in the same commit as the work.

## Git

- **Commit only when I ask.** Write a detailed message: what changed and why, the ids it implements, and any
  file ported from v1.
- **One branch per step** (`step-NN-topic`), from `main`. I decide merges.
- Never push, tag, or change a remote without asking.

## v1

- v1 is at `../EMA-v1` (tag `v1-final`). It is **reference only**: read it when a plan says to, and never copy
  code from it unless the plan names the file to port. Name the source in the commit message ("Ported from
  EMA v1 at v1-final: src/ema/core/models/_sandbox.py").
- v1 is also an independent source of numbers: running it on a sample model, with the same seed, checks a
  v2 diagnostic. Use v1's own virtual environment (`../EMA-v1/.venv`), never v2's.
- v1's lessons learned are in `docs/notes/v1/`. Notes there are background, not specs.

## Costs and installs

- **Anything that calls a paid API** (live agent evals, live tests) runs only when I ask. Before running, give
  an estimate of its cost; afterwards, report what it actually cost.
- **Installing third-party software** (simulators, system packages): plan it as staged steps for me to run,
  with a stop condition for each, rather than installing it yourself.

## Principles

> One line each; the full text, the reason, and the enforcement are in `docs/design/principles.md`.

- P1 Numbers come from EMA: every number a user sees is computed from stored runs; no LLM makes one.
- P2 Results first: diagnostic results hold no interpretation; any is labeled experimental, kept apart.
- P3 Everything that decides a run is hashed; every new run is priced and approved before it runs.
- P4 Deterministic: the same request and runs give the same diagnostic result; every random draw is seeded.
- P5 Every diagnostic result records its provenance.
- P6 No data, no estimates; tolerances are relative to a model prediction's range, so units change no note.
- P7 Noise is explicit: a model is deterministic unless its spec says noisy or repeats measure it.
- P8 The glossary's words, in code, docs, and messages; never the words in its Avoid column.

## Commands

> Fill in once the tooling is chosen (OD-17, OD-18).

- Install: `<uv sync>`
- Fast tests (after every edit): `<uv run pytest -q>`
- Full tests (before reporting a step done): `<uv run pytest -q --slow -n auto>`
- Lint: `<uv run ruff check>`
- Layers: `<uv run lint-imports>`
- Docs: `<…>`

## Where things are

- Specs: `docs/design/`. Decisions: `docs/decisions/`. Plans: `docs/plans/`. Status: `STATUS.md`.
- Architecture, layers, and each module's public names: `docs/design/architecture.md`.
- Glossary: `docs/design/glossary.md`. Use its words in code, docs, and messages.

## Secrets

`.env` holds API keys. Never read, print, or commit it. Model programs never receive it (T<…> in
`docs/design/trust.md`).
