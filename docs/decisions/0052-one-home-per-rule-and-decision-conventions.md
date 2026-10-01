# 0052. Give each rule one home, trim the specs' history, and write down the decision conventions

**Date:** 2026-10-01. **Status:** accepted. **Resolves:** none (consistency review, Q10). Editorial: no
behavior changes.

## Context

- **The bootstrap is specified five times.** `diagnostics/shared.md`, `uncertainty.md`, scatter, the linear
  model, and the polynomial model each write out its resample call. Its constants are in two tables, each
  pointing to the other for its reasons. `KNOWN_ANSWER_N` is defined three times.
- **Contracts restate M and G rows.** C20–C27 and C31–C45 restate G1–G16 and M1–M20 word for word. Two pairs
  had drifted (C37/M8, corrected in place; C33/M3).
- **History in the specs:**
  - "What this spec asks of other documents" sections are mostly asks already applied;
  - each diagnostic's "Tests it implies" repeats its requirements and the contracts;
  - there are 54 inline "(interview, 2026-09-30)" tags.
- **`STATUS.md`'s Done entries** (about 1,500 words) retell the records, and `TODO.md`'s done steps repeat
  STATUS.
- **`reference_models.md`** plans to copy each diagnostic's expected answers at step 11.
- **Conventions:**
  - `decisions/README.md` gives only "superseded by", though "amended by" is in use (0040, 0008, 0022).
  - 0015, 0020, 0023, 0032, and 0034 were changed in part by later records, with no mark.
  - The in-place correction this project uses is written nowhere.
  - CLAUDE.md and README cite records as "D0007", while every document and commit says "0007".
  - CLAUDE.md's "one branch per step (`step-NN-topic`)" collides with TODO's design steps, which commit on
    main.

## Decision

We will:

1. **Make `uncertainty.md` the one home of the bootstrap:** its steps, and both constants with their reasons.
   `shared.md` points to it. Each diagnostic's Uncertainty section keeps only its differences: which estimates
   use distinct runs, what is undefined, and its tag. `KNOWN_ANSWER_N` and `KNOWN_ANSWER_SDS` are defined once,
   in `shared.md`.
2. **Write a contract that restates one M or G row as that id, plus any difference.** For example, C37:
   "M8."; C33: "M3, and files are compared as files". Each keeps its check and negative control.
3. **Trim the accepted specs' history:**
   - delete the "What this spec asks" bullets already applied or addressed to accepted steps, keeping only the
     asks of steps 8–13;
   - keep in "Tests it implies" only each diagnostic's exceptions to the contracts, and drop the section from
     `diagnostics/_template.md`;
   - delete the inline "(interview, 2026-09-30)" tags.
4. **Trim `STATUS.md` and `TODO.md`.**
   - STATUS's Done list has one line per step, with its specs and record ids.
   - The Decided table becomes Id | Record | Date; the record's title is the decision.
   - TODO's done steps keep only "Records: …".
5. **Make `reference_models.md` the one home of each reference model's truths** (formulas, analytic values).
   Its "Expected answers" section becomes an index: model → diagnostic spec table → the script that checks it
   independently. Diagnostic specs cite the truths there.
6. **Write down the decision conventions** in `decisions/README.md` and `0000-template.md`:
   - a record that changes part of an accepted record marks it, in the same commit, "accepted; <part> amended
     by NNNN". Apply this to 0015 (by 0025, 0029, 0030), 0020 (by 0028), 0023 and 0032 (by 0033), and 0034's
     glossary row (by 0042);
   - plain errors in an accepted spec (typos, wrong citations, stale cross-references, a number that
     contradicts its own source) are corrected in place, without a record, and listed in the commit message.
7. **Cite records as "0007"** ("record 0007") in CLAUDE.md and README, as every document and commit does.
8. **In CLAUDE.md:** "One branch per build step (`build-NN-topic`), from `main`; design steps (TODO 1–13)
   commit on `main`". Plans number build steps from 01.

## Alternatives considered

- **Keep the copies,** with a fast test that every named constant has one value: each spec reads alone, but
  copies drift, as C37/M8 did.
- **Full sentences in every contract,** with a docs test comparing each C row with the M or G row it cites.
- **Leave STATUS and TODO as they are:** the history stays where it is read, at about 2,000 words a session.
- **Copy the expected answers into `reference_models.md`** at step 11: two copies of each number.
- **Merge `notes/decision_workflow.md` into `decisions/README.md`:** not chosen; it stays as a short guide.
- **Archive or index `docs/notes/v1/`:** not chosen. The v1 notes are scratch notes for deriving v2's design,
  and are archived and removed from this repository when the design is finished.
- **Add "Ported from v1" and "Ids implemented" fields to the plan template:** not chosen now.

## Consequences

- **Accepted specs:** `uncertainty.md`, `diagnostics/shared.md`, the six diagnostic specs, `contracts.md`,
  `designs.md`, `model_interface.md`, `use_cases.md`, and `scope.md`, edited by Decisions 1–3. No requirement,
  value, or test changes.
- **`diagnostics/_template.md`:** no "Tests it implies" section.
- **`STATUS.md`, `TODO.md`:** Decision 4.
- **`reference_models.md`** (draft): Decision 5, with the diagnostic specs citing it.
- **`docs/decisions/README.md`, `0000-template.md`,** and the status lines of 0015, 0020, 0023, 0032, and 0034:
  Decision 6.
- **`CLAUDE.md`, `README.md`:** Decisions 7 and 8.
- **Order:** apply after the records 0043–0051, whose edits touch the same sections.
