# 0070. Step T's provisional choices: runs, results, requests, summaries, the approval id, and the reuse key

**Date:** 2026-10-02. **Status:** accepted (2026-10-02, by the owner; drafted as proposed under 0066). **Resolves:** none.

## Context

Record 0066 added step T to the roadmap: the rest of `ema.types` (`architecture.md` §3's `runs.py`,
`results.py`, `requests.py`, `summaries.py`) and `identity.py`'s `approval_id` and `reuse_key`
(`data_model.md` §3.4), built before the store, the runner, the reports, and the diagnostics, so they can be
built in parallel. Its plan is `../plans/T-types.md`. §3 gives each type's fields as stubs; `data_model.md`,
`diagnostics/shared.md`, `uncertainty.md`, `contracts.md` (C17), and the use cases give their rules and shown
text. Where they are silent, the choices below keep P1–P7 and the specs' intent; none changes an accepted
spec's rule. They are listed so the owner can accept or reject each.

## Decision

We will, provisionally:

**Ids and codes**

1. **Hold ids in arrays as `numpy.dtype("V32")`** (`identity.ID_DTYPE`): 32 raw bytes, kept whole (an `S32`
   element drops trailing zero bytes, so 1 run id in 256 would read back short). `id_array(hex ids)` and
   `hex_ids(array or hex)` convert, through step 01's `batch_call_id` reader. Zeros mean "none" (a new row's
   `row_runs`, an unbatched run's `batch_call_ids`).
2. **Status and kind codes** in `RunColumns` are each member's index in its enumeration: ok 0, failed 1; error 0,
   timeout 1, unread 2, and −1 for an ok run's kind; through `RunStatus.code`, `FailureKind.code`, and
   `from_code`.
3. **`approval_id`** hashes `{"model_version_id", "asked_for", "request", "new", "reused", "n_before"}` with the
   request's canonical form; `asked_for` must be `diagnostic_evaluation` with a `Request` or `test_run` with a
   `TestRunRequest`, and counts must be ≥ 0 (W3's `new ≥ 1` stays the store's check). **`reuse_key`** returns
   the key's canonical JSON (§3's stub; the result id is `sha256_hex` of it), with the run ids as hex text and
   `versions` required to have exactly the keys `ema`, `numpy`, `scipy`, `matplotlib`.

**Construction rules**

4. **A type refuses what a store check or a spec forbids, with `ValueError`**, since a bad record is a mistake
   in EMA's code, not a user's request (`RequestError` stays for requests; the `Request`'s space is still
   parsed by `ModelParameterSpace.parse`, so a malformed one raises `RequestError`). `Run`: kind and reason
   exactly when failed (§5.6); a failed run has no model predictions, an ok run reads at least one, each missing
   one has a reason, every value is finite (§5.8, 0043, M7); replicate, attempt, and time ≥ 0. `RunColumns`:
   every column one row per run, `points` `(n, d)`, a kind exactly when failed. `Resolution`: `row_keys` index
   `new_keys` or are −1, a new row's `row_runs` is zeros. `RunBatch`: one run per design row. `Price`: counts ≥
   0, `reused_failed ≤ reused`, a time exactly when `from_runs > 0` (P3). `Progress`: phase `runs` or
   `analysis`, 0 ≤ done ≤ total. `RunInfo`: a kind exactly when failed.
