# 0007. Choose the principles

**Date:** 2026-09-29. **Status:** accepted; P8 superseded by 0008. **Resolves:** none (TODO step 1).

## Context

`../design/principles.md` listed 14 candidate principles, taken from v1's design rules
(`../notes/v1/lessons_learned_answers_2026-09-27.md` §3) and `../notes/v1/ema-redesign.md`. A principle is an
invariant, not a procedure, and has a reason, an enforcing mechanism, and a test; the page aims for ten or
fewer. v1's CLAUDE.md grew to 36 rules, several of which restated one another or were implementation details
(record 0001, "Context").

On 2026-09-29 the owner was interviewed on each candidate (keep, reword, merge, or drop), with one question
for each part of a principle: the statement, why, enforced by, and tested by. Two candidates not on the list
were added from `../design/architecture.md` and records 0003–0005. Some candidates turned out to be covered
already by accepted records (0004, 0005, 0006) or by the accepted `../design/purpose.md`.

## Decision

We will adopt eight principles, P1–P8, worded as in `../design/principles.md`:

| P | Principle | From the candidates |
|---|---|---|
| P1 | Numbers come from EMA | "Numbers come from EMA, not from an LLM" |
| P2 | Results first; interpretation is separate | "Results first; interpretation is separate", with "Heuristic thresholds are named and documented" merged in, for interpretation thresholds only |
| P3 | Everything that decides a run is hashed; every new run is priced and approved | "Runs belong to a model version and are reused", "Nothing runs without approval" (without its isolation clause), and "Cost is known before running" |
| P4 | Diagnostic evaluations are deterministic | "Designs are deterministic", promised for the same EMA and library versions |
| P5 | Every diagnostic result records its provenance | "Every result records its provenance" |
| P6 | No data, no estimates; no dependence on units | "No data, no claims", with "Conclusions don't depend on units" (model predictions only) and the NaN rule from "Every diagnostic follows the same steps" |
| P7 | Noise is explicit | "Noise is explicit" |
| P8 | The glossary's words | new; generalizes what records 0003, 0004, and 0005 require for their own terms |

We will drop three candidates, and hold two until the steps that decide what they depend on (see
"Consequences").

## Alternatives considered

The dropped candidates:

- **Every diagnostic follows the same steps** (design → run → compute → plot → report; a failed run is NaN,
  and every diagnostic tolerates it). As written, the first half is a procedure, not an invariant. Record 0006
  fixes the sequence ("EMA builds one design, prices it, asks for approval before any new runs, runs it,
  computes one diagnostic result, and produces one report"), and the layers in `../design/architecture.md` and
  the contracts cover the rest. The NaN rule was kept, in P6.
- **Every estimate has an interval,** made by a stated method (OD-12); a claim that something is small needs
  the whole interval below its threshold. The first half is covered by record 0004 (the interval's method and
  settings are always reported with it), by the glossary's definition of an estimate (a number with its
  variability interval and its method), and by `../design/purpose.md` ("Reports include variability intervals
  for all estimates"). Its checks belong to the diagnostic contract. The second half is interpretation, by
  P2's definition.
- **Compute from what the model received** (if the model rounds its inputs, diagnostics use the rounded
  values). Dropped for now: it belongs with the model interface, and matters only if rounded formats for
  input decks come back (OD-20, v1's `number_format`).

Other merges considered and not taken:

- **Designs are deterministic merged with provenance:** tried, then undone. Determinism (the same request
  gives the same result) and provenance (every diagnostic result records where it came from) have different
  mechanisms and tests.
- **"Designs are deterministic" across library versions:** would argue for EMA's own seeded stream (OD-13);
  the owner chose the same EMA and library versions, which P5 records.
- **Units as its own principle, including model parameters:** folded into P6 for model predictions only.
  Model parameter units belong with the map from a model parameter space to a reference shape (record 0005),
  in `../design/designs.md`.
- **Cost as its own principle, with budgets:** merged into P3, where the approval shows the price and caps the
  new runs. Budgets wait on OD-15.
- **Heuristic thresholds covering note thresholds too:** P2's naming rule covers interpretation thresholds
  only; the thresholds behind notes (the minimum number of usable runs, the flatness tolerance) are named
  under P6.

## Consequences

- **`../design/principles.md`:** holds P1–P8 and the held candidates; the dropped candidates are recorded here
  instead.
- **Held candidates** stay in `../design/principles.md` until their step:
  - "User code runs isolated, without EMA's secrets" (split from "Nothing runs without approval"): OD-11 and
    `../design/trust.md` (step 10).
  - "One-way layers": `../design/architecture.md` (step 9), with the owner's answers for why, enforced by, and
    tested by already recorded.
- **Pointers from the dropped candidates:**
  - the NaN rule is in P6;
  - the rule that a claim of "small" needs the whole variability interval below its threshold goes to the
    experimental rules' spec, if OD-8 keeps one;
  - "Compute from what the model received" is revisited with `../design/model_interface.md` (step 4) and
    OD-20.
- **Glossary:** rows for "noisy" and "replicate" (P7); "approval" narrowed to a diagnostic evaluation's new
  runs (P3).
- **`../design/scope.md`:** decides whether noisy models are in v2.0 (P7).
- **`../../CLAUDE.md`:** lists P1–P8 in one line each, once `../design/principles.md` is accepted.
- **Tests:** each principle names its tests; they join the contracts in `../design/contracts.md` and the
  plans that build the modules.
