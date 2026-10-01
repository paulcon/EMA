# Designs

**Status:** accepted. **Updated:** 2026-09-30 (the lines' spectra named by 0038; OD-12's questions answered by 0040). **Depends on:** OD-13 (0032); records 0005, 0012, 0013, 0023, 0024, 0033.

> The design generators in v2.0, from `../notes/v1/ema-redesign.md` and scope's Designs row (point, uniform,
> convergent, and lines: coordinate, random, or given; 0012). For each: what the user provides, the points it
> makes, how it uses the seed, its size in closed form, and whether a smaller design is a subset of a larger
> one (which is what lets stored runs be reused). Written from an interview on 2026-09-30 (TODO step 5).

## The model parameter space

- **A hyperrectangle** in v2.0: one range per varied model parameter. The glossary's hyperellipsoid (0005)
  comes later. The seam kept now: generators use the space only through its membership test, its unit map,
  line clipping, and sampling the unit cube, so another shape is one new class.
- **A subset of the model parameters** (0023): each model parameter the space names is varied over a range,
  or held at a value it gives; each one it leaves out is held at its nominal value.
- **Held value:** a number in place of a range holds that model parameter at that value for this design, not
  at its nominal value. It must be inside the model parameter's limits. The report's header lists it with the
  held model parameters, and figures skip it. Runs are keyed by the complete point, so designs that hold a
  model parameter at the same value share runs at their common points. A range must have lo < hi.
- **Scale** (0024): each range is linear (the default) or log. A log range needs lo > 0.
- **Limits** (0024, M6): both ends of each range, and each held value, must satisfy the model parameter's
  limits; with `gt: 0`, the range [0, 10] is refused and [1e-6, 10] is accepted. The check is made when the
  design is built, before any run, and names the model parameter and the limit.
- **Unknown names:** a name that isn't one of the model's model parameters is refused.
- **Column order:** a design's columns follow the model spec's order of model parameters, whatever order the
  space names them in, so the same space written in another order gives the same points.
- **Unit coordinates:** each varied model parameter maps to [−1, 1], through its logarithm when its scale is
  log (so the geometric midpoint maps to 0). Held model parameters have no unit coordinate.

### JSON form

What the CLI's `--space` file, the MCP tools, and the store use, and what is hashed. The Python form follows
it (`architecture.md`, step 9).

```json
{
  "k": [30, 60],
  "E": {"range": [1e9, 1e12], "scale": "log"},
  "h": 0.01
}
```

A two-element list is a linear range; an object gives a range and a scale; a number holds the model parameter
at that value.

## Shared rules

- **Seeds:** a seeded generator takes the seed from the request; when the request gives none, the seed is 0,
  as in v1, and is recorded (P4, P5). Two requests without a seed get the same points, so they reuse runs.
- **Size:** every generator computes its size in closed form, from the request alone, before building. A
  design of more than 10,000,000 points is refused then, with `DesignTooLarge` naming the size and the cap.
  At the cap, a design of 20 model parameters is 1.6 GB of points, and pricing hashes every point.
- **Determinism** (G1): the same request gives the same points, bit for bit. The `random` sampler builds its
  doubles from PCG64's raw output, which numpy keeps stable across versions (NEP 19), so a design's points in
  the unit cube, and its points in linear ranges (lo + (hi − lo)·u), are the same across numpy versions and
  machines. A log range goes through `exp`, which can differ in the last bit between CPUs, so its points are
  promised only with the same machine and library versions (P4). So are random lines' directions, which use
  numpy's `Generator.standard_normal`: NEP 19 lets its stream change in a feature release. A golden-points
  test pins all of these; a change after an upgrade loses reuse, never correctness, since runs are keyed by
  their points.
- **Ready for chunked designs** (a later version): a design larger than the cap, built, priced, run, and
  analyzed a block of rows at a time. v2.0 keeps the seams:
  - every point is a function of the request and its row index, so rows [a, b) can be made without rows
    0 … a − 1;
  - each random line is drawn from its own stream, derived from the seed and the line's index;
  - a design's identity is its request (kind, space, generator parameters, seed, and generator version), not
    its points;
  - the size is closed-form (above).

  Adding chunked designs later is about one build step: about 50 lines in the generators, 100 in the runner's
  pricing and running by blocks, and 100–200 in the diagnostics that accumulate (scatter's figures from a
  subsample; the linear and polynomial fits by normal equations or an updated QR), with known answers that
  chunked and whole give the same numbers; and a record for designs over the cap.

## Samplers

A sampler makes points in the unit cube [0, 1)ᵈ for the uniform and convergent designs (OD-13). v2.0 plans
for several and builds one.

