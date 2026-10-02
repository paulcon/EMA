# 0067. Step 01's provisional choices: the scaffolding, the design types, and the design generators

**Date:** 2026-10-01. **Status:** proposed (provisional; record 0066). **Resolves:** none.

## Context

Build step 01 (`../plans/01-scaffolding-and-designs.md`) was carried through to its task 8 on the `demo` branch
without the owner's review (0066). Its plan lists the choices the owner approved ("Choices made here"); building
it met more places where the specs (`../design/architecture.md` §3–§4 and §10, `../design/designs.md`,
`../design/contracts.md`, `../design/data_model.md` §3.4) are silent or leave a detail open. Each choice below was
made to keep P1–P7 and the specs' intent; none changes an accepted spec's rule. They are listed so the owner can
accept or reject each.

## Decision

We will, provisionally:

**Tooling**

1. **Keep Ruff's default rule set as Ruff 0.16 defines it** (it now includes some RUF, PLE, FURB, and C4 rules
   beside E and F), with 0059's additions, and ignore D105: a magic method such as a dataclass's
   `__post_init__` is not a public name, and 0059 asks for docstrings on public names only.
2. **Exclude Markdown from Ruff** (`extend-exclude = ["docs/checks", "*.md"]`): Ruff 0.16 formats Python code
   blocks inside Markdown, and its first run rewrote six accepted documents (restored from `HEAD` at once).
3. **Make `tests/` a package tree** (an `__init__.py` in each directory), with pytest's default import mode, so
   tests share helpers as `tests.support.designs` and `tests.support.fakes`.
4. **Collect contract modules by one general hook** (`tests/contracts/conftest.py`): every module in that
   directory that isn't `conftest.py`, `test_*.py`, or `_*.py` is collected, and in it only `check_*` and
   `test_*` functions and `Test*` classes. Each contract module parametrizes its checks with a fixture named for
   the implementation (`generator`, `sampler`); later contracts (model adapter, store, diagnostic, interval
   method, basis) add a module and nothing else.
5. **The meta-test counts any exception as a check failing on its broken toy:** an `AssertionError`, pytest's
   "did not raise", or an error the check lets through (C27's broken toy builds from the raw space and raises
   its own error before validating). Each broken toy's failure was inspected once and is for the intended reason.
6. **pytest's `xfail_strict = true`;** the GitHub workflow uses `actions/checkout@v4`, `astral-sh/setup-uv@v6`,
   and `actions/upload-artifact@v4`; its lowest-versions job runs `uv sync` without `--locked`, since the lowest
   resolution rewrites the lockfile; `uv_build` is bounded `>=0.12.21,<0.13`.
