# Reference models

**Status:** empty. **Updated:** <YYYY-MM-DD>.

> The models v2 is developed and verified against, each with the answers a correct diagnostic must give. With
> these, "done" means "matches what was worked out independently", not "the tests Claude wrote pass". Each
> diagnostic spec's "Expected answers" table refers to these ids.

| Id | Model | Interface | d | Structure it has | Why it's here | Source of the expected answers |
|---|---|---|---|---|---|---|
| R1 | linear, e.g. f = 3a − 2b + 0.5c | Python | 3 | exactly linear | known coefficients | analytic |
| R2 | Ishigami | Python | 3 | interactions; one negligible first-order effect | the standard sensitivity test | analytic Sobol indices |
| R3 | borehole | Python | 8 | a few important parameters; smooth | a realistic engineering formula | literature; brute force |
| R4 | constant, and constant plus rounding noise | Python | 3 | none | no data, no claims | trivial |
| R5 | a model that fails in part of its range | Python | 2 | failures in a known region | failed runs | by construction |
| R6 | a noisy model | Python | 2 | known noise level | noise handling | by construction |
| R7 | a model with a jump or kink | Python | 2 | a known location | nonsmooth features | by construction |
| R8 | <a command-line model: v1's `runoff` or `beam`> | command line | <…> | <…> | the input-deck path | <…> |
| R9 | <one real simulator: SWMM, MODFLOW, or Cantera> | command line | <…> | <…> | a real case | <…> |

## Expected answers

> Per model, the quantities the diagnostics in v2.0 must reproduce. v1's `src/ema/testfunctions/truth.py`
> computes Sobol indices, linear R², directions, and pair interactions for its test functions, and can be
> reused as the independent source.

### R1

| Quantity | Value | Tolerance | Source |
|---|---|---|---|
| <…> | <…> | <…> | <…> |
