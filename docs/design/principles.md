# Principles

**Status:** candidates listed. **Updated:** <YYYY-MM-DD>.

> Aim for ten or fewer. A principle is an invariant (always true), not a procedure. Each has:
> - **why**: the reason, which lets someone apply it to a case it didn't foresee;
> - **enforced by**: the code that makes it true;
> - **tested by**: the test that fails if it breaks.
>
> A principle without a test is a wish. Implementation details (how a hash is computed, where commits are
> batched) belong in docstrings, not here. CLAUDE.md lists each principle in one line and points here.

## Accepted

> Move a candidate here once you've decided on its wording.

### P1 <short name>

<statement, one or two sentences>

- **Why:** <…>
- **Enforced by:** <module or mechanism>
- **Tested by:** <test name>

## Candidates

> From v1's design rules (`../notes/v1/lessons_learned_answers_2026-09-27.md` §3) and `../notes/v1/ema-redesign.md`.
> Accept, reword, merge, or delete each.

- **Numbers come from EMA, not from an LLM.** Every number a user sees is computed and stored by EMA.
- **Results first; interpretation is separate.** Values, intervals, run counts, figures, and data caveats are
  results. Any comparison with a heuristic threshold, and any advice, is interpretation, kept apart and
  labelled experimental (or left out, OD-8).
- **Runs belong to a model version and are reused.** A run is stored against the version that produced it.
  A changed model is a new version, and nothing stale is reused.
- **Designs are deterministic.** The same request gives the same points and the same numbers.
- **Every diagnostic follows the same steps**: design → run → compute → plot → report. A failed run is NaN,
  and every diagnostic tolerates it.
- **No data, no claims.** With too few usable runs, or an output that is constant to rounding, a diagnostic
  reports counts and a note, and claims nothing.
- **Conclusions don't depend on units.** Every tolerance is relative to the output's size or range.
- **Every estimate has an interval,** made by a stated method (OD-12). A claim that something is small needs
  the whole interval below its threshold.
- **Compute from what the model received.** If the model rounds its inputs, diagnostics use the rounded
  values.
- **Noise is explicit.** A model is deterministic unless measured otherwise.
- **Cost is known before running.** Every request is priced, and checked against its budget, before any run.
- **Nothing runs without approval.** Approval covers everything that decides what a run does. User code runs
  isolated, without EMA's secrets.
- **Heuristic thresholds are named and documented.** No magic numbers in the code.
- **Every result records its provenance**: EMA's version, the libraries, the model version, the seed, the
  approvals.