7. **The API reference** lists the modules of `ema.types` and `ema.designs`, not the root `ema`, whose lazy
   re-exports would document each error twice (Sphinx's ambiguous cross-reference warning). Napoleon renders a
   dataclass's "Attributes" as fields of the class, and type hints go in the signature, so each field is
   described once (0059 item 5).

**`ema.types`**

8. **One private module for reading numbers,** `ema.types._values` (`is_number`, `as_double`, `as_int`), used by
   layers 0 and 1, so 0065's refusals have one home: a bool is never a number; an integral float is accepted as
   an integer (3.0 as 3); a non-finite value is refused before it becomes a double.
9. **`Limits` and `ModelParameter.nominal` refuse a non-finite value** with `SpecError`, as they refuse a bool
   (the plan); the JSON form's checks stay step 03's.
10. **`ModelSpec.parameter` and `prediction` raise `RequestError`** for an unknown name, naming it and listing the
    model's names, since requests are what reach them.
11. **The space's array shapes,** which §3's stubs leave open: `to_unit` takes complete points `(n, d_all)` and
    gives `(n, d_varied)`; `from_unit` and `from_cube` take `(n, d_varied)` and give complete points; `contains`
    takes complete points, varied values in their closed ranges and held values exactly equal.
12. **Both forward maps clamp to [lo, hi] on every scale,** and set u <= 0 to lo and u >= 1 to hi exactly; a
    value strictly inside a linear range is still lo + (hi − lo)·u, bit for bit. **The map back clamps x to
    [lo, hi] first,** so no logarithm of a value at or below 0 is taken (the same as clamping z).
13. **`ModelParameterSpace`** refuses a name both varied and held; `parse` also accepts a `Range` and a `Scale`
    (the Python form); `canonical()` lists names alphabetically (the canonical JSON sorts them anyway).
14. **`DesignIdentity` is read-only all the way down:** nested mappings become read-only and lists tuples, and
    `canonical()` gives plain dicts and lists back for `canonical_json`.
15. **`Design`** checks that its points are `(n, d)` and its replicates `(n,)`, and makes both arrays read-only.
16. **The run id packs the replicate and the attempt as `<q`** (signed 8-byte little-endian: the same bytes as
    unsigned for the values allowed), and refuses a negative one. **`batch_call_id`** accepts hex text, 32-byte
    `bytes`, an `(n, 32)` uint8 array, or an array of 32-byte fixed-width bytes (read whole, so trailing zero
    bytes are kept), and refuses anything else.
17. **`duration` refuses a negative or non-finite value,** and rounds half up with `Fraction(repr(x))`
    (`decimal` isn't in `ema.types`'s list of imports).
18. **`ema.types/__init__.py` re-exports** every public name of its modules; **the root `ema`** re-exports the
    errors lazily from one table, listed by `__all__` and `__dir__`.

**`ema.designs`**

19. **Registries:** `register` of a taken name and `unregister` of a missing one raise `ValueError` (a mistake in
    a test or a later plugin, not a user's request); `get` of a missing one raises `RequestError`, "sampler X
    comes in a later version" or "design generator X comes in a later version".
20. **Generators and the `random` sampler are plain classes** with class attributes `name` and `version`, which
    mypy accepts for the protocols' attributes.
21. **What a generator refuses beyond the specs' list,** each with `RequestError`: an identity of another kind;
    an unknown parameter; `seed`, `sampler`, or a version among `params` (they are identity fields, 0061); a
    sampler named where none is used (point and lines) and none named where one is needed (uniform,
    convergent); a block outside the design's rows.
22. **Parameters' defaults in the generators:** a point's `x` (nominal) and `repeats` (0), coordinate lines'
    `anchor` (nominal), a given line's `anchor` (the center); every other parameter is required.
23. **The point design** compares its identity's space with `at_point(spec, x)` by their parsed canonical forms,
    so 50 and 50.0 agree.
24. **Convergent:** alpha is read from its decimal string or a float (both through `decimal_fraction`); a size
    whose estimate, from the logarithms of the exact integers, is over 2^62 is refused with `DesignTooLarge` at
    once; the exact sizes stop at the first one over the cap, with n_L computed exactly for the message, so a
    huge level costs nothing. Sizes not strictly increasing are refused naming alpha and n_min.
25. **Lines:** a line that meets the space at one point only (an anchor in a corner, pointing out) is refused;
    every coordinate whose clipping bound is the segment's end is set exactly to its face (a corner when
    several are); a given line's keys are `anchor` (optional) and `direction` (required), any other refused,
    and `lines` is a non-empty list.
26. **A random line's recorded anchor** is `from_cube(u)`, the `random` sampler's conversion, and its segment is
    built from z = 2u − 1 (as step 11's `random_line`); the norm is computed elementwise (plan).
27. **Blocks of a lines design** build only the lines that overlap the block; each line's ends come from its
    segment, so every line is recorded whole. Coordinate lines compute each line's own column to apply 0051's
    refusal.

**Tests**

28. **The design contract's model** is contracts.md's d = 3, with two values it doesn't give: `c` has the limit
    `gt 0` (so C27 can check that a refusal names the limit, M6), and h's nominal value is 0.5. Messages name a
    model parameter as "model parameter X", a limit as the spec writes it ("gt 0.0"), and the cap with
    thousands separators.
29. **The terminology test's generated text** is every string literal in `ema`'s source that isn't a docstring
    (error messages so far), with `EXPLAIN_INTERVALS`'s value exempt when it exists (0042); identifiers are
    split into words on underscores and camel case.
30. **The golden points** are recorded as literal doubles, the log line's included to its last bits.

## Deferrals

- **The 3.13 lowest-versions measurement** (task 7's scratch copy): deferred, as 0066 allows. The workflow's
  third job (`UV_PYTHON=3.13`, `UV_RESOLUTION=lowest-direct`) is written. Effort later: about 15 minutes, in a
  scratch copy of the repository (`UV_PYTHON=3.13 UV_RESOLUTION=lowest-direct uv sync`, then both tiers).
- **`STATUS.md`**: the coordinator's (0066).

## Spec edits on acceptance

None is required. Two clarifications would help later readers: `architecture.md` §3, the space's array shapes
(item 11); §4, the error each registry function raises (item 19).

## Alternatives considered

- **Ruff's narrower rule set of earlier versions** (E4, E7, E9, F): selectable, but 0059 says "Ruff's defaults".
- **Collecting `check_*` everywhere** (`python_functions`): collects a later `ema.models.files.check_files`
  imported by a test (the consistency review's BUILD-7).
- **A meta-test that counts only `AssertionError`:** C27's negative control, "builds before validating",
  fails by raising its own error, which is the failure the check exists to catch.
- **`RequestError` for `register` and `unregister`:** they aren't requests, and no user reaches them.

## Consequences

- **Size:** `ema.types` (this step's modules) 494 code lines, without docstrings, comments, blank lines, or the
  92 lines of re-exports in its `__init__.py`, near the plan's 505; `ema.designs` 496 against §11's 388 (lines
  230 against "about 150"). The projection for the whole of `v2.0` stays near the plan's 8,840, plus about 110
  for `ema.designs`: over `scope.md`'s 8,300, as the plan's question 6 expected; the budget record is the
  coordinator's to propose.
- `docs/guides/run_a_diagnostic.md`: its two code blocks with a literal `…` fixed as the plan says (the JSON
  block fenced as `text`; the Python block's `…` as `...`).
