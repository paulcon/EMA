# 0090. Treat build steps, review rounds, and layer numbers as citations, kept off the site like ids

**Date:** 2026-10-28. **Status:** accepted (2026-10-28, by the owner). **Resolves:** none.

## Context

- **Record 0089 item 1** keeps record ids, spec ids, spec file names, and section marks off the site. Plan 18's
  review (round 1) found other internal words the site check lets through, 25 on 11 pages of the site as built
  on `build-18-site-citations`:
  - **build step numbers:** "The store (step 06):" and four more captions in `index.md`; "(step 03)", "(step T)",
    "the runner (step 07)" in `ema.types.identity` and `ema.store.lock`; "(step 11's method)" and "the PDF build
    step's" in the guides;
  - **review rounds:** "Fork caveat (review round 1):" in `ema.store.lock`;
  - **architecture layer numbers:** "Layer 3b: the runner", "Layer 5: the command line", and four more module
    summaries, which open the module's page and its line in the API reference's table.
- **They work like citations:** each points a contributor at a plan, a record's review, or `architecture.md`'s
  layers, and says nothing a visitor can follow. Most already sit in parentheses.
- **A guide numbers its own steps,** and refers to them: "on step 6's result", "loaded in step 3", "the Python
  function's steps 4–6". Those are the guide's own text, written with one digit. A build step is written with two
  digits, or a letter ("step 06", "steps 04 and 05", "step T"); `architecture.md` §7's steps of a diagnostic
  evaluation ("steps 4–7") are cited only with `architecture.md`, in a parenthesis.

## Decision

1. **A build step, a review round, and a layer number are citations** under 0089: "step 06", "steps 04 and 05",
   "step T", "build step"; "review round 1", "round 2"; "layer 3b", "Layer 5". In the repository they are cited in
   parentheses, like an id (0089 item 2); the site drops them (item 3); its check finds them (item 4). A guide's
   reference to one of its own steps, with one digit ("step 6's result"), is text, and stays.
2. **The filter and the check gain these patterns,** with known answers for each, and for a guide's own steps as
   kept.
3. **The six module summaries that open with a layer** ("Layer 3b: the runner, …") open with what the module is,
   and cite the layer in parentheses ("The runner, a serial loop, … (layer 3b; 0015; AR4, P3)."); a sentence that
   uses a build step as a word ("the PDF build step's") is reworded.

## Alternatives considered

- **Leave them** (0089 as accepted): no change, but the site keeps about 25 internal words, and nothing stops more.
- **Check them without dropping them:** every one reworded by hand, though most are already in parentheses, where
  dropping them is what 0089 does for ids.
- **Every "step N", one digit included:** simpler, but it would flag the guides' references to their own steps.

## Consequences

- **0089's status** becomes `accepted; item 1's list amended by 0090`.
- **`docs/_ext/ema_citations.py`** (the patterns), its tests, and plan 18's notes; about 10 docstrings and the
  guides' two phrases reworded; no code change; CLAUDE.md's "Cite ids" and `CONTRIBUTING.md` unchanged (a build step
  or a review round is cited like an id already).
- **What gets harder:** a docstring can't say "step 07" as a word; it says what the step built, and cites the step.
