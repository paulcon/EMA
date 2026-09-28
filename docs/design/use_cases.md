# Use cases

**Status:** empty. **Updated:** <YYYY-MM-DD>.

> Each use case is a short scenario from the analyst's side: who they are, what model they have, what they
> want to learn, what they type (in Python or the CLI), what EMA asks them, and the report they get. Write
> them before the workspace functions: they become the guides, and the workspace's contract tests.
> Three to five are enough for v2.0.

## U1 <short name, e.g. "Which parameters matter in a cheap Python model?">

- **Analyst and model:** <…>
- **Question:** <…>
- **Steps, as typed:**

  ```python
  ws = ema.open_workspace()
  <…>
  ```

- **What EMA asks, and when:** <approval of the model; the price before running; …>
- **What they get:** <the report: which figures, which numbers with intervals, which notes>
- **What they do next, outside EMA:** <…>
- **Done when:** <the checks that say this use case works: these become a test>

## U2 <e.g. "Is my expensive simulator smooth along each parameter?">

<…>

## U3 <e.g. "A simulator that fails in part of its range">

<…>
