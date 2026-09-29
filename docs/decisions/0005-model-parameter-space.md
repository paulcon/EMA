# 0005. Call the region a design samples the model parameter space, and make it part of the design

**Date:** 2026-09-29. **Status:** accepted. **Resolves:** OD-3 (the part left open by decision 0003).

## Context

Decision 0003 chose "model parameter" and "model prediction", and left open the word for the region a design
samples. The candidates were "model parameter ranges" (the owner's redesign notes, and
`../design/purpose.md`) and "box" (v1's "input box", and the `Box` class suggested in
`../design/architecture.md` §3).

"Box" names one shape: a hyperrectangle, the product of one [low, high] range per model parameter. The region
a design samples may have another shape, such as a hyperellipsoid whose axes are given by the ranges. "Ranges"
names the numbers that define a region, not the region itself.

A design is a set of points at which to run the model to compute a diagnostic. The region it samples is chosen
for that design, not fixed by the model. One way to use EMA is to vary the region (for example, widen or
narrow the range of each model parameter) and see how a diagnostic's estimates change. `../design/purpose.md`
says as much: "Diagnostic results depend on the model parameter ranges and diagnostic parameters the user
chooses; changes in these values may change diagnostic results."

v1 learned the same thing the hard way. Its models held the input box and scales, so changing a scale
rewrote the stored spec for every campaign of that model version. Its lessons learned conclude: "The input box
and scales belong to the design, not the model" (`../notes/v1/lessons_learned_2026-09-27.md` §4).

## Decision

We will call the region a design samples the **model parameter space**, and it will be a property of the
design, not of the model.

- **Model parameter space:** the set of model parameter values a design may sample. Each design has exactly
  one. It may be a hyperrectangle, a hyperellipsoid, or another shape; which shapes EMA supports is decided in
  `../design/designs.md` and `../design/scope.md`, not here.
- **Model parameter ranges:** one [low, high] per model parameter. They are one way to define a model
  parameter space (the sides of a hyperrectangle, or the axes of a hyperellipsoid), not the space itself.
- **Belongs to the design.** A model spec, and so a model version, doesn't contain a model parameter space.
  Changing the space makes a new design, never a new model version.
- **In code,** following 0003's rule that code uses the glossary's words, the class is `ModelParameterSpace`,
  and arguments and fields are named `space`. `Box` is not used.

"Box", "input box", "input space", "domain", and "design space" go to the glossary's Avoid column when they
mean the model parameter space. "Design space" is avoided because it reads as "the space of designs".

## Alternatives considered

- **Box (v1, and `architecture.md`):** short, and familiar from v1, but it names one shape, and would be wrong
  for a hyperellipsoid.
- **Model parameter ranges:** the owner's earlier word, and in `../design/purpose.md`, but it names the numbers
  that define a space, not the space. It is kept for that meaning.
- **Parameter space, without "model":** shorter, but "parameter" alone is ambiguous next to diagnostic
  parameters (0003, "Consequences").
- **Domain, or design space:** standard terms, and kept as such in the glossary. "Domain" suggests the whole
  set where the model is defined, and "design space" collides with "design".
- **The space as part of the model spec:** v1's choice. It makes varying the space awkward, since each
  change touches the model, and it cost v1 the scale problem described above.

## Consequences

- **Glossary:** a row for "model parameter space" (standard terms: parameter space, input space, domain,
  design space, hyperrectangle, hyperellipsoid), and a row for "model parameter ranges". "Hyperrectangle" and
  "hyperellipsoid" are the standard names of the shapes a space may have. The row "ranges / box (OD-3)"
  goes.
- **`STATUS.md`:** OD-3 moves to "Decided", naming 0003 and 0005. No new OD row is needed for the region word.
- **`../design/architecture.md`:** `types/box.py` and `Box` become a `ModelParameterSpace`, which a
  hyperrectangle or a hyperellipsoid implements; `Box.around_nominal` builds a space from a model's nominal
  values; `Design.box`, every design generator's `box` argument, `Diagnostic.design`, and `Workspace.estimate`
  and `run` take `space`; the report header lists the space; the CLI's `--box` is renamed, and how a space is
  given on the command line stays open (§8).
- **`../design/designs.md`:** generators take a model parameter space; G2 reads "every point is inside the
  model parameter space"; `Box.to_unit` becomes a map from the space to a reference shape. Generators for
  shapes other than a hyperrectangle are new work.
- **`../design/model_interface.md`:** the "Versions" section already says the space lives in the design, not
  the spec; it takes this word.
- **`../design/data_model.md`:** the space is a column (or a table) of `designs`, not of `models`. Runs are
  keyed by model version and point, not by space, so a run made for one space can be reused by a design in
  another when the points coincide.
- **Scales are not decided here.** v1's lesson puts scales with the space, in the design; `architecture.md`
  keeps `scale` on `ModelParameter`. That choice belongs to the model interface spec (step 4).
- **Model parameter constraints** (such as positivity) stay on the model parameter. How they limit the spaces
  a design may use is for the model interface and designs specs.
- **Zero-width ranges,** now "held at this value" (`architecture.md` §3), interact with OD-10 (fixed
  parameters).
- **Varying the space to see how diagnostic results change** is a way of using EMA that this record makes
  possible, but it is out of scope for v2.0. It fits a diagnostic campaign, a concept for a later version
  (OD-2). v2.0 needs only what this record already gives it: the space is part of the design, so runs and
  model versions don't change when the space does.
