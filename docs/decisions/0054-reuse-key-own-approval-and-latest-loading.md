# 0054. Reuse a diagnostic result only with the same runs and versions; show its own approval; let the latest loading of a name win

**Date:** 2026-10-01. **Status:** accepted; its example and item 4 amended by 0055. **Resolves:** none (the data model's interview, TODO step 8; the
consistency review's "Step 8 inputs").

## Context

- **C50** says a repeated request returns the stored diagnostic result. **0010** says a retry is stored beside
  the failed run it replaces, and later designs use the retry. In U3, after `r4` retries `r3`'s 34 failed
  runs, `r3`'s request typed again would get its old result with the failed runs under C50 alone (the review's
  "C50 conflicts with 0010's retry").
- **Named constants** such as `BOOTSTRAP_RESAMPLES` are not part of a request (`uncertainty.md`). P4 promises
  the same result only with the same EMA and library versions. Nothing said whether a result stored by an
  older EMA is returned to a repeated request after an upgrade.
- **The mock reports disagree** on the approvals in Provenance: coordinate lines lists the test run's
  approval for its one reused run, and the interrupted evaluation's; the point run and the polynomial model
  list only their own, though they reuse runs too.
- **A model name** means its latest loading's settings (0029), and moving a model's directory makes no new
  model version (M3). Nothing said what loading a spec with the same name from a second directory does.
- **C51's** "deleting a result and rerunning from its provenance gives an identical result" can't hold
  for a fresh request: the rerun reuses every run, so its new and reused counts, its approval, and its note on
  reused failed runs differ from the original's.

## Decision

We will:

1. **Return a stored diagnostic result only when the request, the runs its design resolves to now, and EMA's
   and the libraries' versions (numpy, scipy, matplotlib) are all the same** (the reuse key,
   `../design/data_model.md` §3.4). Otherwise the request is a new diagnostic evaluation, computed from stored
   runs: no new runs and no approval when every run is stored. The old result stays as it was. After `r4`, `r3`'s
   request gives a new result from the retries; after an upgrade, a repeated request is computed again.
2. **List only a diagnostic result's own approval in its report's Provenance:** the approval of the runs its
   evaluation made, or "none (no new runs)". Every run records the approval it was made under, so each
   reused run's approval is found through the run (P5 and C51 hold in the store).
3. **Let the latest loading of a model name win:** loading a spec named `heat` from another directory makes
   `heat` mean that directory, with the same model version if its contents match (a move) or a new one if not
   (as U6's edit does), and the message names the directory it replaces.
4. **Read C51's "rerunning from its provenance" as a replay of the stored provenance** (its runs, approval,
   and measured-noisy records read), as `reproduce` does (U8). A fresh request after deletion is a new
   diagnostic evaluation, with its own counts.

## Alternatives considered

- **The request alone as the reuse key:** a simpler rule, but after a retry the old request never sees the
  retries unless the analyst changes it.
- **The stored result across upgrades:** no recomputation, but it can disagree with what the current EMA
  gives, with nothing in the report to say so.
- **A version number per diagnostic,** bumped when its computation or constants change: fewer
  recomputations, but a rule every change must remember.
- **Every approval behind the runs used, in Provenance:** complete on the page, but long after many smaller
  designs, and it changes two mocks instead of one.
- **Refuse a second directory under a used name** unless the first no longer holds the model: guards against
  two different models becoming versions of one name, but a copied and edited directory then needs a new name.

## Consequences

- **`../design/contracts.md`** (accepted; C46–C56 provisional until step 8):
  - C50 becomes "A repeated request (the same reuse key: request, runs resolved, and EMA's and the libraries'
    versions; `data_model.md`) returns the stored diagnostic result, with no new computation, no new run, and
    no approval asked, and a byte-identical report; a request whose runs or versions changed is a new
    diagnostic evaluation." Negative control unchanged; a second: "returns the stored result after a retry".
  - C51's "deleting a result and rerunning from its provenance" becomes "deleting a result and replaying its
    provenance".
  - C46–C52 and C56 cite `data_model.md`'s invariants I1–I12, and the section's "Provisional" note drops
    step 8.
- **`../design/diagnostics/shared.md`** (accepted): The report, item 7, "the runs used, and the approvals"
  becomes "the runs used, and the approval of its new runs"; "A repeated request" adds "(the same reuse key,
  `../data_model.md`)".
- **`../design/diagnostics/coordinate_lines.md`** (accepted): the mock's Provenance reads "approvals: 7d03 (56
  new runs)", in place of the three approvals.
- **`../design/model_interface.md`** (accepted): Versions, "Settings" becomes "The location and the settings
  (`keep`, `batch_size`, `timeout_s`) are stored with each loading; a model name means its latest loading's
  model version, directory, and settings (0054)."
- **`../design/data_model.md`:** §3.4's reuse key, §5.4 and §5.8's approvals, §5.2's loadings.
- **`../design/use_cases.md`:** unchanged; U1's, U2's, and U5's repeated requests keep their runs and
  versions, so they return the stored result.
- **Cost:** after an upgrade, the first repeat of each request is computed again from stored runs: seconds,
  or about 20 s for the polynomial model at d = 20.
