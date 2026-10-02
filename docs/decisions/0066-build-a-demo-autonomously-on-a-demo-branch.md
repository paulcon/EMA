# 0066. Build an MCP demo autonomously on a `demo` branch, recording provisional decisions

**Date:** 2026-10-01. **Status:** proposed (provisional: applied on the `demo` branch without the owner's
review, by the owner's instruction of 2026-10-01). **Resolves:** none.

## Context

The owner needs a working demo of EMA through its MCP server by the end of 2026-10-02, and has no time to answer
interview questions or review each step. The owner asked (2026-10-01) for a process that executes the build
steps as planned (`docs/notes/build_roadmap.md`), but, instead of waiting on the owner's review, makes reasonable
choices, records them, reviews each phase's code with an independent agent, fixes what the review finds, records
the revisions, iterates the review until its findings are minor, and moves on; the demo is built on a `demo`
branch, and nothing is committed to `main`.

## Decision

We will:

1. **Branch.** Build on `demo`, from `main` at 9044b4b. Steps that can run at once are built on temporary
   branches `demo-NN-<topic>` (git worktrees) and merged into `demo` by the coordinating session. Nothing is
   committed to `main`, pushed, or tagged.
2. **Waves.** Run the roadmap's steps in dependency order, in parallel where the layers allow
   (`docs/notes/demo_build.md` lists the waves). One change to the roadmap's order: the rest of `ema.types`
   (`runs.py`, `results.py`, `requests.py`, `summaries.py`) is built in one step (T) right after step 01, so the
   store, the reports, and the diagnostics can be built at once.
3. **Plans.** Each step writes its plan in `docs/plans/NN-<topic>.md` from the template, with status
   "in progress (demo)", and builds tests first from the accepted specs, as `CLAUDE.md` says. The Review A stop
   and the end-of-step stop are replaced by an independent review.
4. **Provisional decisions.** Where a spec is silent, unclear, or in conflict, the step's agent chooses, and
   lists the choice in its plan's "Choices made here". Each step's choices are collected in one record per step
   (0067 onward), with status `proposed (provisional)`. Accepted specs are not edited on `demo`; a choice that
   would change one says so in its record, for the owner to accept (and apply) or reject.
5. **Deferrals.** What a step leaves out to meet the deadline (for example, the lowest-versions job, slow
   tiers, PDF output) is listed in its plan's Notes and its record, with what it would take to add.
6. **Reviews.** After each wave is merged, a fresh agent that did not write the code reviews each step against
   its specs (correctness, contracts, P1–P7, the layers); a fixing agent fixes the findings; the review is rerun
   until its findings are minor. Each round's findings and fixes are appended to `docs/notes/demo_build.md`.
7. **Commits.** The coordinating session commits each step on `demo` after its review, citing the ids, the
   record, and any file ported from v1, and updates `STATUS.md` in the same commit.

## Alternatives considered

- **Keep the owner's review at each stop:** not possible in the time.
- **A thin vertical slice outside the plans:** faster, but discards the specs' contracts and leaves code that
  the build steps would have to redo.

## Consequences

- Records 0066 onward are proposed, not accepted; the owner reviews them, and the `demo` branch, after the demo.
  Merging `demo` into `main` is the owner's decision.
- Specs may lag the code where a provisional decision changes them; each such record names the spec edit.
