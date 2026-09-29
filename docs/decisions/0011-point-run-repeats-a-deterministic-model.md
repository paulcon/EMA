# 0011. Let the point run repeat a deterministic model, to measure its noise

**Date:** 2026-09-29. **Status:** accepted. **Resolves:** none (TODO step 2, use case U7; a conflict in P7).

## Context

P7 (accepted) says two things that can't both hold:

- **Enforced by:** "the store key includes a replicate number, always 0 for a deterministic model."
- **Tested by:** "A model declared deterministic that returns different values on repeats is caught by the
  point run, and gets a note." Catching it needs repeated runs of a deterministic model at one point: runs
  with replicates 1, 2, ….

The store contract in P7's "Tested by" also says "for a deterministic model, EMA never makes a second run at a
stored point", which the point run's repeats would break.

P7's reason for measuring noise is that a solver tolerance or an internal random seed can make a model noisy
without the user knowing, and unmeasured noise reads as roughness and hides smoothness. The point run is the
diagnostic that measures it (`architecture.md` §6: "point (nominal), repeats (0)").

U7 has a heat solver declared deterministic whose iterative tolerance makes it vary slightly; the point run
at nominal with 10 repeats catches it.

## Decision

We will let the point run's repeats make replicates 1, 2, … of a deterministic model, and nothing else.

- **Point run.** With `repeats=k`, the point run's design has the point with replicates 0 to k. Replicate 0 is
  the ordinary run at that point, reused if it is stored; replicates 1 to k are new runs, priced and approved
  like any others (P3), and reused when the same repeats are asked for again.
- **Every other design** uses replicate 0 for a deterministic model, as P7 says now.
- **P7's "Enforced by"** reads: "the store key includes a replicate number: 0 for a deterministic model,
  except the point run's repeats, which are numbered 1, 2, …".
- **P7's store contract** reads: "for a deterministic model, EMA never makes a second run at a stored point,
  except the point run's repeats."

## Alternatives considered

- **Repeat only models declared noisy:** keeps "always replicate 0" as written, but then hidden noise can't be
  measured, only guessed from roughness along a finer line, which confuses noise with real structure. P7's
  "Tested by" line would change instead, and lose its purpose.
- **Store the point run's repeats outside the run store** (as a separate noise check): keeps the store key
  simple, but the repeats are runs, with their own time and approval, and P3 and P5 need them stored and
  reusable like any other.
- **Decide later (step 4 or 7):** possible, but the conflict is in an accepted principle, and U7 depends on it.

## Consequences

- **`../design/principles.md`** (accepted): P7's "Enforced by" and "Tested by" lines change as above. Its
  statement doesn't.
- **`../design/glossary.md`** (accepted): the "replicate" row reads "a deterministic model has only replicate
  0, except the point run's repeats (0011)".
- **`../design/use_cases.md`:** U7 uses the point run's repeats on a model declared deterministic.
- **The point run's spec** (step 6) says how the repeats are numbered and reused, and what counts as measured
  variation (relative to what, P6).
- **`../design/contracts.md`** (step 7) and **`../design/data_model.md`** (step 8): the store contract and the
  run key carry the exception.
