# 0053. Reserve the `ema_` prefix in model names, and offer export through the MCP server

**Date:** 2026-10-01. **Status:** accepted. **Resolves:** none (the export spec's interview).

## Context

- **The export's `runs.csv`** (`../design/export.md`) has a column per model parameter and model prediction,
  by name, beside EMA's own columns (`ema_status`, `ema_reason`, …). A model's names are any Python identifiers
  (`../design/model_interface.md`), so a model prediction named `ema_status` would collide with EMA's column.
- **0016** lists the MCP server's tools: "list and describe models and diagnostics; propose a model spec and
  save it; test a model; estimate; run a diagnostic; get a diagnostic result, a report, or a figure. At most 10
  tools." Export is not among them. The interview chose to offer it through MCP too, writing only inside a
  directory the user names when starting the server.

## Decision

We will:

1. **Refuse a model spec with a model parameter or model prediction name that starts with `ema_`,** when it
   is loaded, naming it. EMA's columns in an export keep that prefix to themselves.
2. **Add export to the MCP server's tools,** within its cap of 10 (0016). The tool writes only inside a
   directory the user named when starting the server (`../design/trust.md`, step 10).

## Alternatives considered

- **Bare EMA column names** (`status`, `reason`), with a list of reserved names refused at loading: shorter
  columns, but a longer list to keep and check.
- **Prefix the model's names instead** (`param.k`, `pred.T_max`): no refusal needed, but less friendly in
  other tools.
- **Export from Python and the CLI only:** keeps a tool slot free, but an MCP client couldn't hand the analyst
  their runs.

## Consequences

- **`../design/model_interface.md`** (accepted): Names, "a model parameter or model prediction name may not
  start with `ema_`"; a new requirement, M21: "A model parameter or model prediction name that starts with
  `ema_` is refused at loading, naming it", tested by a spec with a model prediction `ema_status`, as M18 is
  for `noisy: true`.
- **`../design/contracts.md`** (accepted): no change; M21 is the model interface's own test.
- **0016's status:** "accepted; its tool list amended by 0053 (export)".
- **`../design/architecture.md`** (step 9): the MCP export tool is one of the 10; with `estimate` (the price),
  the list is tight, and step 9 counts it.
- **`../design/trust.md`** (step 10): the export tool's directory (`../design/export.md`, E7).
