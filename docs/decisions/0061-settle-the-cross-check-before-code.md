# 0061. Settle the specs' cross-check before code: a seed for every diagnostic, "user", golden points across machines, and the rules build step 01 needs

**Date:** 2026-10-01. **Status:** accepted; items 3 and 5 amended by 0062. **Resolves:** none ("Before the first line of code", `TODO.md`).

## Context

Before the first build step, eight independent reviewers checked the accepted specs against each other
(`../notes/consistency_review_2026-10-01_before_code.md`). The plain errors are corrected in place (0052).
What is left contradicts an accepted spec or record, or leaves something that build step 01 (`ema.types`, the
design generators, and their contracts) or a later step would otherwise have to decide:

- **The seed.** Every request has a seed (C8, the canonical request, `Request.params`), but the point run's
  and coordinate lines' parameter tables have no `seed` row, and `Diagnostic.parameters` is built from those
  tables. So `seed=5` could be refused or accepted, and if refused, C8 can't be checked for them. Nor does any
  spec say what `DesignIdentity.seed` holds for an unseeded design, or whether `params` repeats the seed.
- **"Analyst" and "user"** name one person: the glossary, `purpose.md`, and the principles say "user";
  `trust.md` and `use_cases.md` say "analyst", and it reaches generated text (the MCP server's instructions,
  "this client can't ask the analyst").
- **Golden points across machines.** `designs.md` promises log-range points and random-line directions bit for
  bit only on one machine with the same libraries (0044 kept that). 0059 runs the checks on Linux with the
  latest numpy on 3.14 and with numpy 2.1.0 on 3.13, and the owner develops on a Mac: G1's golden points can't
  pass on all three as written.
- **How a generator is called.** `DesignGenerator.size` and `build` take a `DesignIdentity`, while G's tests
  call `uniform(n=…)` and `point({"k": 50}, repeats=3)`, and §5 lists `seed` and `sampler` among `Uniform`'s
  parameters though they are fields of the identity. The design contract (C20–C23) needs per-generator inputs
  (seeded or not, nesting claimed, an example, one over the cap) that no protocol member gives. A generator
  given an identity of another `generator_version` has no rule, and a replay rebuilds a design from its stored
  identity without checking the points against the stored runs'.
- **Integers and doubles.** Canonical JSON keeps integers as integers (`data_model.md` §3.4), but the examples
  mix `"k": [30, 60]`, `(30.0, 60.0)`, and `"nominal": 45.0`. So `45` and `45.0` would be two model versions,
  and the same request from the CLI and from Python could get two reuse keys.
- **The map back to unit coordinates.** The fits need the unit coordinates of stored, possibly reused runs,
  and the shared-anchor test and given lines' anchors need them too; `designs.md` gives only the forward maps.
  0058 considered pinning the inverse and didn't, for one test's sake; the fits now need it.
- **`ema mcp`.** The command lives in `ema.cli`, which AR1 and AR3 forbid from importing its sibling `ema.mcp`.
- **The stderr tail.** `trust.md` (0057) says `failed_runs` returns a failed run's last 15 lines of stderr,
  but `RunInfo` and Q7 carry no tail.
- **Smaller ones:** T9's deletion without following links is placed in `ema.runner`, but `prepare` also clears
  a leftover run directory; C6's offset merges the point run's fixture replicates (5 distinct values become 1,
  computed); a root inside a workspace should exit 2 (T5) but is checked in `open_workspace`; `result.json`'s
  keys are unnamed; `ema.types`'s closed list of standard-library imports lacks what its own checks use;
  `duration()` has examples but no rule; golden reports compare labels, but the mocks' titles write R ids as
  model names; four glossary rows disagree with the specs; 0028 says a rerun's run gets a new id while the data
  model gives it the same id; and six partial amendments carry no "amended by" mark (0052).

## Decision

We will:

1. **Give every diagnostic a `seed` parameter.** The point run and coordinate lines get the row lines has:
   `seed` | integer ≥ 0 | 0 | recorded; these diagnostics make no random draws | no. The seed is in the request
   and the reuse key, so two requests that differ only in it are two diagnostic evaluations with the same
   numbers (C8). `DesignIdentity.seed` holds the request's seed for every kind, used only by seeded
   generators; `DesignIdentity.params` holds only what isn't already a field (no `seed`, `sampler`, or
   versions).
2. **Say "user", not "analyst",** in every spec, guide, and generated text; the glossary gets a row "user | the
   person who runs EMA, from Python, the CLI, or through an MCP client | | analyst".
3. **Promise golden design points as follows** (G1): the `random` sampler's unit rows and linear-range points
   bit for bit on every machine and numpy version; log-range points within 1 ulp across machines, and bit for
   bit within one; random-line directions within 4 ulps across machines (they pass through a normalization),
   and bit for bit within one. A change in numpy's `standard_normal` stream fails the golden-points test, as a
   reuse loss to record, never silently. Reuse stays by exact point (0044, 0051).
4. **Call generators stateless, with an identity only:** `size(identity, spec)` and `build(identity, spec,
   start, stop)`. G's tests and `architecture.md` §5 build an identity; §5's per-generator parameter lists
   name `params`' keys only. A generator refuses an identity of another `generator_version`, naming both. The
   design contract's inputs come from a table keyed by generator name in `tests/contracts/design.py`.
5. **Check a replay's points:** a replay compares each rebuilt row's point hash with its stored run's; a
   mismatch is an error naming the row.
