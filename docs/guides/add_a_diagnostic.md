# Add a diagnostic

**Status:** outline. **For:** EMA's owner and Claude Code (each v2.0 diagnostic's build step follows it), and
outside contributors. **Specs:** `../design/diagnostics/_template.md`, `../design/diagnostics/shared.md`,
`../design/contracts.md` (C1–C19), `../design/architecture.md` §6 (`ema.diagnostics`), `../design/scope.md`.

> A diagnostic is added by changing EMA's source: v2.0 has no plugin entry points (about 30 lines later, on the
> registries; `architecture.md` §4). The [working rules](https://github.com/paulcon/EMA/blob/main/CLAUDE.md) are for everyone: build only from an
> accepted spec, decisions recorded, tests first, one step at a time. Outline now, full text once the code
> exists; `<…>` marks text to write then.

## Before any code

1. **Propose it.** An issue (or a pull request holding only the spec) with the question the diagnostic
   answers, for which kind of model, and why no v2.0 diagnostic answers it (`purpose.md`, `use_cases.md`).
   <…>
   - Outside contributors: by invitation to the repository; contributions come in under its MIT license
     (`LICENSE`; record 0060). <…>

2. **Write its spec from [the template](https://github.com/paulcon/EMA/blob/main/docs/design/diagnostics/_template.md)** (`diagnostics/_template.md`), status `draft`: the five-row table, its
   diagnostic parameters, the computation with references, its uncertainty (an interval method, or none, and why;
   `uncertainty.md`), minimum runs and degenerate cases, the figures, and a mock report on a reference model,
   drawn by hand. Use the glossary's words. <…>
   - **Expected answers** on reference models, each computed by a separate script in `docs/checks/`, from the
     spec, not from the code (step 11's method; `reference_models.md`). A new reference model, if one is
     needed, counts against the reference models' 1,000 lines. <…>
   - The owner interviews, and sets the spec to `accepted`; only the owner does. <…>

3. **Draft its decision record,** status `proposed`: adding a diagnostic changes the list in [the scope](https://github.com/paulcon/EMA/blob/main/docs/design/scope.md),
   and its size budget of 6 diagnostics (0012). It also names its source lines: the source budget has about 60 lines
   left at v2.0 (`architecture.md` §11), so a new diagnostic usually proposes raising it, or a cut
   elsewhere. Only the owner accepts. <…>

4. **The plan** (`docs/plans/NN-…`, from [the plan template](https://github.com/paulcon/EMA/blob/main/docs/plans/_template.md)) on its own branch (`build-NN-<diagnostic>`), with its
   stop condition. <…>

## The tests, first

5. **Its known-answer tests,** from the spec's expected answers, with the spec's tolerances (`tests/`). <…>

6. **Register it for the contract checks:** they run over every registered diagnostic
   (`tests/contracts/diagnostic.py`; C1–C19), from its `example_request`. The tests and the contract checks are shown
   to the owner before the code is written (`CLAUDE.md`). <…>

## The code

7. **Choose its design generator,** or add one (with its own spec section and record; `designs.md`; C20–C27).
   <…>

8. **Write the module,** `ema/diagnostics/<name>.py`, implementing the `Diagnostic` protocol; its members are
   listed in [the architecture](https://github.com/paulcon/EMA/blob/main/docs/design/architecture.md) (§6), the one place they are kept.
   - What it declares, from its spec: its name and title, whether it takes a space, a `DiagnosticParameter` per
     row of the spec's parameter table but `space` and `prediction`, which are `run`'s own arguments (every table has a `seed` row; 0061), its
     interval method and spawn tags (C8). <…>
   - What it computes: its minimum runs (C3), its design, its estimates, observations, and notes from the
     usable runs only (P6), and its figures from the stored runs and result only (P1). <…>
   - What it doesn't: the shared precheck, observations, and notes, the report, the store, and the approval
     are `evaluate`'s and the other layers' (`shared.md`; AR1–AR7). <…>
   - Cite the ids it implements in docstrings and tests. <…>

9. **Register it** with `ema.diagnostics.register` (`architecture.md` §6), called when `ema.diagnostics` is
   imported (where the call is made is the first diagnostic's plan's). The workspace, the CLI
   (`ema diagnostics`), and the MCP server (`diagnostics`, `params`' JSON schema; C55) find it through the
   registry; nothing else changes. <…>

10. **Its pages:** the API reference (from its docstrings, Sphinx), and a line in the list in
    [Run a diagnostic](run_a_diagnostic.md). <…>

## Before review

11. **The checks** (`CLAUDE.md`): the fast tier with the import contracts; the full tests; Ruff, mypy;
    the docs build with warnings as errors. Its line count, against the record's. <…>

12. **The pull request:** what changed and why, the ids it implements, and the record; [the status file](https://github.com/paulcon/EMA/blob/main/STATUS.md) updated in
    the same commit. The owner reviews and merges. <…>
