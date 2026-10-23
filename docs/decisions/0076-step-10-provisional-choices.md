# 0076. Step 10's provisional choices: scatter's tables, figures, sampler reader, and column-wise estimators

**Date:** 2026-10-02. **Status:** accepted (2026-10-02, by the owner; drafted as proposed under 0066). **Resolves:** none.

## Context

Build step 10 (`../plans/10-scatter.md`) builds `ema.diagnostics.scatter` on step 09's base (record 0075), on
`demo-10-scatter`, without the owner's review (0066). `diagnostics/scatter.md` gives SC1–SC10, the estimates, the
bootstrap's differences, the figures, the mock report, and the expected answers; record 0073 gives the conventions
for text in results and the line under each table; record 0068 the numerics (`rank_correlation`, `binned_index`, no
vector-vector BLAS). A few details are open in the specs, and the first build was too slow for the fast tier: one
evaluation with the 1000-resample bootstrap took about 1 s at d = 3, and the contract runs about 55 evaluations.
Each choice below keeps P1–P7 and the specs' intent.

## Decision

We will, provisionally:

**The result**

1. **Three estimates tables,** as the mock prints them and step 08's golden test rebuilt them: `moments` (keys
   `mean`, `std`; labels "Mean", "Standard deviation"; the model prediction's units), `rank_correlation` (columns
   "Model parameter", "Rank correlation ρ", "Variability interval"), and `binned_index` ("Binned first-order index
   Sᵢ"; its title "14 bins." opens the line under it, record 0073 item 3; settings `distinct` "the index"). In the
   last two, each estimate's key and label is the model parameter's name, so `transform` declares both tables
   unchanged under y -> a·y + b rather than listing keys in `TRANSFORMS`. No observations of its own: the shared
   ones are the mock's.
2. **ρ and S are computed from the design's values in model parameter units,** not unit coordinates: the order is
   the same (scatter.md), and the figures' bins use the same values. SC3's test checks a log range against a
   linear one over the same unit coordinates: identical, bit for bit.
3. **Undefined resamples** (V4) are counted per estimate, keyed by the model parameter's name, in each table's
   line ("Undefined resamples, dropped: x1 349, x2 349."); the mean and standard deviation are never undefined.

**The diagnostic parameters**

4. **The `sampler` parameter's reader accepts any name,** and the design refuses one that isn't registered with
   G17's words ("sampler sobol comes in a later version", from `base.identity`); its JSON schema lists the
   registered samplers. Step 09's `Name` reader refuses before the design with other words, and C14 needs a
   parseable other value (`"sobol"`) whose design is refused. The reader is in `scatter.py`; the linear and
   polynomial models may want it in `base` (a move of 15 lines).
5. **The example request** is n = 20, seed 3: enough usable runs under the contract's failure masks, and a seed
   other than the seed parameter's other value (1).
6. **A space with no varied model parameter** is refused in `design_identity`, before any design is built:
   "scatter needs a varied model parameter: the space holds every one".

**The figures (scatter.md, Figures; 0051)**

7. **The y axis** of every scatter figure is the usable runs' range with 5% added at each end, so every figure of a
   report has the same limits (and the card records them); with no range (constant, one run, none) matplotlib's.
   The panel's title is the model parameter's name; the card holds `"parameter"`, and the panel's `"bins"`, one
   `{"x_lo", "x_hi", "n", "mean"}` per group of the index (the groups sorted stably, split as `array_split`).
8. **Bin means only with estimates** (the stored result's), as the degenerate cases say; the caption is then "y
   against each model parameter, with the means of the 14 bins of the binned index.", else "y against each model
   parameter.".
9. **The histogram only when the usable runs' y has a range:** none with no usable run or a constant model
   prediction (as specified), and none with one usable run (below the minimum, where the spec draws it; its one
   bin would have no width). Its card holds `"edges"` and `"counts"`, its y axis "number of runs"; its caption adds
   "The k runs not usable are not in it." when k > 0 (the spec: "the caption gives the number of runs not
   usable").
10. **A model parameter named `histogram`** is drawn as `scatter-histogram.png`: a name is an identifier, so no other
    model parameter's figure has a `-`, and the histogram keeps `scatter_histogram.png`.

**The numerics (`ema.numerics.stats`, step 02's module, used by scatter only)**

11. **Column-wise forms for the bootstrap:** `rank_correlations(X, y)` and `binned_indices(X, y, bins)` compute
    every varied model parameter's ρ and S in one pass, and `average_ranks(A)` ranks rows with numpy alone
    (scipy's `rankdata` costs about 0.1 ms a call in its array-API layer). `rank_correlation` and `binned_index`
    are their one-column cases. ρ is unchanged bit for bit (centered ranks are exact multiples of 1/2); S's group
    sums are `np.add.reduceat`'s (the first value plus numpy's pairwise sum of the rest), which may differ from
    `np.mean`'s in the last bit (94 of 2,000 random fixtures), and are the same at 8 memory offsets (tested). An
    evaluation at d = 3 went from about 1 s to about 0.2 s.

**Tests**

12. **Estimate-only tests use a fake interval method that calls no estimator** (`NoIntervals`, all intervals
    "none"); the golden report, SC5, and SC9's slow variant use the bootstrap. R5's timeout region raises the
    timeout at once in the tests (`reference._Timeout`), not after 0.2 s. The known answers at n = 20,000 are slow
    (about 1.3 s each). SC4's "seeds where it is negative": R1's c at n = 200, seed 10, S = -0.0297.

**Review round 1** (the independent review's three minors and a nit; fixed on `demo-diagfix`, each with a test)

13. **A model parameter named `histogram` in any case** (`Histogram`, `HISTOGRAM`) is drawn as `scatter-<name>`
    (amends item 10): `figure_name` compares `casefold()`, so on a case-insensitive disk (macOS's default)
    `scatter_Histogram.png` no longer overwrites `scatter_histogram.png`. Not changed: two model parameters whose
    names differ only in case (`a`, `A`) still share a figure file on such a disk; a model spec allows them (names
    are unique as written), and every diagnostic names figures after model parameters, so the rule belongs to the
    model spec's reader or to `ema.plotting.save`, not to scatter.
14. **The figures at one and two usable runs are tested** (item 9): one usable run, a panel per varied model
    parameter with its one point and its strip, no bin means, no histogram; two, the histogram too, of ⌊√2⌋ = 1 bin
    from the minimum to the maximum holding both, its caption counting the runs not usable.
15. **`rank_correlations`' "exact" is bounded** (nit; amends 0068 item 11, which this item 11 extends): the centered
    ranks' products and sums are exact while the sums of squares, about n³/12 in quarters, fit in 53 bits, so for
    n ≲ 3·10⁵; beyond that the column-wise and one-column forms may differ in their last bits. The docstring says so.
16. **The fast tier's bootstrap cost** (the third minor): the contract's checks that don't test the intervals use a
    lean fake (record 0084, Review round 1); scatter's contract share went from about 48 s to 15 s of test time.
17. **One reader for a registry's name** (amends item 4; step 13's review, record 0079 Review round 1): scatter's
    `SamplerName`, `_fits.SamplerName`, and the polynomial model's `Registered` were three copies with three JSON
    schemas (an `enum`, a pattern, `examples`). `ema.diagnostics.base.Name(samplers.names)` replaces them (step 09's
    `Name`, which refused an unregistered name in its own words and was used by no diagnostic): it reads any
    well-formed name (a letter, then letters, digits, `_`, `-`), refuses what isn't one naming the registered ones,
    and leaves an unregistered name to the registry's "sampler X comes in a later version" when the design is built.
    Its schema is `{"type": "string", "pattern": "^...$", "examples": [registered names]}`: not an `enum`, which a
    client would apply before EMA, refusing "sobol" in other words than G17's. Scatter's schema loses its `enum`.

## Deferrals

- **v1's numbers** were not run: the mock report's numbers, computed by `docs/checks/scatter.py` (an independent
  implementation), are reproduced to every printed digit, and the expected answers hold at n = 20,000.
- **The `sampler` reader in `base`** (item 4): when a second diagnostic needs it, about 15 minutes.

## Spec edits on acceptance

- **`diagnostics/scatter.md`, Figures:** the y limits (item 7), the cards' fields (items 7, 9), no histogram with
  one usable run (item 9), `scatter-<name>.png` for a model parameter named `histogram` in any case (items 10, 13),
  the captions (items 8, 9).
- **Record 0068, item 11:** `rank_correlations` equals `rank_correlation` bit for bit for n ≲ 3·10⁵ (item 15). Mock report: record 0073's
  edits (ρ, Sᵢ; "14 bins." first).
- **`architecture.md` §4 (`ema.numerics.stats`):** `average_ranks`, `rank_correlations`, `binned_indices` (item 11).
- **`designs.md`, G17:** the refusal comes from the design for a diagnostic parameter too (item 4).

## Alternatives considered

- **Unit coordinates for ρ and S** (item 2): the same numbers, one more mapping, and the figures would need the
  model parameter units anyway.
- **Keeping scipy's `rankdata` and per-column calls** (item 11): about 1 ms per resample at d = 3, 55 evaluations
  in the contract alone; the fast tier's 30 s would not hold.
- **Batching the 1000 resamples in one array** (faster still): needs a change to the bootstrap's interface
  (`Estimator.fn` takes one resample), which the linear and polynomial models share.
- **`Name(samplers.names)` for `sampler`** (item 4): refused "sobol" with another message, and C14 fails on it.
- **A histogram of one bin of width 1 around a single run** (item 9): a made-up width; nothing to read from it.

## Consequences

- **Size:** `scatter.py` 242 code lines (no docstrings, comments, or blanks) against the roadmap's 250;
  `ema.numerics.stats` 32 -> 59 (item 11).
- **Tests:** the fast tier gains 19 scatter tests (about 8 s serially) and 2 numerics tests, and the contract's
  19 checks over scatter (about 25 s serially on a loaded machine; `check_deterministic`'s 11 bootstraps the
  longest, about 3–5 s); the slow tier 5 (the known answers, R4b at n = 20,000, SC9 with intervals).
- Steps 12 and 13 may reuse `SamplerName` and the column-wise pattern for their bootstraps.