6. **Hash model-parameter values as doubles:** every value in model parameter units (nominal values, limits,
   range ends, held values, a point's `x`, anchors, given directions) becomes a double when parsed; integer
   diagnostic parameters stay integers, and alpha keeps its decimal string (0047). A run id hashes its two ids
   as hex text.
7. **Pin the map back to unit coordinates** in `designs.md`: linear z = (2x − (lo + hi))/(hi − lo), log the same
   in ln x, clamped to [−1, 1], with lo and hi mapping exactly to −1 and 1. The fits, the shared-anchor test
   (`SHARED_ANCHOR_TOL`), and given lines' anchors use it.
8. **Let `ema.cli` import `ema.mcp`** lazily, in the `mcp` command only (it needs the `ema[mcp]` extra): the
   layers contract puts `ema.cli` above `ema.mcp`, and AR3 says so. The command stays `ema mcp`.
9. **Return the stderr tail:** `RunInfo` gains `stderr_tail: str | None`, shown in its `text`, and Q7 returns
   the tails beside the reasons, so `failed_runs` returns them as `trust.md` says.
10. **Delete run directories in one place:** `remove_tree` in `ema.models.files`, which doesn't follow links,
    used by `prepare` and `ema.runner`; `trust.md`'s T9 row moves there.
11. **Exempt the point run from C6:** the offset merges replicates that differ in the last bits; C5 still holds.
12. **Refuse a root inside a workspace in `open_workspace(root=)`** with `PathRefused`; `ema mcp` maps that
    refusal at start to exit 2, as T5's test expects.
13. **Name `result.json`'s keys:** `export_format`, `design`, `spec`, `columns`, `result`; `result` is
    `DiagnosticResult.to_json()`'s object, which `reproduce` reads.
14. **Let `ema.types` import `re`, `keyword`, and `collections.abc`,** which its own checks need.
15. **Give `duration()` one rule:** under a minute in seconds, under an hour in minutes, otherwise hours and
    minutes ("about 1 h 20 min"); U4's "about 80 min" is written that way.
16. **Settle the rest:**
    - golden reports don't compare the model's name (the mocks write R ids; only R2 is named so far);
    - the glossary's "request" leaves out the model version, as `Request`, the canonical request, and P5 do;
      "approval" and "confirmation" are the user's answer, a yes letting runs happen (declined ones are
      stored); "observation" covers a cell that says why there is no number;
    - `DiagnosticParameterInfo.type`'s example drops "model parameter space", which is not a diagnostic
      parameter;
    - 0028's "a new id" is amended: a rerun's run has the same id (`data_model.md`);
    - the missing "amended by" marks are added: 0006 by 0049 (the test run's approval), 0010 by 0056 (`price`),
      0017 by 0034 (observations), 0031 by 0057 (`pass_env`), 0035 by 0051 (P6's point-run exception), 0036
      by 0038 and 0040 (observations only).

## Alternatives considered

- **Refuse `seed` for the point run and coordinate lines,** and reword C8 to "records seed 0": one fewer row,
  but a parameter every request carries would be refused for two diagnostics, and C8 untestable for them.
- **"Analyst" everywhere:** it names the role well, but "user" is already the glossary's word and the more
  common one in the specs and generated text.
- **Golden points bit for bit on one machine only** (as now): the checks on two Linux setups would skip or
  fail them. **Bit for bit everywhere:** not achievable for `exp` across CPUs without our own `exp`.
- **Generators as request dataclasses** (`Uniform(n, seed, sampler)`): matches §5's lists, but two shapes for
  one design, and the stored identity must still rebuild it.
- **Replays from the stored runs' points:** no rebuild at all, but a replay would no longer check that today's
  generator still makes the design it claims to.
- **Integers kept as typed:** fewer conversions, but the same request through two interfaces gets two keys.
- **A separate console script for the MCP server** (`ema-mcp`): no layer change, but `ema mcp` is in
  `trust.md`, `export.md`, the get-started guide, and 0057.

## Consequences

- **`../design/diagnostics/point_run.md`, `coordinate_lines.md`:** the `seed` row; "No seed" says the seed is
  a parameter that changes nothing.
- **`../design/architecture.md`:** `DesignIdentity`'s `seed` and `params`; the generator signatures and §5's
  lists; the version refusal; the layers contract and AR3; `RunInfo.stderr_tail`; `remove_tree`;
  `open_workspace(root=)` and `ema mcp`'s exit 2; `ema.types`'s import list; `duration()`'s rule; replay's
  point check; `DiagnosticParameterInfo.type`.
- **`../design/designs.md`:** G1's promise and its test; the inverse map; the generator tests' calls.
- **`../design/data_model.md`:** §3.4's doubles and the run id's bytes; Q7's tails; replay's check.
- **`../design/contracts.md`:** C6's exception; C20's golden points; the design contract's table.
- **`../design/trust.md`:** T9's row; T5's check.
- **`../design/export.md`:** `result.json`'s keys.
- **`../design/diagnostics/shared.md`:** what golden reports don't compare.
- **`../design/glossary.md`:** the "user" row; "request", "approval", "confirmation", "observation".
- **"analyst" → "user":** `trust.md`, `use_cases.md`, `principles.md`, `architecture.md`, `scope.md`,
  `export.md`, `designs.md`, `model_interface.md`, three diagnostic specs, and two guides. Records are not
  edited.
- **`use_cases.md`:** U4's duration.
- **Records' statuses:** 0006, 0010, 0017, 0028, 0031, 0035, 0036 marked, and the index with them.
- **Later:** a numpy release that changes `standard_normal` fails the golden-points test and needs a record.
