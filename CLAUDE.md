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
  record 0007).
- **Tests first.** For a new module, write its contract checks and known-answer tests from the spec, show
  them to me, then write the code.
- **One step at a time.** Each build step has a plan in `docs/plans/`, numbered from 01. Stop at the plan's stop
  condition and wait for review.
- **Size budgets** (`docs/design/scope.md`) are constraints. Going over one is a decision to propose, not
  something to drift into.
- **Update `STATUS.md`** at the end of each step, in the same commit as the work.

## Git

- **Commit only when I ask.** Write a detailed message: what changed and why, the ids it implements, and any
  file ported from v1.
- **One branch per build step** (`build-NN-topic`), from `main`; design steps (TODO 1–13) commit on `main`. I
  decide merges.
- Never push, tag, or change a remote without asking.

## v1

- v1 is at `../EMA-v1` (tag `v1-final`). It is **reference only**: read it when a plan says to, and never copy
  code from it unless the plan names the file to port. Name the source in the commit message ("Ported from
  EMA v1 at v1-final: src/ema/core/models/_sandbox.py").
- v1 is also an independent source of numbers: running it on a reference model, with the same seed, checks a
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

## Commands

> Records 0059 and 0084 (the fast tier with `-n auto`). Python 3.13 and newer; develop on 3.14.

- Install: `uv sync`
- Fast tier, with the import contracts (after every edit): `uv run pytest -q -n auto && uv run lint-imports`
- Full tests (before reporting a step done): `uv run pytest -q --slow -n auto`
- Lint (before reporting a step done): `uv run ruff check && uv run ruff format --check && uv run mypy`
- Docs (before reporting a step done): `uv run sphinx-build -W --keep-going docs docs/_build/html`
- GitHub Actions (`checks.yml`) runs only when I start it.

## Where things are

- Specs: `docs/design/`. Decisions: `docs/decisions/`. Plans: `docs/plans/`. Status: `STATUS.md`.
- Architecture, layers, and each module's public names: `docs/design/architecture.md`.
- Glossary: `docs/design/glossary.md`. Use its words in code, docs, and messages.

## Secrets

`.env` holds API keys. Never read, print, or commit it. Models never receive it (M2 in
`docs/design/model_interface.md`; T2 in `docs/design/trust.md`).