5. **`Counts`** holds every failure kind (0 when none), and refuses counts that don't add up: new + reused =
   runs, failed + missing + usable = runs, and runs ≤ rows (S2; U2's "97: 56 new, 41 reused"; U3's "200 runs:
   34 failed, 166 usable").
6. **`Estimate`**: a finite value (where none can be computed there is no estimate, `uncertainty.md`); an
   interval of two finite doubles with lo ≤ hi and no reason, or None with a non-empty reason (0041).
   **`Observation`**: a finite double, an integer kept as one, or text (a run's kind). **`MeasuredNoisy`**: a
   finite point and std.
7. **A diagnostic result refuses a provenance** of another model version, diagnostic, or model prediction, or
   naming another number of runs than its design rows; and, as §3 says, a result with no estimate, observation,
   or note (0036).
8. **Mappings and sequences are frozen** as step 01's `DesignIdentity` does: mappings read-only (nested ones
   too, lists as tuples), sequences tuples. **Arrays are read-only views, not copies**, as step 01's `Design`:
   a copy of 10⁷ run ids is 320 MB.
9. **`Request`** parses its space and keeps its canonical form (every range `{"range": [lo, hi], "scale": ...}`,
   values as doubles, 0061), so a space given in any form makes one request, one approval id, and one reuse key;
   it refuses a request whose canonical form isn't strict JSON. Its canonical form is `{"diagnostic",
   "prediction", "space", "params"}`, the space null for the point run (§3.4 lists the parts, not the keys).
10. **`TestRunRequest.__test__ = False`,** so pytest doesn't try to collect it from a test module that imports it.

**JSON (C17, I11)**

11. **A result's JSON** is the canonical JSON (one encoder, I11) of every field but `shown`, its provenance
    included: tuples as lists, enumerations as their values (counts by kind as `{"error": n, ...}`), timestamps
    as `data_model.md` §3.2's text, run ids as hex text, the request and the design identity in their canonical
    forms, the design structure's levels and lines (0063). `from_json` rebuilds it, refusing non-strict JSON
    (NaN, Infinity) and anything that isn't a result with `ValueError`; `from_json(r.to_json()) == r`, every double
    bit for bit.
12. **`Provenance.canonical()` and `Provenance.from_canonical()`** (beyond §3's stubs): the whole provenance, as
    an export's `result.json` and a bare replay hold it (U8). *Corrected in review round 1 (item 18): the store
    does not write this form; its columns are `Provenance.column()` and `DiagnosticResult.column()`.*
13. **Timestamps:** `text.timestamp_text` and `text.parse_timestamp`, one rule for every stored timestamp (ISO
    8601 in UTC to the millisecond, "2026-10-01T14:03:07.123Z"): a naive datetime is refused; a timestamp a
    type holds (`MeasuredNoisy.made_at`, `ResultSummary.made_at`) is converted to UTC and cut to the millisecond,
    so it reads back equal. The store (step 06) uses the same two functions.

**Shown text**

14. **Renderers for the texts the specs give exactly,** as classmethods: `Price.make` ("96 new runs, 1 reused,
    about 3 h 12 min (from 1 stored run)"; "1 new run, 0 reused, time unknown"; "..., 200 reused, of which 34
    failed, ..."; the time by `duration`, "run" singular for 1); `Progress.of_runs` ("40/96 runs");
    `ResultSummary.make` (§7: "Diagnostic result 3f2a: scatter on beam@91c0…, T_max; 200 runs: 200 new, 0
    reused, 0 failed; report: ema report 3f2a", failed summed over kinds); `Reproduction.make` (U8's two lines);
    and `RunKey.make`, which computes the point hash and the run id. Every other text field (the approval and
    confirmation questions, `trust.md`; the model, loading, diagnostic, and run summaries) is rendered by the
    step that builds it, and the type prints what it is given.
15. **U8's text where U8 is silent:** with no original, "Diagnostic result 3f2a: replayed from its provenance,
    with no original to compare."; provenance differences written "name: detail" (versions) are joined into
    "Provenance differs in numpy (2.3.1 here, 2.4.0 there), scipy (...)."; any other (the rebuilt design's
    check, "design points differ at rows 3, 17") is its own sentence, capitalized.
16. **A result with no `shown`** prints "Diagnostic result <first 12 hex digits>: <diagnostic>, <model
    prediction>"; `Note` prints as its text, like every other type with a `text` field (a test checks them
    all).
17. **`finite_doubles`** joins `ema.types._values` (record 0067 item 8's home for reading numbers), for EMA's own
    records: a run's point, a run key's, the test run's, a measured-noisy point.

**Review round 1** (an independent review's findings; each amends or adds to the items above)

18. **The store's columns, not the whole JSON** (corrects item 12; `data_model.md` §5.9, §5.10, §5.12, W5).
    `Provenance.column()` is the `provenance` column: exactly `ema`, `numpy`, `scipy`, `matplotlib`,
    `spawn_tags`, `measured_noisy_read`, and `design_structure`, as canonical JSON. `DiagnosticResult.column()`
    is the `result` column: `title`, `counts`, `header_rows`, `notes`, `estimates`, `observations`, `figures`,
    and `extra`. Everything else has a column or a table of its own (the ids, the diagnostic, the model
    prediction, the request, the design, the approval; the run ids in `result_runs`; the result's
    measured-noisy record in `measured_noisy`, §5.11). `Provenance.from_columns(column, *, model_version_id,
    request, design, approval_id, run_ids)` and `DiagnosticResult.from_columns(*, result_id, model_version_id,
    diagnostic, prediction, result, measured_noisy, provenance)` rebuild them from a row (JSON columns as stored
    text) and its `result_runs`. Writing the whole JSON would copy `result_runs` into two columns: a 10⁷-row
    design's run ids are about 670 MB of hex text a copy, near SQLite's default limit of 1 GB on one value.
    `to_json` and `canonical()` stay whole, for `export.md`'s `result.json`, C17, and a bare replay.
19. **Equality without writing the JSON:** a `Provenance` and a `DiagnosticResult` are equal exactly when their
    JSON is, compared part by part (the run ids as bytes, the rest by their canonical JSON). A **`Request`** is
    equal exactly when its canonical JSON is, and hashes by it, as its approval id and reuse key do: a seed 1.0
    is not 1, and −0.0 is not 0.0.
20. **JSON read strictly, records checked when built:** `from_json`, `from_canonical`, and `from_columns` refuse,
    with `ValueError`, any object without exactly the keys written (an unknown key, `shown` included), a number
    past the doubles or infinite (`1e999`), an id that isn't 64 hex digits, a text field that isn't text, and a
    malformed stored space (the `RequestError` inside becomes `ValueError`: a stored record is EMA's). The
    constructors make the same checks, so a malformed record is refused when built, not at W5: an
    `IntervalInfo`'s settings must be strict JSON data (numpy's integers, NaN, and arrays refused; in JSON, only an
    `ID_DTYPE` array is ids), as must a `Request`'s parameters (`ValueError`, not `TypeError`).
21. **A result's cross-checks** (amends item 7): `counts.runs` is the number of distinct run ids in its
    provenance (`numpy.unique`, about 0.35 s per 10⁶ rows); it has an approval exactly when `counts.new > 0`
    (§5.9; a replay keeps the original's approval and counts, so it passes); its own measured-noisy record has
    its result id, model version, and model prediction (§5.11); each record its provenance read has the
    provenance's model version and the request's model prediction (Q10); the design identity's model version is
    the provenance's (0046).
22. **Codes and integer columns** (amends items 2 and 4): `from_code` refuses a code no member has (−1 is
    `FailureKind`'s only, for an ok run); `RunColumns` refuses a status other than 0 and 1 and a kind other than
    −1 to 2; an integer column (`row_keys`, `replicates`, `status`, `kind`) refuses a non-integer array rather
    than casting it; a `Resolution`'s stored row has its run's id, never zeros.
23. **`Price`:** `reused ≤ from_runs`, since Q2 counts every stored run of the model version, any status, the
    reused included (amends item 4).
24. **Arrays don't alias their sources** (amends item 8): an input array that owns its data is made read-only
    in place, the caller's too (no copy: 10⁷ ids are 320 MB); one that nothing can write is shared; a writable
    view of another array's data is copied. Step 01's `Design` keeps its rule (not this step's to change).
25. **One rule for ids given to a type:** `id_array` reads every form `batch_call_id` takes (hex text, 32-byte
    `bytes`, an `(n, 32)` uint8 array, an array of 32-byte elements), and `RunColumns`, `Resolution`, and
    `Provenance` read ids through it; an `S32` array is read whole, so its trailing zero bytes aren't dropped.
26. **`Reproduction.make(result, *, result_id, short_id, identical, differences=(), versions=(),
    design_differences=())`** (amends items 14 and 15): `result_id` is the original's, and a `Reproduction`
    refuses a replayed result with another (`architecture.md` §7, `reproduce`: the replay keeps it); it has
    differences exactly when `identical` is False; `versions` are `(name, here, there)` triples, written
    "numpy: 2.3.1 here, 2.4.0 there" in `provenance_differences` and "numpy (2.3.1 here, 2.4.0 there)" in the
    text; each of the rebuilt design's differences is its own sentence.
27. **Unhashable, plainly:** the frozen types holding read-only mappings (`Run`, `Counts`, `IntervalInfo`,
    `ApprovalRequest`, `DiagnosticParameterInfo`, `RunInfo`) set `__hash__ = None`, so `hash` fails at once;
    `Request` hashes by its canonical JSON. Step 01's and step 03's types are theirs to change.

**Review round 2** (the minor findings left from wave 2)

28. **An integer column refuses unsigned values past int64's maximum** (amends item 22): a uint64 array is read
    when its values fit, and refused, naming the value, when one would wrap.
29. **A failed run's model predictions are NaN in `RunColumns.values`** (`architecture.md` §3), checked when
    built; **a provenance's measured-noisy records read are newest first** (`data_model.md` §5.12, Q10), ties
    allowed, checked by their `made_at`.
30. **Nit:** `identity.py`'s docstring says the approval id and the reuse key are here (step T).

## Deferrals

- **Each summary type as strict JSON** (the MCP envelope's `data`, step 15): `results._plain` is the seam (it
  turns any of these dataclasses into JSON data). About an hour with step 15.
- **Rendering the questions and the summaries' texts:** steps 07 and 14, from `trust.md` and the use cases.

## Spec edits on acceptance

None is required. Clarifications that would help: `architecture.md` §3 could list `ID_DTYPE`, `id_array`,
`hex_ids`, `timestamp_text`, `parse_timestamp`, `Provenance.canonical`/`from_canonical`, the `column` and
`from_columns` methods, and the `make` classmethods (items 1, 12–14, 18, 26), and say that ids in arrays are
`V32`; `data_model.md` §3.4 could give the request's canonical keys (item 9); §5.9 could name the `result`
column's keys (item 18).

## Alternatives considered

- **`S32` id arrays:** an element drops trailing zero bytes (item 1).
- **`(n, 32)` uint8 id arrays:** §3 gives the arrays as `(n,)`.
- **Rendering every text in its own step:** the price is shown by the runner (07), the workspace's `price`
  (14), the CLI, and the MCP server; one renderer beside `duration` keeps one wording, tested once.
- **`RequestError` for a malformed record:** no user reaches these constructors; `ValueError` marks a bug in
  EMA.
- **`to_json(provenance=False)` for the `result` column** (item 18): it would still repeat the ids, the
  diagnostic, the model prediction, and the measured-noisy record, which have columns and a table of their own;
  `column` and `from_columns` name the store's form once, beside the export's.
- **Copying every input array** (item 24): safe, but 320 MB for 10⁷ ids; freezing an owner costs nothing.
- **Keeping microseconds in timestamps:** the store keeps milliseconds (§3.2), so a stored record wouldn't
  read back equal.

## Consequences

- **Size:** `ema.types` is now 1,514 code lines (without docstrings, comments, blank lines, or `__init__.py`'s
  175 lines of re-exports): step 01's 494 and this step's 1,020 (`results.py` 531, `runs.py` 225,
  `summaries.py` 98, `requests.py` 98, and 68 in `identity.py`, `text.py`, and `_values.py`); review round 1
  added 210 (the store's columns, strict reading, and the cross-checks). With step 03's model spec JSON and
  checks (about 275, §11), `ema.types` ends near 1,790, against §11's 860, past plan 01's forecast (about
  1,500). The budget record is the coordinator's to propose.
- Steps 06, 07, 08, 09, and 14 build on these types; a change to a field after them is a schema change for the
  store (`data_model.md` §11).
