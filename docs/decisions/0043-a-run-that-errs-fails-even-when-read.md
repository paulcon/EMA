# 0043. Fail a run that errs, times out, or exits nonzero, even when its model predictions can be read

**Date:** 2026-10-01. **Status:** accepted. **Resolves:** none (consistency review, Q1). **Amends:** 0022's
consequence for the data model and its glossary row.

## Context

- **Two rules in accepted documents.**
  - M4, C35, and the glossary's "failed run" row say a run is failed **only** when none of its model
    predictions is read. 0022's consequence for the data model says the same: "a run's status is failed only
    when all are missing".
  - M12, C39, and `../design/model_interface.md` (Failures) say "a nonzero exit is a failure even when the
    model predictions can be read". The Failures section defines three kinds: `error` (raised, crashed,
    nonzero exit, signal, couldn't start), `timeout`, and `unread` (finished cleanly, nothing read).
- **A case that splits them.** A program writes a good `plate.out`, then exits with code 1, after a failed
  cleanup step, or after a solver diverged with a partial file written. Under M4 the run is `ok` and its value
  is used. Under M12 it is `failed` (kind `error`).
- M1 already says a failed run has NaN model predictions, and 0022 introduced "missing" per model prediction
  for runs that finish cleanly. The tighter wording of M4 came from 0022's per-prediction rule, not from a
  decision about exit codes (consistency review, 2026-10-01, `../notes/consistency_review_2026-10-01.md`).

## Decision

We will treat a run as **failed** when its call raised or crashed, exited with a nonzero code or a signal,
couldn't start, or timed out, whatever it wrote (kinds `error` and `timeout`), or when it finished cleanly
and none of its model predictions could be read (kind `unread`). A run that finished cleanly and read at least
one model prediction is `ok`. Each model prediction it couldn't read is missing, with its own reason (0022).

A failed run's model predictions are NaN (M1). What the program wrote stays in its run directory when `keep`
keeps it (0020, 0028), for inspection outside EMA.

## Alternatives considered

- **Read wins:** a run with any model prediction read is `ok`, and a nonzero exit is only a reason. Not
  chosen: it uses values a broken run may have left half-written, and the program itself reported the
  failure. A simulator that routinely exits nonzero with good output shows as failed runs with the reason
  "exited with code 1", and the user fixes the wrapper.
- **Exit wins, and keep the values read:** store what a failed run read, never usable by a diagnostic. Not
  chosen: it adds a stored-but-unusable state to the data model for a case the run directory already covers.

## Consequences

- **`../design/model_interface.md`** (accepted):
  - Failures: "a run is `ok` when it finished cleanly and read at least one model prediction".
  - M4: "a run that finished cleanly is failed only when none is read (kind `unread`)".
  - M12 and the kinds: unchanged.
- **`../design/contracts.md`** (accepted): C35 is worded as M4. C39 is unchanged.
- **`../design/glossary.md`** (accepted): "failed run": "a run whose call raised, crashed, exited nonzero,
  couldn't start, or timed out (whatever it wrote), or that finished cleanly with none of its model predictions
  read; it is stored with its kind, its reason, and NaN model predictions, and reused like any stored run
  unless the user asks to retry (P6, 0010, 0043)".
- **`../design/data_model.md`** (step 8): a run's status is failed for the kinds above, not "only when all
  [model predictions] are missing" (0022's consequence, amended).
- **0022's status:** "accepted; its data-model consequence and glossary row amended by 0043".
- **Tests:** M12's test (a good `plate.out` and exit 1: failed, kind `error`) and M4's (two parsers, one
  finding nothing: `ok`, one NaN) both stand, and now agree.
