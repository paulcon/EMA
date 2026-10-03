# Lines

**Status:** accepted. **Updated:** 2026-10-01 (step 11, 0058); 2026-10-02 (`m`'s default, 0077; review round 1 of
applying 0066–0085). **Module:** `ema/diagnostics/lines.py`. **Depends on:** `shared.md`; `coordinate_lines.md`;
`../designs.md`; records 0012, 0034, 0035, 0036, 0038, 0044, 0048, 0049, 0051, 0052, 0058, 0077.

> The model prediction along m random lines, or along lines the user gives, and the spectrum of each line
> (0012; U2's finer line through a kink). Written from an interview on 2026-09-30 (TODO step 6). Each line is
> analyzed as a coordinate line is (`coordinate_lines.md`); this spec states what differs. Everything not
> stated here follows `shared.md`.

## Summary

| | |
|---|---|
| **User provides** | a model parameter space; m random lines (5) and a seed (0), or given lines (an anchor and a direction each); n (17); the model prediction |
| **Design** | random lines, or given lines (`../designs.md`): n evenly spaced points on each line, end to end in the space |
| **Compute** | for each line, its Gram spectrum and decay rate, as coordinate lines, and its length; observations only, no estimates |
| **Plots** | for each line, one PNG: the model prediction against the distance along it, and its Gram spectrum |
| **Report** | where each line runs (a table of its ends); for each line, its length, range, degrees above the floor, and decay rate; the shared observations; a note per constant line; the figures |

## Parameters

| Name | Type | Default | Meaning | Changes the design? |
|---|---|---|---|---|
| `space` | model parameter space | required | the ranges varied, and the values held (`../designs.md`) | yes |
| `m` | integer ≥ 1 | 5; none with `lines` | the number of random lines | yes |
| `lines` | list of lines, each `{"anchor": {...}, "direction": {...}}` | none | given lines, in place of random ones | yes |
| `n` | integer ≥ 7 | 17 | the number of points on each line, end to end | yes |
| `seed` | integer ≥ 0 | 0 | the random lines' seed; recorded, and unused, with given lines | yes (random lines) |
| `prediction` | model prediction name | the only one | the model prediction analyzed (0022) | no |

- **Two modes, one request:** with `lines`, the design is those lines, `lines(space, lines, n)`; without it, m
  random lines, `random_lines(space, m, n, seed)`. A request with both `lines` and `m` is refused before
  building. `m`'s default is a rule: none when `lines` is given, 5 otherwise (`null` in MCP's JSON is none); the
  canonical request holds `m: null` with given lines, or `lines: null` with random ones, and the Provenance line
  leaves out the one that is none (`shared.md`; 0077 items 10, 11).
- **A given line** (`../designs.md`, Given lines): the anchor in model parameter units, a partial mapping,
  unnamed varied model parameters at the space's center and held ones at their held values; the direction in
  unit coordinates (`{"a": 1, "e": 1}`), unnamed components 0. Refused before building: an anchor outside the
  space, a zero direction, or a direction naming a held model parameter or an unknown name (G14). U2's finer
  line through a kink is one given line in a narrower space.
- **m = 5** (`LINES_M`): 85 runs at n = 17; random lines share no points. v1's nonsmoothness diagnostic also
  used 5 lines.
- **n = 17** (`LINES_N`), as coordinate lines, in both modes; a finer line sets n = 33 or 65. n ≥ 7
  (`COORD_MIN_N`), refused below before building.
- **A space with no varied model parameter** is refused before building.
- **Numbering:** lines are numbered from 0 in the report and the file names: random lines by their stream index
  j, given lines in the order given.
- **Nested:** random lines in m (the first m of m + 1, G13) and in n → 2n − 1 (G11); given lines in n → 2n − 1.
- **No draws of its own:** the random lines' anchors and directions come from the design's streams (spawn keys
  j); the diagnostic draws nothing (`shared.md`, spawn tags).

## Computation

Each line has n points, evenly spaced from one end to the other in unit coordinates; its own parameter is
s_j = −1 + 2j/(n − 1), j = 0 … n − 1, whatever its direction.

- **Gram spectrum, decay rate, degrees above the floor:** exactly as coordinate lines, in s
  (`coordinate_lines.md`, Computation): the same Lanczos computation, tail, window ⌊(n − 1)/2⌋, floor
  10⁻¹⁰ of the line's range, and `LINE_RATE_MIN_DEGREES`.
- **Length:** the distance between the line's ends in unit coordinates, from 0 up to the diagonal of [−1, 1]^d,
  2√d (0049). A new observation: the rate is per degree along the line's own span, and a shorter segment of an
  analytic function decays faster. On R11 at n = 33, lines of length 2.00, 1.39, and 0.70 have rates 0.209,
  0.362, and 0.743.