- **The `sampler` field** is part of the uniform and convergent designs' requests, and so of the design's
  identity, with the sampler's version; points from two samplers are never mixed up. The default is
  `"random"`, the only value v2.0 accepts; any other name is refused with "sampler X comes in a later
  version".
- **The sampler interface** is the only way generators reach a sampler:
  - `name` and `version`, hashed with the request;
  - `unit_rows(seed, d, start, stop)`: rows [start, stop) of the sampler's sequence, so a block is made without
    the rows before it (chunked designs);
  - `nested`: whether the first n rows of a larger design are the n-row design;
  - `balanced_sizes`: the sizes at which it is balanced (any, or powers of 2);
  - `rate`: r, where an estimate's error from n points of the sampler is assumed to decrease like n^(−r);
    ½ for `random`, about 1 for Sobol. The convergent design's sizes use it.
- **Uniform** accepts any sampler; **convergent** requires a nested one, and refuses the rest.
- **`random`** (v2.0): PCG64 seeded from the request; row i is the raw 64-bit draws i·d to i·d + d − 1, each
  converted to (x >> 11)·2⁻⁵³, the same as numpy's `Generator.random` today. Nested for every n; row i is
  reached with `advance(i·d)`; balanced at any size; rate ½. About 15 lines, and 20 for the interface and
  the refusal.
- **Tested** with a fake sampler registered in the tests: uniform uses it, and convergent refuses it when it
  isn't nested, so the seam works without shipping a second sampler.

Later samplers (none adds a dependency; scipy is already one):

| Sampler | Effort later | Nested? | Notes |
|---|---|---|---|
| Sobol (`scipy.stats.qmc`, scrambled) | 30–50 lines, a record, known answers (discrepancy below `random`'s) | yes | balanced at 2ᵏ, so convergent's sizes need a rule |
| Halton | about 20 lines on top of Sobol | yes | any size |
| Latin hypercube | about 20 lines | no | uniform only; no reuse between sizes |
| minimum-distance (`../notes/v1/20260923.md`) | a small step, with its rejection rule and a record | no | uniform only |

## Generators

| Generator | User provides | Points | Size | Nested? | Seeded? |
|---|---|---|---|---|---|
| point | a point (nominal), repeats (0) | the point, as replicates 0 … repeats | repeats + 1 | yes, in repeats | no |
| uniform | space, n, sampler (`random`) | n points of the sampler, mapped to the space | n | yes, with a nested sampler: the first n rows | yes |
| convergent | space, n_min, alpha (error factor), level, sampler (`random`) | levels 0 … L: the first n_l points of one uniform design | n_L = ⌈n_min · alpha^(−L/r)⌉ | yes, in level | yes |
| given lines | space, lines (anchor, direction each), n | n evenly spaced points on each line, end to end inside the space | (number of lines)·n | in n → 2n − 1 | no |
| coordinate lines | space, n, anchor (nominal) | one line per varied model parameter, through the anchor | d·n (d varied) | in n → 2n − 1 | no |
| random lines | space, m, n, seed | m lines through uniform anchors, in uniform directions | m·n | in m; in n → 2n − 1 | yes |

### Lines

Shared by given, coordinate, and random lines (0012):

- **In unit coordinates.** A line is straight in the unit cube, so along a log-scale model parameter its points
  are spread evenly in the logarithm. Held model parameters keep their values along every line.
- **End to end.** The line's segment is where it meets the space; its n points are at t_j = j/(n − 1),
  j = 0 … n − 1, of the way from one end to the other, both ends included. Evenly spaced points are what the
  lines' spectra need (Gram polynomials, `diagnostics/coordinate_lines.md`). An end on a face of the space is exactly that range's end (lo or hi). n ≥ 2.
- **Refining:** since t_j = j/(n − 1), a line of 2n − 1 points contains the line of n points, bit for bit, so
  refining 17 → 33 points reuses all 17 runs.
- **Rows and runs:** the size counts rows, line by line. Rows at the same point (lines crossing at a shared
  anchor) share one run, and the price counts distinct points.
- **Recorded** with the design, for each line: its anchor, its direction, and its two ends.

**Given lines** (the lines diagnostic, U2's line through a kink): `lines(space, lines, n)`, where each line is
an anchor and a direction.

- **The anchor** is in model parameter units, a partial mapping; unnamed varied model parameters are at the
  space's center, held ones at their held values. It must be inside the space. The anchor is on the line, but
  is one of its points only if it falls on the grid t_j.
- **The direction** is in unit coordinates (`{"k": 1, "q": -0.5}`); unnamed components are 0. It must be
  nonzero, and may not name a held model parameter or a name that isn't a model parameter.

**Coordinate lines** (U2): `coordinate_lines(space, n, anchor)`, one line per varied model parameter, in the
model spec's order, each varying that model parameter over its whole range with the others at the anchor's
values.

- **The anchor** is a partial mapping in model parameter units; unnamed model parameters are at their nominal
  values (held ones at their held values). It must be inside the space: when a nominal value is outside its
  range, the request is refused, naming it, and the anchor has to be given.
- **Shared anchor:** when n is odd and the anchor's unit coordinate along a line is 0 to within 10⁻¹² (the
  range's center; the geometric center for a log range), that line's middle point is set exactly to the
  anchor's value. All other coordinates are the anchor's values exactly, so lines that each meet this rule
  share the anchor's run; the anchor is the only point two coordinate lines can share. U2 (nominal values at
  the centers, n = 17, 6 model parameters) has 102 rows and 97 distinct points. A line along which the anchor
  is off center, or any line when n is even, doesn't contain the anchor, and shares no point with the others;
  the coordinate lines spec (step 6) says how the report shows it. The 10⁻¹² is a named constant.

**Random lines** (the lines diagnostic): `random_lines(space, m, n, seed)`.

- **Each line has its own stream,** derived from the seed and the line's index j (numpy's `SeedSequence`,
  spawn key j, P4), so m lines are the first m of m + 1, and line j can be made alone (chunked designs).
