# 0044. Compare golden reports by their numbers to four digits; print ASCII minus signs and whole integers

**Date:** 2026-10-01. **Status:** accepted; its golden points amended by 0061 (across machines). **Resolves:** none (consistency review, Q2).

## Context

- **Five specs** (scatter, the linear model, the polynomial model, coordinate lines, lines) require a golden
  report "byte-identical" to the spec's mock report. S3 says "Every number in the report is
  `format(x, ".4g")` of the stored double".
- **The mocks can't be matched byte for byte.** Reviewers reproduced every printed number, but:
  - **Ids:** ids and hashes are placeholders. `R2@8e41` stands for `name@` and 12 hexadecimal digits, and a
    model's name is lowercase (`../design/model_interface.md`). Result and approval ids (`3f2a`) and the
    library versions in the provenance are placeholders too.
  - **Minus signs:** the mocks print a typographic minus (U+2212), where `format` writes an ASCII hyphen.
  - **Integers:** S3 taken literally prints a count of 20,000 as `2e+04` and seed 12345 as `1.234e+04`.
  - **Log ranges:** R3 has one. On one machine, numpy's exp and log differ from the C library's in 0.35% of
    R3's points, each by at most 1 unit in the last place (10⁶ points, 2026-10-01). The printed 4-digit
    numbers differ in none, but a value on a rounding boundary can flip its last digit between machines.
- **Within one machine,** P4 holds bit for bit. Rerun and reproduction (S10, U8) compare data cards and
  reports exactly, and nothing here changes that.

## Decision

We will:

1. **Compare a golden report by its structure and numbers.** The test renders the report on the reference
   model and parses it. It has the mock's sections, rows, labels, and notes, and each number is within one unit
   in the 4th significant digit of the mock's. Ids, hashes, dates, and library versions are not compared. The
   mock in the spec is the golden report: there is no separate golden file.
2. **Print an ASCII hyphen** for every minus sign in a report: `format`'s output, in numbers and exponents
   alike.
3. **Print integers in full.** Counts, design sizes, seeds, degrees, levels, and ids print exactly. S3's
   `format(x, ".4g")` applies to the other numbers: estimates, observations, and the space's ranges and held
   values.

## Alternatives considered

- **EMA's output, frozen as a golden file** after review against the mock, compared byte for byte with ids
  masked. Not chosen: a second artifact to keep, and it can fail between machines over a 1-ulp difference.
- **The printed numbers as exact strings:** the same parsing, with string equality. Not chosen: it can fail
  between machines on a rounding boundary.
- **The diagnostic result's doubles to a relative tolerance,** with layout checked separately. Not chosen: it
  tests the report text only indirectly; the stored doubles are already checked by the known-answer tests.
- **A typographic minus (U+2212) for a leading sign:** nicer type, but a rendering rule beyond `format`, and
  S3's parse test would have to accept it.

## Consequences

- **`../design/diagnostics/shared.md`** (accepted):
  - Numbers (line 37) and S3: "Every computed number in the report is `format(x, ".4g")` of the stored double,
    with an ASCII minus; counts, sizes, seeds, degrees, and levels are printed in full; ids and hashes are not
    numbers."
  - S3's test: "parse the report's numbers, skipping ids and hashes; compare with the diagnostic result".
  - A "Golden report" definition, as Decision 1, which the five specs cite.
- **The five diagnostic specs** (accepted): each golden-report row's "byte-identical (golden report)" becomes
  "golden report (`shared.md`: structure, and numbers within one unit in the 4th digit)". The data cards'
  byte identity on rerun (S10) is unchanged.
- **The mock reports** (in all six diagnostic specs and `shared.md`): U+2212 becomes an ASCII hyphen inside
  the mocks. Spec prose keeps U+2212.
- **`../design/designs.md`:** unchanged. Golden points (G1) stay bit for bit on one machine, as the spec
  already says.
- **`../design/data_model.md`** (step 8): runs are reused by exact point keys, so a design rebuilt on another
  machine may make new runs where a log range's points differ by 1 ulp. Step 8 decides whether reuse across
  machines matters (for example, keying by design and row).
- **`../design/contracts.md`:** unchanged ("a golden report" in its list of spec tests now means Decision 1).
