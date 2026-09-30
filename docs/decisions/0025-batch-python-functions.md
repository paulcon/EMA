# 0025. Let a Python function take a batch of points in one call

**Date:** 2026-09-30. **Status:** accepted. **Resolves:** none (TODO step 4; the owner's "parallel flag").

## Context

The owner's redesign notes say: "If the model has a true parallel flag, then send all the inputs to the model
at once" (`../notes/v1/ema-redesign.md`, "Scheduler"). A vectorized Python function (NumPy over an array of
points) is often many times faster on n points at once than in n calls. v1 had no such flag: its Python
functions were always called once per point.

Two accepted records assume one call per run:

- 0015: v2.0 runs one model run at a time; each run has its own run directory; a run has three phases
  (prepare, execute, collect); runs are counted against the approval when they start.
- 0020: every run has a run directory, at `<workspace>/runs/<run id>/`, and runs in it.

P3's price estimates time from stored run durations.

## Decision

We will let a Python function model declare `batch: true`, and then call it with many points at once.

- **Call.** `f(X)`, with `X` an (n, d) array whose columns follow the order of the model spec's model
  parameters (held ones included, 0023). It returns an (n,) array when the model has one model prediction,
  or a mapping from model prediction names to (n,) arrays when it has several (0022).
- **Batch size.** A design's new runs go in calls of at most `batch_size` points (a spec field; by default all
  of them). `batch_size` doesn't decide what a run does, so it is not part of the model version.
- **Run directories.** Each run keeps its own run directory, with its record and point, as 0015 and 0020 say.
  The call runs in a batch directory beside them, which each run's record names; the lookup (0020) gives both.
- **Approval.** A call's runs are counted against the approval when the call starts (0015), so a call never
  holds more points than remain approved.
- **Failures.** A NaN (or other non-finite value) at one point is a missing model prediction for that run
  (0022). An exception, a timeout, or a result of the wrong shape fails every run in the call, each with the
  same reason.
- **Interruption.** Stopping EMA loses the call in progress; the runs of finished calls are stored.
- **Time.** Each run records the call's time divided by its size, and the call's size and time. Prices
  estimate per run from these, as for any model.

"One model run at a time" in `../design/scope.md` now reads: one model call at a time, a call being one run,
or one batch of a Python function model.

## Alternatives considered

- **Later, as a small build step (suggested in the interview):** keeps 0015's one-call-per-run as written, but
  cheap vectorized models (U1's kind) pay one call per point.
- **One shared run directory per batch:** simpler on disk, but it amends 0015's rule 3 and 0020's one
  directory per run id.
- **Time per batch only:** more accurate for models with a large start-up cost, but a second pricing rule.
- **Always all new points in one call:** one field fewer, but a large design is one call that can't be
  stopped partway, and a crash loses all of it.

## Consequences

- **`../design/scope.md`** (accepted): the "Running" row reads "one model call at a time (a run, or a batch of
  a Python function model, 0025) …".
- **`../design/model_interface.md`:** the Python function section has `batch` and `batch_size`; the three
  phases of a run (0015) apply to a call.
- **`../design/data_model.md`** (step 8): a run records its batch (directory, size, and time) when it has one.
- **`../design/contracts.md`** (step 7): the model adapter contract runs a batch model and the same function
  one point at a time, and requires identical model predictions; a batch with one NaN row; a batch that raises;
  the approval cap with a batch larger than the runs left.
- **Isolation** (OD-11, the next item) applies to a batch call as to any call.
- **Size:** about 100–150 source lines and their tests, within the 8,000-line budget, whose estimate
  (about 7,800) leaves little room.
