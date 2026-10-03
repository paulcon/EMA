# 0067. Step 01's provisional choices: the scaffolding, the design types, and the design generators

**Date:** 2026-10-01. **Status:** accepted (2026-10-02, by the owner; drafted as proposed under 0066). **Resolves:** none.

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
5. **The meta-test counts only an `AssertionError` with the broken toy's expected message** (changed in review
   round 1, item 34; first, any exception counted): each broken toy is listed with the failure it must give,
   and a check's refusal helper turns any error other than `RequestError` into
   `AssertionError("built before validating")`, so C27's broken toy, which raises its own error before
   validating, fails for the intended reason and no other error passes the meta-test.
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
24. **Convergent:** alpha is read from its decimal string or a float (both through `decimal_fraction`); the
    sizes stop at the first one over the cap. Sizes not strictly increasing are refused naming alpha and n_min.
    (Corrected in review round 1, item 31: the first version's claim that "a huge level costs nothing" was
    false; near alpha = 1 its exact fractions grew with each level, and n_L was computed as a full power.)
25. **Lines:** a line that meets the space at one point only (an anchor in a corner, pointing out) is refused;
    every coordinate whose clipping bound is the segment's end is set exactly to its face (a corner when
    several are); a given line's keys are `anchor` (optional) and `direction` (required), any other refused,
    and `lines` is a non-empty list.
