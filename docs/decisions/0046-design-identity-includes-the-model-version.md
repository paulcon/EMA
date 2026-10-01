# 0046. Include the model version in a design's identity

**Date:** 2026-10-01. **Status:** accepted. **Resolves:** none (consistency review, Q4).

## Context

- **`../design/designs.md`** (accepted, Determinism) says "a design's identity is its request (kind, space,
  generator parameters, seed, and generator version), not its points". Its ask of the data model adds the
  sampler and its version (0032).
- **Some points come from the model version,** not the request:
  - a model parameter the space leaves out is held at its nominal value (0023);
  - coordinate lines' anchor and the point design's x default to nominal values;
  - columns follow the model spec's order.

  Edit a nominal value, and the model version changes (0029), and the same request gives other points under
  the same design identity.
- **Runs are safe:** they are keyed by model version, complete point, and replicate (C46), so no run crosses
  model versions. Anything keyed by design identity is not: a stored design, or the stored diagnostic result a
  repeated request returns (C50).

## Decision

We will make a design's identity its request (kind, space, generator parameters, seed, sampler and its
version, generator version) **and the model version it was built for**. Two designs with the same request for
different model versions are different designs.

## Alternatives considered

- **The resolved values instead of the model version:** every held value, the resolved anchor or point, and
  the model parameter order. Two model versions that agree on these would share a design. Not chosen: runs
  never cross model versions anyway (C46), so the only gain would be fewer design records, at the cost of a
  more complex identity.
- **Leave it to the data model,** with a rule never to look up a design or a result across model versions. Not
  chosen: the identity itself should say what decides the points.

## Consequences

- **`../design/designs.md`** (accepted):
  - Determinism: "a design's identity is its request (kind, space, generator parameters, seed, sampler and its
    version, generator version) and its model version, not its points".
  - The data model ask: the same.
- **`../design/contracts.md`** (accepted): C20 gains a case: the same request for two model versions that
  differ in a nominal value gives two designs, with different points where a model parameter is held at its
  nominal value.
- **`../design/data_model.md`** (step 8): a design references its model version. A stored diagnostic result
  is found by a request that includes the model version (the reuse key, step 8).
