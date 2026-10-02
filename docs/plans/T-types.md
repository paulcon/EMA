# T. The rest of `ema.types`: runs, results, requests, summaries, and two ids

**Status:** in progress (demo; record 0066); its choices are record 0070. **Branch:** `demo-T-types`.
**Updated:** 2026-10-02.

## Goal

Every type of `architecture.md` §3 exists, so the store (06), the runner and approval (07), the reports (08),
and the diagnostics (09–13) can be built in parallel against one vocabulary (record 0066 added this step): the
four modules `types/runs.py`, `types/results.py`, `types/requests.py`, and `types/summaries.py`, with
`DiagnosticResult.to_json` and `from_json` (C17), and `identity.py`'s `approval_id` and `reuse_key`
(`data_model.md` §3.4).

## Implements

- **`architecture.md` §3:** `runs.py` (`RunStatus`, `FailureKind`, `Run`, `RunKey`, `Resolution`, `RunColumns`,
  `RunBatch`, `Price`); `results.py` (`Estimate`, `IntervalInfo`, `EstimateTable`, `Observation`,
  `ObservationTable`, `Note`, `Figure`, `Counts`, `MeasuredNoisy`, `Provenance`, `DiagnosticResult` with
  `to_json` and `from_json`, `ResultSummary`, `Reproduction`); `requests.py` (`Request`, `TestRunRequest`,
  `ApprovalRequest`, `ConfirmationRequest`, `Approver`, `Progress`); `summaries.py` (`ModelSummary`,
  `ModelDescription`, `Proposal`, `Report`, `LoadingSummary`, `DiagnosticSummary`, `DiagnosticParameterInfo`,
  `RunInfo`); "every type with a `text` field prints as that text"; mappings read-only; array-holding
  classes `eq=False`, a result and a provenance equal when their JSON is.
- **`data_model.md`:** §3.2 (ids as 32 bytes; timestamps as ISO 8601 UTC to the millisecond); §3.4 (the
  request's canonical form, the test run's, the approval id, the reuse key, strict canonical JSON); §4.3
  (`RunStatus`, `FailureKind`); §5.6 and §5.8's checks on a run (kind and reason null exactly when ok; an ok run
  reads at least one model prediction, 0043; a missing value has a reason, never NaN); §5.9 and §5.12 (what a
  result and its provenance hold, the design structure, 0063); I11.
