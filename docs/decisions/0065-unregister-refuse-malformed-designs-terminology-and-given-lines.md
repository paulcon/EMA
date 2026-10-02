# 0065. Add `unregister` to every registry, refuse malformed design requests, check four more words, and settle a given line's anchor and direction

**Date:** 2026-10-01. **Status:** accepted. **Resolves:** none (plan 01's questions 1, 3, 4, and 5;
`../plans/01-scaffolding-and-designs.md`).

## Context

Writing plan 01 (the scaffolding, the design types, and the design generators), and three independent reviews
of it, found four things build step 01 needs that no accepted spec settles:

- **Removing a fake from a registry.** `../design/architecture.md` §4 gives each registry `register`, `get`, and
  `names`, and says a fake is "registered in the tests through the same `register`, removed by a fixture: no
  monkeypatching", and that a fixture registering a second version of a generator (C51) "removes the first and
  restores it". No public name removes an entry. The same holds for every registry: samplers, design
  generators, bases, interval methods, output parsers, and diagnostics.
- **Requests no spec refuses.** `../design/designs.md` refuses some cases (G5, G8, G9, G12, G14, G15, G17) and
  states lines' n ≥ 2 and convergent's n_min ≥ 1, but says nothing of:
  - uniform's `n < 1`, random lines' `m < 1`, a point's `repeats < 0`, convergent's `level < 0`, and a negative
    seed (numpy's `SeedSequence` refuses one with its own error); these ranges are in the diagnostics'
    parameter tables, in layer 3b, while the generators are in layer 1 and are called directly in the tests;
  - a range end, held value, point's `x`, anchor, or direction that is NaN, ±inf, a bool, or a string: G15's
    "lo ≥ hi" doesn't catch NaN, `canonical_json` would later fail with a bare `ValueError`, and an
    int-to-double conversion would turn `True` into 1.0;
  - a malformed space (a list of three, an unknown `scale`, an extra key in a range's object);
  - an `anchor` (coordinate or given lines) naming a name that isn't a model parameter: G14 refuses that only
    in a direction;
  - an empty list of given lines, which would make a design of 0 rows;
  - a convergent design with a sampler whose 1/r isn't an integer, whose rounding rule `designs.md` leaves to
    that sampler's record.
- **The terminology test's list.** Record 0008 says "a word joins the list when a decision record decides
  against it". Record 0061 (item 2) decided "user", not "analyst"; record 0057 (item 13) decided "model" over
  "user code", "model code", and "model program". The glossary's header lists none of them.
- **A given line's anchor and direction,** both shown in the lines diagnostic's data card (`lines.md`):
  - nothing says whether `Line.direction` holds the direction as given or normalized; random lines' directions
    are normalized draws;
  - the anchor's unnamed varied model parameters are "at the space's center" (`designs.md`, Given lines). On a
    log range the arithmetic center of [10⁻⁶, 10⁶] is 5·10⁵ (z ≈ 0.95), and the geometric center is 1 (z = 0).
    `designs.md` reads the center as geometric for unit coordinates ("the geometric midpoint maps to 0") and
    for coordinate lines' shared anchor.

The owner answered each question on 2026-10-01, choosing the suggested option, and accepted this record the
same day.

## Decision

We will:

1. **Give every registry `unregister(name)`,** beside `register`, `get`, and `names`: it removes the entry, and
   refuses a name that isn't registered. Test fixtures register a fake and unregister it; a fixture that
   replaces a registered entry (C51's second generator version) unregisters it, registers its own, and
   restores the original afterwards. It is for the tests and for a later plugin mechanism; nothing in `ema`
   calls it.
2. **Refuse malformed design requests in layer 1,** before building, with `RequestError` naming the parameter:
   - each generator's parameters outside its own floors: uniform's and random lines' `n`, `m` integers ≥ 1;
     lines' `n` ≥ 2 (G14); a point's `repeats` ≥ 0; convergent's `n_min` ≥ 1 and `level` ≥ 0; the seed an
     integer ≥ 0; a bool or a non-integral number where an integer is required. The diagnostics' own floors
     (lines' and coordinate lines' n ≥ 7) stay theirs;
   - in a space, a point's `x`, an anchor, or a direction: a value that isn't a finite number, a bool included,
     refused by `ModelParameterSpace.parse` or the generator, before the conversion to doubles (0061 item 6);
   - a malformed space: a list that isn't two numbers, a `scale` other than `linear` or `log`, a range's object
     with a key other than `range` and `scale`;
   - an anchor naming a name that isn't a model parameter, as G14 does for a direction;
   - an empty list of given lines;
   - a convergent design with a sampler whose 1/r isn't an integer, naming the sampler, until a sampler's record
     brings its rounding rule.
3. **Add four words to the terminology test's generated-text list:** "analyst", "user code", "model code", and
   "model program". The test still checks identifiers only for `qoi`, `box`, and `DiagnosticRun`, and scans no
   documents (0008).
4. **Settle a given line's anchor and direction:**
   - `Line.direction` holds the direction as the user gave it, in unit coordinates, unnamed components 0, not
     normalized; a random line's holds its normalized draw;
   - an anchor's unnamed varied model parameter is at the range's center in unit coordinates (z = 0; u = ½
     through the range's map), the geometric center for a log range: 1 on [10⁻⁶, 10⁶]. That value is
     `Line.anchor`'s, and stays bit for bit along any coordinate whose direction component is 0 (0062 item 4).

## Alternatives considered

- **Registries:** a context manager, `registered(x)`, that registers and removes on exit: tidy in tests, but
  a second shape beside `register`, and no use outside a `with`. `register` returning a remover: no new name,
  but a changed signature and a return value most callers ignore.
- **Refusals left to the diagnostics' parameter parsing** (step 09): fewer checks in layer 1, but the
  generators are called directly in the tests and by the design contract, where a size-0 or NaN design would
  pass silently; and a bad space value still needs a rule in the space's parse.
- **Terminology:** "analyst" only, or none, keeping the phrases as advice in the Avoid column. Text EMA
  generates is where a retired word does the most harm, and the test is cheap.
- **A given line's direction normalized,** as random lines' are: one form for every line, but the data card
  would no longer show what the user wrote ((1, 1) as (0.7071…, 0.7071…)).
- **The arithmetic center** on a log range: the plain reading of "center" in model parameter units, but it
  contradicts the unit coordinates' and coordinate lines' reading, and sits near the top of the range.

## Consequences

- **`../design/architecture.md`:** §4's registries and its tables (`samplers.py`, `generators.py`,
  `basis.py`, `intervals.py`) gain `unregister`; §5's parsers and §6's diagnostics registries likewise; §4's
  paragraph on fakes says fixtures unregister them; §3's `Line.direction` comment ("as given; a random line's
  normalized").
- **`../design/designs.md`:** Shared rules gain the refusals of item 2, as a new requirement G18 (a generator
  refuses parameters outside its floors, and malformed values) with its test; G14's test adds an anchor naming
  an unknown model parameter and an empty list of given lines; G15's test adds NaN, ±inf, a bool, and a string
  as a range end or held value, a list of three, an unknown scale, and an extra key; Given lines say the anchor's
  unnamed coordinates are at z = 0 (the geometric center on a log range) and the direction is kept as given;
  Convergent refuses a sampler whose 1/r isn't an integer.
- **`../design/contracts.md`:** C27's negative control unchanged; C27's row cites G18 beside G15.
- **`../design/glossary.md`:** the header's generated-text list adds the four words.
- **0008's status:** "accepted; its generated-text list amended by 0042 and 0065", and the index with it.
- **`../plans/01-scaffolding-and-designs.md`:** its questions 1, 3, 4, and 5 answered by this record.
- **Size:** about 40 lines in `ema.types` and `ema.designs` (the checks and their messages) and 6 for the
  registries' `unregister`, in the line count plan 01 reports.