- **The anchor** is uniform in the space: d draws from the line's stream, converted as the `random` sampler's
  are.
- **The direction** is uniform on the sphere in unit coordinates: d standard normals from numpy's
  `Generator.standard_normal` on the same stream, after the anchor's draws, divided by their norm.
- **The line** is clipped to the space, with n points end to end (above). The anchor is generally not one of
  them.

### Point

- **Request:** `point(x, repeats)`. `x` maps some model parameters to values, in the form of a space's held
  values (`{"k": 50}`); the rest are at their nominal values, and with no `x` the point is the nominal point.
  Each value must be inside its model parameter's limits. A name that isn't a model parameter is refused. No
  model parameter space (U7).
- **Replicates** (0011): `repeats = k` makes the point with replicates 0 to k. Replicate 0 is the ordinary run
  at that point, reused when stored; replicates 1 to k are new runs, reused when the same repeats are asked for
  again. The generator's default is `repeats = 0`; the point run's spec (step 6) sets the diagnostic's.
- **Nested in repeats;** not seeded.

### Convergent

- **Request:** `convergent(space, n_min, alpha, level, seed, sampler)`. The generator knows nothing about
  fits: the linear and polynomial model specs (step 6) set n_min from the number of coefficients, and alpha's
  default, and the user may override both as diagnostic parameters.
- **alpha is an error factor:** 0 < alpha < 1, the factor by which each level should reduce the error of an
  estimate (`../notes/v1/ema-redesign.md`: "error factor alpha"). If a sampler's error decreases like n^(−r),
  reducing it by alpha takes alpha^(−1/r) times the points. The sampler declares r (Samplers); for `random`,
  r = ½, and n_l = ⌈n_min · alpha^(−2l)⌉.
- **Levels** 0 to L (`level = L`): L + 1 nested designs, with sizes

  n_l = ⌈n_min · alpha^(−l/r)⌉, l = 0 … L,

  each computed from n_min, not from the level before. Level l has the first n_l points of one uniform design
  with the same seed, space, and sampler, so the whole design is the uniform design of n_L points (U5:
  scatter's 200 points are its first 200). No diagnostic needs two levels for its variability interval, and
  none checks the observed rate against r (0040).
- **Exact rounding:** n_min is an integer ≥ 1; alpha is read as the decimal it is written as (`0.9` is 9/10,
  not the nearest double), and n_l is computed in exact rational arithmetic (for `random`, the exponent 2l is
  an integer), then rounded up, with no tolerance. A later sampler whose 1/r isn't an integer brings its own
  rounding rule, in its record.
  - alpha = 0.5: 18, 72, 288 (the error halves; 4× the points per level).
  - Doubling needs alpha ≥ 1/√2, rounded up: alpha = 0.7072 gives 18, 36, 72, 144, 288, 576, 1151 (0.7072⁻² =
    1.99947, so exactly the error factor asked for). alpha = 0.7071, or even 0.70710678, is just below 1/√2,
    and gives 18, 37, 73, 145.
- **Refused** before building: alpha outside (0, 1), sizes that aren't strictly increasing (n_min = 2, alpha =
  0.95: 2, 3, 3), and a sampler that isn't nested (Samplers). The report shows alpha, r, and the sizes.

## Requirements

