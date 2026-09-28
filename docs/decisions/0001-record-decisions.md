# 0001. Record decisions in decision records

**Date:** 2026-09-28. **Status:** proposed. **Resolves:** none.

## Context

In v1, decisions were recorded in several places:
- memory notes outside the repository;
- plan files in `~/.claude/plans/`;
- reports in the gitignored `docs/brainstorms/`;
- CLAUDE.md, whose design rules grew to 36 and about 7,400 words.

Several decisions were argued again, or rediscovered, in later sessions: the sobol interaction trade-off,
whether a constant surface is additive, whether declines count toward the approval limit. Claude Code filled
gaps in specs sensibly, but without review, which is part of how the architecture drifted
(`docs/notes/v1/lessons_learned_2026-09-27.md` §3).

## Decision

We will record every significant decision about v2 as a numbered decision record in `docs/decisions/`, in
Nygard's format. We will keep three kinds of document apart:
- specs in `docs/design/`, which change only through decisions once accepted;
- decisions in `docs/decisions/`, which are never edited, only superseded;
- status in `STATUS.md`, with open decisions listed as OD-n.

Claude Code builds only from accepted specs, and asks when a spec is silent.

## Alternatives considered

- **Keep decisions in the specs themselves:** simpler, but it loses the reasons and the alternatives, and
  edits hide what changed.
- **Keep them in memory notes or issues:** outside the repository or outside git history, and invisible to a
  new session unless it's pointed to them.

## Consequences

- Each decision costs a page of writing. Claude Code can draft it; the owner accepts it.
- New sessions (and collaborators) can find why the code is as it is.
- CLAUDE.md stays short: principles and pointers, not a record of every decision.
