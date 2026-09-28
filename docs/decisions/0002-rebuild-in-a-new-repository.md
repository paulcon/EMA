# 0002. Rebuild v2 in a new repository; keep v1 for reference

**Date:** 2026-09-28. **Status:** proposed (the owner decided to rebuild on 2026-09-28; this record awaits
acceptance of its wording). **Resolves:** OD-1.

## Context

v1 was built in seven days: about 28,000 source lines, 12 diagnostics, 26 agent tools, and 36 design rules
in a 7,400-word CLAUDE.md (`docs/notes/v1/lessons_learned_2026-09-27.md`). Its core ideas held up, but its
scope and structure outran review. The alternatives were:
- refactor v1 in place, removing its experimental layers and restructuring its store and tools;
- rebuild alongside v1 in the same repository;
- rebuild in a new repository.

Claude Code reads what is in the repository it works in: the code, CLAUDE.md, and its per-directory memory.
Both packages are named `ema`.

## Decision

We will rebuild EMA as v2 in a new repository, from written specs, porting v1 code only file by file when a
plan names it.

- **The directory `~/PycharmProjects/EMA` and the GitHub repository `pauls-code-projects/EMA` become v2's.**
- **v1 moves to `~/PycharmProjects/EMA-v1`** and GitHub `pauls-code-projects/EMA-v1`, tagged `v1-final` at
  22253f3. Its virtual environment is rebuilt at the new path, and its Claude Code memory moves with it.
- **v1 is reference only.** It is kept runnable, as an independent source of numbers to compare against.
- **v1's working notes** (`docs/brainstorms/*.md`, which git never held) are copied into v2's
  `docs/notes/v1/`.

## Alternatives considered

- **Refactor in place:** lower risk, since v1's core is tested, but it keeps v1's concepts (campaigns, flags,
  26 tools) in view, and its history, CLAUDE.md, and memory steer every session towards them.
- **Rebuild in `v2/` in the same repository:** one place, but Claude sees both packages, searches find v1
  code, the two `ema` packages clash, and the history mixes.

## Consequences

- v2 starts with an empty memory and a short CLAUDE.md. Working preferences from v1's memory are restated in
  v2's CLAUDE.md.
- Everything v1 verified (estimators, the sandbox, the approval rules) has to be verified again as it is
  ported, against the sample models and against v1's own output.
- `move_v1_start_v2.sh` performs the move. The v1 GitHub rename, the tag push, and the new repository are
  confirmed step by step when it runs.