| Id | Requirement | Test |
|---|---|---|
| G1 | The same request gives the same points, bit for bit; a different seed gives different points (P4). | Each generator built twice; golden points for fixed requests (the `random` sampler's unit rows, a linear range, a log range, random lines); seeds 1 and 2 differ. |
| G2 | Every point is inside the space, and inside every model parameter's limits. | Random requests to each generator, log ranges included: every point in the closed ranges; held values exact. |
| G3 | The size computed before building, from the request alone, equals the number of rows built. | Each generator over a grid of requests. |
| G4 | Where nesting is claimed, the smaller design's points are points of the larger, bit for bit: its first rows (uniform and convergent in n or level, point in repeats, random lines in m), or every other point of each line (lines refined n → 2n − 1). | Each claim in the Generators table, compared bit for bit. |
| G5 | A design over 10,000,000 points is refused before it is built. | A uniform request with n = 10,000,001: `DesignTooLarge`, and no array allocated. |
| G6 | Rows [a, b) of a design, made alone, equal those rows of the whole design. | For each generator, a block from the middle, compared bit for bit. |
| G7 | A convergent design's level l is the first n_l points of the uniform design of n_L points with the same seed, space, and sampler; n_l = ⌈n_min · alpha^(−l/r)⌉, in exact rational arithmetic from alpha's decimal. | n_min = 18, level 3: alpha = 0.7072 gives 18, 36, 72, 144; alpha = 0.7071 gives 18, 37, 73, 145; alpha = 0.5, level 2, gives 18, 72, 288; the points equal `uniform(n=n_L)`. |
| G8 | A convergent request with alpha outside (0, 1), sizes not strictly increasing, or a sampler that isn't nested is refused before building. | alpha = 1 and alpha = 0; n_min = 2, alpha = 0.95, level 2; the fake non-nested sampler. |
| G9 | A point design has the point, complete, with replicates 0 to repeats; unnamed model parameters are at nominal; a value outside its limits is refused. | `point({"k": 50}, repeats=3)` on the heat model: 4 rows, q at nominal, replicates 0–3; `{"k": -1}` with `gt: 0`: refused. |
| G10 | A line's points are evenly spaced in unit coordinates, from one face of the space to another; an end on a face is exactly that range's end. | A diagonal given line in a space with one log range: equal steps in unit coordinates; ends exactly lo or hi. |
| G11 | A line of 2n − 1 points contains the line of n points, bit for bit. | n = 17 and 33, for each kind of line. |
| G12 | With n odd, the coordinate lines along which the anchor is at the center share the anchor exactly; the other lines, or all of them when n is even, share no point. | 6 model parameters, n = 17: 102 rows, 97 distinct points; the anchor off center in one model parameter: 98 distinct; in all six: 102; n = 16: 96 rows, 96 distinct. |
| G13 | Random lines: the first m lines of m + 1 are the m-line design; line j made alone equals line j of the whole. | m = 5 and 6, seed 1; line 3 alone. |
| G14 | A line request is refused, before building, for an anchor outside the space (including a nominal value outside its range, for coordinate lines), a zero direction, a direction naming a held model parameter or an unknown name, or n < 2. | One request for each. |
| G15 | A space is refused, before any run, for a name that isn't a model parameter, lo ≥ hi, a log range with lo ≤ 0, or a range end or held value outside the limits, naming the model parameter (M6). | One space for each; [0, 10] with `gt: 0` refused, [1e-6, 10] accepted. |
| G16 | A design's columns follow the model spec's order, whatever order the space names them in. | The same space with its names in two orders: identical points. |
| G17 | A sampler other than `random` is refused as coming later; a sampler registered in the tests works with uniform, and convergent refuses it when it isn't nested. | `sampler="sobol"`; a fake nested sampler and a fake non-nested one. |

## What this spec asks of other documents

- **Glossary** (accepted): the amended "model parameter" row, and rows for design generator, sampler, and
  nested (0033; applied 2026-09-30).
- **Diagnostic specs (step 6):** each diagnostic's design parameters and defaults: the linear and polynomial
  models' n_min and alpha; the point run's repeats; coordinate lines' n and what the report shows when the
  lines share no point; the lines diagnostic's m, n, or given lines. Reports list held model parameters.
- **Uncertainty (step 7):** answered by 0040 (OD-12): no diagnostic needs two or more levels of a convergent
  design for its interval, and none checks the observed rate against the sampler's r.
- **Contracts (step 7):** the design generator contract, from G1–G17.
- **Data model (step 8):** a design's identity is its request (kind, space, generator parameters, seed,
  sampler and version, generator version), not its points; runs are keyed by complete points.
- **Architecture (step 9):** `Box` becomes the model parameter space's type (the glossary avoids "box"), with
  held values in place of zero-width ranges; the design generator registry; the sampler interface; the stubs
  follow this spec (`convergent` with an error factor, `lines` for given lines, no `plane`).

## Open questions

- None. Record 0033 (accepted) holds the held values, the glossary changes, and the sampler's `rate`.
