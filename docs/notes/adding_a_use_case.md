# Adding a use case

**Written:** 2026-09-29. A short guide to adding a use case to `../design/use_cases.md`, with a template. The
rules themselves are in `../../CLAUDE.md`, `../../README.md`, and `../decisions/README.md`. Where this guide and
those files differ, those files win.

## When to add one

Add a use case when a user would use EMA in a way that no use case covers yet. For example: a new kind of
model, a new diagnostic in the user's workflow, or a new promise that a principle makes and no use case
tests. Use cases come before the workspace functions. They become the guides and the workspace's contract
tests, so a feature with no use case behind it has no test of the path a user takes.

If the scenario is an existing use case with one thing changed, extend that use case, or write a short one
that starts from it ("after U2, …").

## Steps

1. **Check the table** at the top of `use_cases.md`. Is the scenario new, or a variation?
2. **Take the next id**: U10, U11, …. Ids are never renumbered or reused, because tests, guides, and commits
   cite them.
3. **Draft it from the template below**, in the glossary's words (`../design/glossary.md`):
   - Write the full form for a new scenario. Write the short form (steps, what EMA asks, "Done when") for a
     variation of an earlier use case.
   - Where it depends on an open decision in `../../STATUS.md`, assume the suggested option and mark the
     place with its OD-n.
   - Cite the principles and decision records it exercises (P3, 0010).
   - Claude Code can interview you on each part, with drafted options, one use case at a time.
4. **Check it** against the list in "Checks" below.
5. **Record what it asks of other specs** in the last section of `use_cases.md`, "What the use cases ask of
   other specs". Put a "Decide:" line on the TODO step that settles each open question.
6. **Get it accepted.** `use_cases.md` is accepted, so it changes only through a decision record: draft one
   with status `proposed`. Say what the use case adds, why it is needed, and what it asks of other specs.
   If an answer in the interview changes another accepted spec or principle, the record says so too.
7. **Commit it all together** once the record is accepted: the record, `use_cases.md`, the decisions index,
   any `TODO.md` "Decide:" lines, the "Use cases:" line of each guide it feeds (`../guides/`), and
   `../../STATUS.md`.

## Checks

- **The numbers add up.** For each price, count the design's distinct points, then the ones already stored:
  - Designs can share points. Coordinate lines share their anchor; nested uniform and convergent designs
    with the same seed and model parameter space share a prefix.
  - Designs in different model parameter spaces share almost none.
  - The time is the new runs times the run time. It is "unknown" when the model version has no stored run
    durations, as for a new model version (P3).
  - Several numbers in U2–U5 were wrong in their first drafts, for these reasons.
- **Every new run is approved (P3),** including a test run at the nominal point. A request with no new runs
  asks nothing.
- **"What they get" holds no interpretation (P2).** It lists figures, estimates with variability intervals,
  counts, and notes. What they mean is the user's to say, under "What they do next".
- **"Done when" checks the flow, not the numerics.** Known answers for a diagnostic belong to that
  diagnostic's spec (`../design/diagnostics/`). The use case checks what EMA asks, the counts, reuse,
  determinism (P4), and what the report contains, on a reference model (`../design/reference_models.md`).
- **The typed steps use `ema.workspace` as drafted** in `../design/architecture.md` §7. A new name or argument
  goes in the section "What the use cases ask of other specs", and counts toward the budget of public names
  in `../design/scope.md`.

## Template

The full form:

````markdown
## U<n> <short name: the user's question, or the situation>

- **User and model:** <who they are; their model: Python function or command line, time per run, number
  of model parameters, model predictions (OD-9); the reference model the "Done when" test uses>
- **Question:** <what they want to learn, in their words; the answer is theirs to draw (P2)>
- **Steps, as typed:** <one line on what they do>

  ```python
  ws = ema.open_workspace("<name>")
  <…>
  ```

- **What EMA asks, and when:** <each approval and its price: new, reused (and how many of those failed),
  time or "unknown"; anything refused before asking>
- **What they get:** <the report: header (model version, model parameter space, design, run counts);
  figures, with their axes; estimates with variability intervals; notes; provenance>
- **What they do next, outside EMA:** <the decisions or work the report feeds>
- **Done when:** on <reference model>, in a fresh workspace:
  - <a check that becomes a workspace contract test>
  - <…>
````

The short form, for a variation of an earlier use case:

````markdown
## U<n> <short name>

- **Steps, as typed:** after U<m>, <what changes>.

  ```python
  <…>
  ```

- **What EMA asks, and when:** <…>
- **Done when:**
  - <…>
````

Then add its row to the table at the top of `use_cases.md`:

```markdown
| U<n> | <short name> | <principles and decisions it exercises: P…; OD-…> |
```