26. **A random line's recorded anchor** is `from_cube(u)`, the `random` sampler's conversion, and its segment is
    built from z = 2u − 1 (as step 11's `random_line`); the norm is computed elementwise (plan).
27. **Blocks of a lines design** build only the lines that overlap the block; each line's ends come from its
    segment, so every line is recorded whole. Coordinate lines apply 0051's refusal from the few points near
    the anchor (review round 1, item 37).

**Tests**

28. **The design contract's model** is contracts.md's d = 3, with two values it doesn't give: `c` has the limit
    `gt 0` (so C27 can check that a refusal names the limit, M6), and h's nominal value is 0.5. Messages name a
    model parameter as "model parameter X", a limit as the spec writes it ("gt 0.0"), and the cap with
    thousands separators.
29. **The terminology test's generated text** is every string literal in `ema`'s source that isn't a docstring
    (error messages so far), with `EXPLAIN_INTERVALS`'s value exempt when it exists (0042); identifiers are
    split into words on underscores and camel case.
30. **The golden points** are recorded as literal doubles, the log line's included to its last bits.

**Review round 1** (2026-10-02; the independent review's M1, m1–m6, m8, and nits)

31. **Convergent's sizes, exact and cheap** (M1; G3, G5, G7, C24). A request whose n_min + L is over the cap is
    refused with `DesignTooLarge` before any size is computed, naming n_min + L: strictly increasing sizes give
    n_L >= n_min + L. Each n_l is then the exact rule's, computed in one of two ways. A float estimate,
    n_min·exp(l·ln f) with ln f from `log1p` near 1 (f = alpha^(−1/r)), is used when it is at most 2^52 and the
    interval of relative half-width 10^−12 around it holds no integer: its error is below about 200 ulps
    (4.4·10^−14), so its ceiling is the exact one. Otherwise n_l is exact: from the integers n_min·num^l and
    den^l for a small power, else from fixed-point bounds on f^l by repeated squaring, rounded down and up,
    refined (from 128 bits, doubling) until both round up to the same integer; that ends, since for l >= 64,
    den^l > n_min and n_min·f^l isn't an integer. A long run of levels costs a float each; the exact powers are
    O(log l) operations. Over the cap, n_L is computed the same way, unless its logarithm puts it over 2^62:
    then it is refused naming the first size over the cap and its level (n2). The refusal of sizes not strictly
    increasing shows the last five. The sizes equal the plain rational rule's over 17 alphas, 9 values of
    n_min, and up to 3,000 levels (`test_g7_the_sizes_equal_the_exact_rule_for_many_alphas_and_levels`), and a
    timed test answers the review's cases at once. `designs.md`'s rule ("computed in exact rational arithmetic
    … with no tolerance") is kept in its results; the float is only a path to them that is proved to agree.
32. **`check_identity` returns the seed as an `int`** (an integral float, 3.0, as 3), and every seeded generator
    draws from it (m1): random lines crashed on 3.0 (`spawned` refuses a float).
33. **Convergent refuses alpha text that isn't a decimal number** (digits, an optional point, an optional
    exponent: "1/3", " 0.5 ", "0x0.8" refused), and reads a numpy float as its double (m2, 0047).
    `decimal_fraction` itself is unchanged (`identity.py` is left for the merge with step T; Deferrals).
34. **The meta-test** (item 5's new form; m4): every broken toy has its expected failure, the design contract's
    as messages (C27's: "built before validating"), the sampler contract's likewise.
35. **C21's check of a line's ends** (m3; G10): for each end, every coordinate whose clipping bound is that
    end's t, found from the recorded anchor and direction, is exactly its face (lo or hi), and the ends are the
    first and last rows. Run over the contract's examples, random lines (m = 50, five seeds, two spaces), and
    the review's given line in [−1, 1]²; removing the near-end rule, the far-end rule, or the t = 1 override
    now fails a test.
36. **C28's hash check** (m5): the design's identity, built from the registry as the workspace will, holds the
    sampler's name and version, and the uniform generator refuses an identity of another sampler version,
    naming it. The meta-test registers each broken toy for the check.
37. **Lines' `size` makes `build`'s checks** (m8): given lines make each line's segment (O(d) a line, no
    points), coordinate lines apply 0051. **Coordinate lines' 0051 check** makes only the points within two
    steps of the anchor's place, round((z + 1)/2·(n − 1)) (m6): a line's points are nondecreasing from lo to
    hi, so a point equal to the anchor is there. Tested against every point of every line as an anchor, n up
    to 41, and the doubles beside each.
38. **Nits:** a line meeting the space at one point is named in the refusal (n1); `read_params` says
    "diagnostic parameter" (n3, the glossary); a linear range whose width hi − lo overflows is refused (n4);
    `Design` documents that its arrays are read-only views of those it is given, not copies (n6: a design's
    10,000,000 rows aren't held twice); a block's bounds are integers, numpy's included, never bools (n7); the
    terminology test scans a Protocol's attributes (n5); the map back's clamp at x <= 0 on a log range is
    tested (n10).

**Review round 2** (2026-10-02; the minor findings left from wave 1)

39. **Alpha's exponent is never expanded** (G5, C24): the text is read first as a `Decimal`, its exponent an
    integer; alpha ≤ 0 or ≥ 1 is refused there, an exponent past `Decimal`'s (10^18) is refused as not a number,
    and below 10^−1000 level 0 is (n_min,) and level ≥ 1 is `DesignTooLarge` (n_1 > 10^2000 at r = 1/2), so
    "1e-10000000" no longer builds 10^(10^7) (`test_g5_c24_an_alpha_with_a_huge_exponent_is_answered_at_once`).
40. **The float path's precision is pinned** (G7): long runs near alpha = 1 (up to 693,000 levels) equal an
    80-digit `decimal` reference, and with ln f from `log` instead of `log1p` two sizes of n_min = 3,401,420,
    alpha = 0.99999284 are one too small (a negative control); `_power_bounds` brackets the exact power over
    2,000 random cases, bits from 1, and `_ceil_size` takes its starting bits (from 8 it refines to 16).
41. **Nits:** the n_min + L refusal says the design "would have at least … if its sizes strictly increase"; an
    echoed alpha text is cut to 40 characters and "…".

## Deferrals

- **The 3.13 lowest-versions measurement** (task 7's scratch copy): deferred, as 0066 allows. The workflow's
  third job (`UV_PYTHON=3.13`, `UV_RESOLUTION=lowest-direct`) is written. Effort later: about 15 minutes, in a
  scratch copy of the repository (`UV_PYTHON=3.13 UV_RESOLUTION=lowest-direct uv sync`, then both tiers).
- **`STATUS.md`**: the coordinator's (0066).
- **A block of a lines design still makes every line** (review round 1, m6): a block's `Design` records the
  whole design's lines (the plan's Choices), so each block makes all m lines' segments and records (for random
  lines, m spawned streams: O(m·d)); only the lines that overlap the block have their points made. Effort later:
  about 1–2 hours, to make the lines once per design (the runner keeps the `DesignStructure` and asks the
  generator for points only); the seam is `_lines`, which takes the segments and records apart from the block.
- **Hand-off to roadmap step 09 (parsing the diagnostic parameters):** the same design must never have two
  identity hashes (`data_model.md` §3.4). The generators read n = 3.0 as 3, a float alpha as its decimal, and
  integers in `x`, an anchor, a direction, or the space as doubles, so `DesignIdentity`s that differ only so
  build the same design and hash differently. Step 09 canonicalizes the identity before hashing (integers as
  integers, alpha as its decimal string, model parameter values and directions as doubles), with a test there
  that such pairs get one hash. Also for step 09 (or step T, which owns `identity.py`): `decimal_fraction`
  accepts "1/3" and padded text, and refuses a numpy float; convergent now refuses the first two and accepts
  the third itself (item 33), and whether `decimal_fraction` should is that step's choice.

## Spec edits on acceptance

None is required. Two clarifications would help later readers: `architecture.md` §3, the space's array shapes
(item 11); §4, the error each registry function raises (item 19).

## Alternatives considered

- **Ruff's narrower rule set of earlier versions** (E4, E7, E9, F): selectable, but 0059 says "Ruff's defaults".
- **Collecting `check_*` everywhere** (`python_functions`): collects a later `ema.models.files.check_files`
  imported by a test (the consistency review's BUILD-7).
- **A meta-test that counts any exception** (round 0's item 5): it let a check pass the meta-test by crashing
  for any reason; review round 1 replaced it (item 34).
- **Copying a design's arrays** (n6): safe against a caller's later writes, but holds 10,000,000 rows twice.
- **Bounding L by a constant** instead of item 31's estimate (M1): simpler, but refuses designs inside the cap.
- **`RequestError` for `register` and `unregister`:** they aren't requests, and no user reaches them.

## Consequences

- **Size after review round 1:** `ema.designs` 556 code lines (convergent 131, lines 226), from 496: item 31's
  exact-and-cheap sizes are about 60 lines. The budget record is the coordinator's (m7).
- **Size:** `ema.types` (this step's modules) 494 code lines, without docstrings, comments, blank lines, or the
  92 lines of re-exports in its `__init__.py`, near the plan's 505; `ema.designs` 496 against §11's 388 (lines
  230 against "about 150"). The projection for the whole of `v2.0` stays near the plan's 8,840, plus about 110
  for `ema.designs`: over `scope.md`'s 8,300, as the plan's question 6 expected; the budget record is the
  coordinator's to propose.
- `docs/guides/run_a_diagnostic.md`: its two code blocks with a literal `…` fixed as the plan says (the JSON
  block fenced as `text`; the Python block's `…` as `...`).