- **No summary across lines:** no minimum, median, or interval over the m rates. The lines differ in length and
  in the features they cross (R7's short lines miss the kink and the jump, and keep rates of 0.6–1.2 that don't
  change with n; the long ones that cross the jump halve), so a summary mixes them; and the rates change with n,
  which a bootstrap over lines wouldn't show (R2's median rate over 20 lines: 0.381 at n = 17, 0.620 at n = 33).
  Considered and not chosen: the minimum, median, and maximum as observations; the median as an estimate with a
  bootstrap over the lines.

**Observations for each line** (0034), in line order, one table:

| Observation | Definition |
|---|---|
| Usable | the line's usable runs, "17 of 17" |
| Length | as above, in unit coordinates |
| Range | max − min of the line's usable runs, in the model prediction's units |
| Degrees above the floor | "k* of K" |
| Decay rate | in decades per degree; or "none" and why |

**Where each line runs:** a table with one row per varied model parameter, in the model spec's order, and one
column per line, each cell "from → to" in model parameter units, from the line's start (t = 0) to its end
(t = 1). At most 5 lines per table (`LINES_TABLE_COLUMNS`); more lines make more tables, so the table's width
doesn't grow with m or d. The lengths are in the observations table, not repeated here.

- **Runs not usable on a line, a constant line, k* < 3:** as coordinate lines: no spectrum or rate for a line
  with any run not usable ("none: 2 runs not usable"); a note for each constant line ("y is the same in all 17
  usable runs along line 1: 1."); k* in its column.
- **Changes of units** (P6): y → a·y + b, with a > 0, leaves the degrees and notes unchanged, and the rates
  within 10⁻¹² under a·y alone and within `RATE_SHIFT_TOL` under the shift (0048), and scales the ranges by a.
  The lengths and ends don't depend on y.

## Uncertainty

OD-12, for lines: **none**, as coordinate lines (0038): each rate is an observation of the n runs on its line,
and there is no estimate across lines (above). A rerun at 2n − 1 points per line reuses every run.

## Minimum runs and degenerate cases

- **Fewest usable runs:** 1 (`COORD_MIN_RUNS`), for the shared observations; each line needs all its n ≥ 7 runs
  usable for a rate.
- **All runs failed:** counts by kind and the note; no observations (`shared.md`).
- **Constant** (every usable run of the diagnostic the same double; 0035): the shared note and observations;
  each line "none: constant"; no per-line notes.
- **A constant line,** when others vary: its note. On R10, given lines through the nominal point with
  directions (a, e) = (1, 1) and e: the second is constant, since e has no effect (0058).
- **A short line:** any length > 0 is analyzed; its length is in the table. A line always has length > 0: it is
  a line, not a ray, through an anchor inside the space, in a nonzero direction.
- **Given lines that coincide:** their points are the same, and so are their runs; each is still its own row.
- **Figures** (0051): one PNG per line in every case, with the same layout, as coordinate lines': a line's top
  panel shows its usable runs and the strip of the others; its spectrum panel is empty, with the reason, when the
  line has no spectrum.

## Figures

**`lines_<j>.png`,** one per line, in line order, with two panels:

- **Top, the line:**
  - **x axis:** the distance from the line's start in unit coordinates, 0 to its length, labeled
    `distance along line 1 (unit coordinates)`, so lengths compare across lines.
  - **y axis:** the model prediction, with this line's own limits (as coordinate lines).
  - **Points:** one marker per usable run, joined in order along the line.
  - **The anchor** of a given line: a vertical dotted line at its distance along the line. A random line's anchor
    isn't marked: it is only the draw that placed the line (its position is in the data card).
  - **Runs not usable:** × in the strip below the axes, at their distances (`shared.md`).
- **Bottom, the spectrum:** as coordinate lines (`coordinate_lines.md`, Figures): |c_k| / range on a log axis
  against the degree, any value below `SPECTRUM_YMIN` an open marker on the bottom edge (0048), the tail fit,
  the floor, the window; an empty panel with the reason when there is no spectrum.
- **No panel of the model parameters along the line:** each is linear in unit coordinates along it, and the
  ends table says from where to where.
- **Title:** "line j"; the numbers are in the tables.
- **Data card:** as coordinate lines', and the line's anchor, direction (unit coordinates), ends (model
  parameter units and unit coordinates), and length.

## Mock report

Random lines on R7 with the defaults: m = 5, n = 17, seed 0. The numbers are computed, drawing each line from
`SeedSequence(0, spawn_key=(j,))` as `../designs.md` says, and checked at step 11 by
`../../checks/gram_rates.py`; the hashes are placeholders.

```markdown
# Lines: R7, y

| | |
|---|---|
| Model version | R7@41d9 |
| Model prediction | y |
| Space | a [-1, 1]; b [-1, 1]; c [-1, 1]; e [-1, 1] |
| Held | none |
| Design | random lines, m = 5, n = 17, seed 0 |
| Runs | 85: 85 new, 0 reused; 0 failed; 0 missing y; 85 usable |

## Observations

| Of the 85 usable runs | y |
|---|---|
| Minimum | 0.2 |
| Maximum | 1.995 |
| (max - min) / max\|y\| | 0.8997 |

| Model parameter | Line 0 | Line 1 | Line 2 | Line 3 | Line 4 |
|---|---|---|---|---|---|
| a | 0.6198 → 1 | -1 → 1 | 1 → -1 | -1 → 1 | 0.2123 → 0.783 |
| b | -0.4175 → -0.3458 | -0.1497 → -0.6877 | -0.9938 → 0.003045 | -0.1718 → 0.3618 | -0.2506 → -0.8688 |
| c | 0.1892 → 0.5543 | -0.1069 → 0.381 | 0.1505 → 0.6742 | -0.1998 → 0.1157 | -1 → 1 |
| e | -1 → -0.6411 | 0.9332 → -0.672 | 0.3123 → 0.8897 | -0.3275 → -0.8983 | 0.0431 → 0.7265 |

| Line | Usable | Length | Range | Degrees above the floor | Decay rate (decades per degree) |
|---|---|---|---|---|---|
| 0 | 17 of 17 | 0.6417 | 0.4261 | 8 of 8 | 0.8166 |
| 1 | 17 of 17 | 2.665 | 0.3665 | 8 of 8 | 0.6447 |
| 2 | 17 of 17 | 2.367 | 1.274 | 8 of 8 | 0.2184 |
| 3 | 17 of 17 | 2.17 | 1.132 | 8 of 8 | 0.07052 |
| 4 | 17 of 17 | 2.275 | 1.102 | 8 of 8 | 0.1891 |

Length: in unit coordinates. Decay rate: minus the least-squares slope of log₁₀ of the Gram spectrum's tail
against the degree, over the degrees whose tail is above 10⁻¹⁰ of the line's range, at most K = 8.
Observations of the 17 runs on each line; no variability intervals.

## Figures

![y along line 0](lines_0.png) ![y along line 1](lines_1.png) ![y along line 2](lines_2.png)
![y along line 3](lines_3.png) ![y along line 4](lines_4.png)

y against the distance along each line, and the line's Gram spectrum, |c_k| / range, with the tail fit and the
floor of 10⁻¹⁰. Data cards: `lines_0.json`, `lines_1.json`, `lines_2.json`, `lines_3.json`, `lines_4.json`.

## Provenance

EMA 2.0.0; numpy 2.3.1, scipy 1.16.0, matplotlib 3.10.0; model version R7@41d9; request: lines, space as
above, m = 5, n = 17, seed 0, prediction y; runs: 85; approvals: 7e22 (85 new runs).
```

What the lines cross, for the reader of this spec (not in the report, P2): line 3 crosses the jump at b = 0.2
(0.07052); lines 2 and 4 cross the kink a + e = 0.6 (0.2184, 0.1891); lines 0 and 1 cross neither (0.8166,
0.6447).

## Expected answers

"Exact rational arithmetic" is the independent computation of `coordinate_lines.md`'s Expected answers (the
Gram coefficients in `fractions`, then the rate in doubles; `../../checks/gram_rates.py`). Rates with a
tolerance of 10⁻⁶ are given to 7 digits. The points of random lines are pinned by
`../designs.md`'s golden-points test.

