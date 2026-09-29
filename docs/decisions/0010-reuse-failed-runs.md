# 0010. Reuse failed runs unless the user asks to retry them

**Date:** 2026-09-29. **Status:** accepted. **Resolves:** none (TODO step 2, use case U3).

## Context

P3 says a stored run is reused when its model version and point match, and doesn't say whether a failed run
counts. The glossary says a failed run "is stored with its reason, and its model predictions are NaN".

v1 never reused a failed or timed-out run, "so a flaky failure can be retried"; it did reuse a run refused for
breaking an input constraint, since the refusal depends only on the spec
(`../../../EMA-v1/CLAUDE.md`, "Runs belong to a model version"; `../notes/v1/lessons_learned_answers_2026-09-27.md`).

P7 treats a model as deterministic unless its spec says it is noisy or repeats measure variation. A
deterministic model that fails at a point (a solver that doesn't converge there) fails again at that point,
and each attempt costs a full run, or a full timeout. In U3, a heat solver takes about 2 minutes per run and
fails at 34 of 200 points: under v1's rule, every later design that includes those points spends their time
again, and its price can't say how much of it will fail.

Some failures don't depend on the point: a timeout on a busy machine, a full disk, a license server that was
down. Those are worth running again.

## Decision

We will treat a failed run as a stored run, and reuse it unless the user asks to retry.

- **Reuse.** When a design includes a point whose stored run (same model version, point, and replicate)
  failed, EMA reuses that failed run and doesn't run the model there. The failed run counts as not usable
  (P6).
- **Price.** The price counts failed runs among the reused ones ("200 reused, of which 34 failed").
- **Retry.** `retry_failed=True` on `Workspace.run` and `estimate` (`--retry-failed` in the CLI) runs the
  design's failed points again. They are priced as new runs, and approved like any others (P3).
- **Report.** When a diagnostic result uses reused failed runs, a note says how many, and that
  `retry_failed` runs them again.
- **Provenance.** A diagnostic result that used a failed run stays reproducible after a retry (P5): the retry
  doesn't erase the failed run it replaces for later designs.

## Alternatives considered

- **Never reuse a failed run (v1):** simple, and a transient failure gets another chance automatically. But a
  deterministic failure costs its full time again in every design that includes the point, and the price
  can't say so in advance.
- **Retry timeouts only; reuse other failures:** timeouts are the most likely to be transient. But the reason
  for a failure isn't always reliable (a solver can crash because the machine ran out of memory), and a rule
  per reason is one more thing to explain; the flag covers both.
- **Always reuse, with no retry:** the user would have to change the model version to try again, which
  throws away every good run as well.

## Consequences

- **`../design/principles.md`:** P3's statement is unchanged; it already reuses by model version and point.
- **`../design/glossary.md`** (accepted): the "failed run" row adds "reused like any stored run unless the
  user asks to retry (0010)".
- **`../design/use_cases.md`:** U3 shows reuse and retry of failed runs, and tests them.
- **`../design/architecture.md` §7–8:** `Workspace.run` and `estimate` take `retry_failed`; the CLI's `run`
  and `estimate` take `--retry-failed`; `CostEstimate` counts failed runs among the reused ones.
- **`../design/data_model.md`** (step 8): how a retried run is stored beside the failed run it replaces, so
  that later designs use the retry and earlier diagnostic results keep the failed run.
- **`../design/contracts.md`** (step 7): the store contract makes no new run at a failed point unless retry is
  asked, and then exactly the failed points.
- **A transient failure stays failed** until the user retries it. The note in the report is how they find
  out.