- **`contracts.md` C17** at the type level: strict JSON, every double exact, a "none" interval as null with its
  reason, the design structure included; the negative control, a NaN estimate, refused. (C17's `check_round_trip`
  over every diagnostic is step 09's.)
- **`diagnostics/shared.md`:** what a result holds (S1's sections as fields; S2's counts; the note's code and
  text); **`uncertainty.md`:** an estimate's interval or "none" with its reason, its method and settings, the
  undefined counts (V4, V6, 0041).
- **Shown text** where a spec gives it exactly: the price (`architecture.md` §3, U1–U3, 0010, C47: "96 new runs,
  1 reused, about 3 h 12 min (from 1 stored run)", "1 new run, 0 reused, time unknown", "200 reused, of which 34
  failed"); the run progress line ("40/96 runs", U2); a result's shown line (§7); U8's reproduction lines.
- **Records:** 0010, 0022, 0034, 0036, 0040, 0041, 0043, 0054, 0055, 0062, 0063.

## Out of scope for this step

- Rendering the texts no spec gives exactly (the approval and confirmation questions, `trust.md`, step 07; the
  model, loading, diagnostic, and run summaries, step 14): their types print the text they are given.
- `version_hash`, `ModelSpec`'s JSON (step 03); every store, runner, and workspace function.
- The MCP envelope's `data` (each type as strict JSON, step 15), beyond the result's and provenance's JSON.

## Tasks

1. Plan and record 0070.
2. Tests first, from the specs: `tests/unit/types/test_runs.py`, `test_results.py`, `test_requests.py`,
   `test_summaries.py`, and the new ids in `test_identity.py`'s companion `test_ids.py`.
3. Code the four modules and the identity functions; re-export from `ema.types`; add the modules to the API
   reference.
4. Run every check in `CLAUDE.md`; measure the lines.

## Checks before reporting done

- `uv run pytest -q && uv run lint-imports`; `uv run ruff check && uv run ruff format --check && uv run mypy`;
  `uv run sphinx-build -W --keep-going docs docs/_build/html`; `uv run pytest -q --slow -n auto`.
- Lines of `ema.types` against `architecture.md` §11's 860 (Notes).

## Stop condition

All checks pass; the report goes to the coordinator (0066). Nothing committed.

## Choices made here

Each is record 0070's, numbered as there, one line each.

1. Ids in arrays are `numpy.dtype("V32")` (`ID_DTYPE`), with `id_array` and `hex_ids`: `S32` drops trailing zeros.
2. Status and kind codes are each member's index (ok 0, failed 1; error 0, timeout 1, unread 2; −1 when ok).
3. `approval_id` checks `asked_for` against the request's type; `reuse_key` returns the key's canonical JSON,
   run ids as hex, `versions` exactly `ema`, `numpy`, `scipy`, `matplotlib`.
4. A malformed record is refused with `ValueError` (EMA's bug, not a user's request): §5.6's and §5.8's checks on
   a run, array lengths, a price's time exactly with stored runs, progress within its total.
5. `Counts` fills every failure kind, and checks new + reused = runs, failed + missing + usable = runs ≤ rows.
6. An estimate's value is finite; its interval two finite doubles, lo ≤ hi, or None with a reason (0041).
7. A result refuses a provenance of another model version, diagnostic, prediction, or number of rows.
8. Mappings frozen (nested too), sequences tuples; arrays read-only views, not copies (10⁷ ids are 320 MB).
9. `Request` parses its space into the canonical form; its form is `{"diagnostic", "prediction", "space",
   "params"}`, the space null for the point run; non-strict JSON refused.
10. `TestRunRequest.__test__ = False`, so pytest doesn't collect it.
11. A result's JSON is the canonical JSON of every field but `shown`; `from_json` refuses NaN and malformed input.
12. `Provenance.canonical()` and `from_canonical()`, for the store's provenance column and a bare replay.
13. `timestamp_text` and `parse_timestamp` in `text.py`: UTC to the millisecond; naive refused.
14. Renderers: `Price.make`, `Progress.of_runs`, `ResultSummary.make`, `Reproduction.make`; `RunKey.make`.
15. U8's text where U8 is silent: no original; versions joined as "numpy (2.3.1 here, 2.4.0 there)"; other
    provenance differences as their own sentences.
16. A result without `shown` prints "Diagnostic result <12 hex>: <diagnostic>, <prediction>"; `Note` prints as
    its text.
17. `finite_doubles` joins `ema.types._values`.

## Notes

- **Built** on `demo-T-types` (record 0066), tests first: the five test modules failed at collection before the
  code existed, then passed.
- **Tests:** 535 (534 in the fast tier, 1 slow), 128 of them new, in `tests/unit/types/`: `test_ids.py` (the
  approval id's and the reuse key's bytes against hand-built canonical JSON and SHA-256; id arrays; timestamps),
  `test_runs.py`, `test_requests.py`, `test_results.py` (C17's round trip with −0.0, a subnormal, 0.1, an
  integer observation, a "none" interval, the design structure, the measured-noisy records; C17's negative
  control, a NaN estimate, refused), `test_summaries.py`, and `test_shown.py` (every type with a `text` field
  prints as it; it found `Note`).
- **Times** (this Mac, 2026-10-02): the fast tier 1.3 s serially; both tiers 2.0 s with `-n auto`.
- **Source lines** (code lines, as plan 01 counts them): `ema.types` 1,304 [3,066 physical], without
  `__init__.py`'s 175 lines of re-exports: step 01's 494 and this step's 810 (`results.py` 367, `runs.py` 195,
  `summaries.py` 96, `requests.py` 86; `identity.py`, `text.py`, `_values.py` 66). With step 03's ~275,
  `ema.types` ends near 1,580 against §11's 860, as plan 01's question 6 forecast (about 1,500); the budget
  record is the coordinator's.
- **Shared files, edited additively:** `identity.py` (a `TYPE_CHECKING` import after `numpy`, then functions
  appended), `text.py` and `_values.py` (functions appended; `text.py`'s first import lines gain `re` and
  `datetime`), `types/__init__.py` (re-exports inserted in sorted order, as Ruff's isort requires, and a second
  `__all__ +=` list appended), `docs/index.md` (four modules). The docstrings of `identity.py` and
  `types/__init__.py` still say the approval id, the reuse key, and the four modules "come with later steps":
  left as they were for the merge; update them when steps 03 and T are merged.
- **Deferred** (0070): each summary type as strict JSON for the MCP envelope (step 15; `results._plain` is the
  seam, about an hour); the questions' and summaries' texts (steps 07 and 14).