| Reference model | Quantity | Expected | Tolerance | Source |
|---|---|---|---|---|
| R7, random, m = 5, n = 17, seed 0 | rate, lines 0–4 | 0.8166077, 0.6447274, 0.2184303, 0.07051713, 0.1891380 | 10⁻⁶ | exact rational arithmetic |
| R7, random, m = 5, n = 17, seed 0 | the report | the mock report above | golden report (`shared.md`: structure, and numbers within one unit in the 4th digit) and data cards | this spec |
| R11, random, m = 10, seed 0, n = 33, 65, 129 | each line's rate | log₁₀ ρ, ρ the Bernstein ellipse parameter of the line's segment through its nearest pole (a or b = ±i/2): 0.2090 for lines 0, 1, 3, 4, 5, 6, 9; 0.7532, 0.2555, 0.3568 for lines 2, 7, 8 | 0.02 (computed at n = 33, 65, 129: within 0.006 for the long lines, 0.012 for line 2) | analytic |
| R7, given: through the nominal point, direction (a, e) = (1, 1) | length; rate at n = 17, 33, 65 | 2√2 = 2.828; 0.2025713, 0.1082395, 0.05902797 | exact; 10⁻⁶ | analytic; exact rational arithmetic |
| R10, given: through the nominal point, directions (a, e) = (1, 1) and e, n = 17 | notes; k* and rate of each line | one note, "y is the same in all 17 usable runs along line 1: -0.559."; line 0: k* = 1, none; line 1: none: constant | exact | analytic: along line 0, y is linear; e has no effect, and y = 0.5·ψ₂(0) = −√5/4 (0058) |
| R1 and R10, random, m = 5, seed 0 | k*; rate | 1 (R1) and 2 (R10) on every line; none | exact | analytic: degree 1 and 2 along any line |
| R4a | notes; each line | the shared "constant" note only; none: constant | exact | trivial |
| R5, random, m = 5, n = 17, seed 0 | runs not usable, by kind; lines with no rate | the points in each region (`../reference_models.md`); "none: k runs not usable" on each line that has any | exact | by construction |
| R2, y → 2⁻¹⁰·y + 3 | rates; k*; notes; ranges | rates within `RATE_SHIFT_TOL` = 10⁻⁵; k* and notes identical; ranges × 2⁻¹⁰ | as stated | P6 |

## Named constants

| Name | Value | Meaning | Why this value |
|---|---|---|---|
| `LINES_M` | 5 | the default number of random lines | 85 runs at n = 17; R7's lines already split into smooth and nonsmooth ones |
| `LINES_N` | 17 | the default number of points per line, in both modes | as coordinate lines; a finer line sets its own |
| `LINES_TABLE_COLUMNS` | 5 | the most lines in one table of ends | a table readable at any m and d |

The rate's constants (`LINE_RATE_FLOOR`, `LINE_RATE_WINDOW`, `LINE_RATE_MIN_DEGREES`, `RATE_SHIFT_TOL`),
`SPECTRUM_YMIN`, `COORD_MIN_N`, and `COORD_MIN_RUNS` are coordinate lines', shared.

## Requirements

| Id | Requirement | Test |
|---|---|---|
| LN1 | The design is `random_lines(space, m, n, seed)`, or `lines(space, lines, n)` when lines are given; both `m` and `lines`, n < 7, or a space with no varied model parameter is refused before building, as are G14's cases. | Each mode equals its generator bit for bit; one refused request for each case. |
| LN2 | Each line's spectrum, degrees, and rate are computed as coordinate lines' (CL2, CL3), in the line's own parameter s. | R7's given line across the kink at n = 17, 33, 65. |
| LN3 | One observations row per line, in line order: usable, length, range, k* of K, rate; no summary across lines. | R7 random at the defaults (the mock report). |
| LN4 | The ends table: one row per varied model parameter in the model spec's order, one column per line, "from → to" in model parameter units, at most 5 lines per table. | R3 with m = 7: two tables, of 5 and 2 lines, 8 rows each. |
| LN5 | A line with any run not usable has no spectrum or rate; a constant line has a note; a constant diagnostic result has the shared note only. | R5 random at seed 0; R10's two given lines (0058); R4a. |
| LN6 | One PNG per line; the x axis is the distance along it, 0 to its length; a given line's anchor is marked, a random line's isn't. | R7 random: 5 PNGs, no anchor marks; R7's given line across the kink: a mark at distance √2. |
| LN7 | y → a·y + b (a a power of 2) leaves the rates within `RATE_SHIFT_TOL` = 10⁻⁵ under the shift, 10⁻¹² under a·y alone (0048), and k* and the notes unchanged, and scales the ranges by a. | R2 with a = 2⁻¹⁰, b = 3. |
| LN8 | Random lines nest in m, and every line in n → 2n − 1: the runs are reused. | R7: m = 6 after m = 5 makes 17 new runs; n = 33 after n = 17 makes 16 new runs per line. |
| LN9 | The known answers and the golden report. | Expected answers. |

## Tests it implies

- `shared.md`'s S4 has no table to check: lines have no Estimates section, as coordinate lines.
- The per-line computation is shared with coordinate lines, so its tests (CL2, CL3) cover both; LN2 checks the
  wiring.

## What this spec asks of other documents

- **`../reference_models.md` (step 11):** R7's given line's expected answers; R11's per-line rates from the nearest pole
  (done at step 11).
- **Architecture (step 9):** `random_lines.py` becomes `lines.py`, one diagnostic with two modes; the per-line
  computation shared with coordinate lines.
