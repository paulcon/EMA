# Answers to the questions on the lessons-learned report

2026-09-27. These answer `questions_for_lessons_learned.md`, section by section, for `lessons_learned_2026-09-27.md`. Where v1's code shows the idea, the answer points to it; where v2 would do something new, there is a short sketch. The sketches are illustrations, not tested code. Links to documentation and tutorials are collected in the last section, [References](#references), and cited in the text by tag, such as [R-mcp]. That section also suggests a reading order.

---

## 1. Summary

### What does "runs belong to a model version and are cached" mean?

Three ideas together.

- **A model version** is a model's spec plus the exact contents of the files it uses: the Python function's source, the input-deck template, the simulator script. EMA fingerprints all of that into a *version hash* (section 5), and names the version `borehole@3f9a…`. Edit the template, and it's a new version. Move the directory, and it's the same version.
- **A run** is one evaluation of the model at one input point: the inputs, the output, whether it succeeded, how long it took.
- **"Belongs to a model version"** means each run is stored against the version that produced it, not against the campaign or diagnostic that asked for it. So a run done for campaign A is available to campaign B, as long as the model hasn't changed.
- **"Cached"** means that before running a point, EMA looks it up: the same version, the same inputs (to the last bit), and the same replicate. If a successful run exists, EMA reuses its output instead of running the model again. Failed runs are not reused, so a flaky failure can be retried.

Why it matters: exploration asks overlapping questions. A `scatter` of 200 random points and a `fourier` fit with the same seed share their first 200 points, so the second diagnostic is free. In v1, `fourier` after `sobol` often costs nothing. If the simulator changes, the hash changes, and nothing stale is reused.

In v1 this lives in `store.py` (the `runs` table, with index `runs_cache ON runs (model_id, input_hash)`), `execution.py` (`run_design` looks up the cache before scheduling), and `spec.py` (`version_hash`).

### What is a contract? And what is the contract suite?

A **contract** is the set of promises an interface makes to whoever uses it, written so they can be checked. For a diagnostic, the promises include:
- "if every run failed, you claim nothing";
- "the same request gives the same design and the same numbers";
- "multiplying the output by 10¹² doesn't change your conclusions";
- "your result is valid JSON";
- "you finish in under 5 s with 20 inputs".

These don't depend on *which* diagnostic it is. Any diagnostic must keep them.

The **contract suite** is v1's `tests/diagnostic_contract.py`: about 16 `check_*` functions, each testing one promise on *any* diagnostic class it is given. `tests/test_diagnostic_contract.py` runs every check on every registered diagnostic (the registry × the checks, with `pytest.mark.parametrize`). So a new diagnostic is tested the moment it is registered, without anyone writing tests for it. Section 4 goes into how that works and how to design one.

---

## 2. What was built, in numbers

### What is churn?

**Churn** is the number of lines added plus the number removed over a period, as git counts them (`git log --shortstat`). EMA's week had +81,875 and −9,054 lines. The code that remains (source, tests, evals) is about 47,000 lines of Python, plus about 84,000 words of docs.

High churn against the final size means a lot was written and rewritten. That can be healthy (refactoring), or a sign that the design was still moving while code was being written on top of it. For EMA it was mostly the second: most of it was new features added faster than they could be reviewed, plus retrofits such as the experimental split.

### What is the Agent surface?

Everything the LLM sees of EMA, which is also everything you have to keep stable and test when you change the agent:
- the **system prompt** (1,600 words in v1);
- the **tools**: each tool's name, description (in v1, the function's docstring), and parameter schema. There are 26 in v1;
- the **shapes of tool results**: the JSON each tool returns;
- the **harness notes** the session inserts, such as revise mode's "rewrite this reply" note.

In v1 this adds up to about 10,500 tokens sent at the start of every session. The report calls it a surface because, like an API, it is the contract between EMA and the model. Changing any part of it changes the agent's behaviour, which is why v1 requires the eval gate for each change.

### What is ALTER TABLE?

An SQL statement that changes an existing table's structure. For example, `ALTER TABLE runs ADD COLUMN replicate INTEGER NOT NULL DEFAULT 0;` adds a column to a table that already holds data. SQLite supports adding, renaming, and (since 3.35) dropping columns. See [R-sqlite-alter].

v1 needed 12 of these across 2 migrations in its first week. Each time the design gained a concept (budgets, provenance, replicates, the experimental switch), existing workspaces had to be upgraded to it. That's what a **migration** is: a script that takes a database from schema version N to N+1 (`store._MIGRATIONS`). The count is a measure of how much the data model changed after data had started to be stored.

---

## 3. How control was lost

### How can I ensure that interpretation and advice stay out of the main diagnostic reports and only appear in a separate section labelled "experimental"?

Make the separation structural, so that mixing them takes deliberate effort, rather than a matter of discipline or prompting. In order of strength:

1. **Separate types.** A diagnostic's `compute()` returns a `Result`: values, intervals, counts, data notes. A `Result` has no place for words like "negligible" or "linear". Interpretation is a *different* function in a *different* module, `interpret(result) -> Interpretation`, which reads a `Result` and returns verdicts with their thresholds. The core never imports the interpretation module.
2. **One-way dependencies, checked.** Put interpretation in its own package (`ema/experimental/`). A test, or a tool like import-linter, fails if anything in `ema/core`, `ema/diagnostics`, or `ema/report` imports it. The main report renderer then *cannot* reach interpretation, because it has no access to the code.
3. **Separate storage.** Interpretations go in their own table (or file), keyed by the result they read, with a column saying which version of the rules produced them. v1 had to add `interpretation_text` next to `summary_text` after the fact.
4. **Separate rendering.** The report is built from two renderers: `render_results(...)` for the main body, and `render_experimental(...)`, which writes one section headed "Experimental". Only the second is given interpretations. A single switch (`experimental=False`) skips it entirely.
5. **A test that proves it.** v1's `check_summary_ignores_interpretation` is the model: build the report with every interpretive field withdrawn, build it again with them present, and require the main body to be byte-identical. If a verdict ever leaks into the main body, this fails.
6. **Define the line in the glossary first.** v1 settled it late:
   - *results* are numbers, intervals, rankings, run counts, figures, and caveats about the data;
   - *interpretation* is any comparison with a heuristic threshold, and anything that says what a number means or what to do next.

   Writing this down on day 1 decides every later case.

For the agent, the equivalent is to not let it write interpretation into chat at all (section 7). An `interpret` command or tool produces the experimental document from stored results, so there is no prose to police.

### What are the rules that should stay? What's the right way to design rules? Should I try to envision all of them or derive them from bugs?

**Both, in different proportions.** Envision the few rules that define the product and its safety up front. Let the rest emerge from bugs, but treat every bug-driven rule as a question first: *could a different design make this bug impossible?* If so, change the design, not the rule list.

**What makes a good rule:**
- It states an **invariant**: something always true, not a procedure. "The same request gives the same points and the same numbers" is an invariant. "Seed the bootstrap from the design's seed plus one" is an implementation detail that serves it.
- It is **testable**, and it names its test. A rule with no check is a wish.
- It says **why**. The reason is what lets you (or Claude) apply it to a case the rule didn't foresee.
- It is **short**. If a rule needs a paragraph of special cases, the design underneath it is probably wrong.
- It has **one home**. The principle is stated once (in the design document, or CLAUDE.md), and the details live in the docstring of the code that enforces it.

**v1's 36 rules, sorted** (a suggestion for you to review):

*Principles to keep, the core of v2:*
- The core computes everything; the agent computes nothing.
- Results first; interpretation is separate and labelled experimental.
- Runs belong to a model version and are cached; a changed model is a new version.
- Designs are deterministic: the same request gives the same points and numbers.
- Every diagnostic follows the same steps (design → run → compute → present), and failed runs are NaN, which every diagnostic tolerates.
- No data, no claims (section 12).
- Tolerances scale with the output: conclusions don't depend on units.
- Estimates come with intervals, and a "negligible" claim needs the whole interval below its threshold.
- Diagnostics compute from the inputs the model actually received.
- Noise is explicit: a model is deterministic unless measured otherwise.
- Budgets are checked before anything runs.
- Approval covers everything that decides what a run does; user code runs isolated with a scrubbed environment.
- Heuristic thresholds are named constants, documented in the spec.
- Every result records its provenance.

*Implementation details: keep the behaviour, and move the text into code docstrings:*
- model directories never stay on `sys.path`, and a new version runs new code;
- relative paths resolve against `model.json`;
- write-ahead logging and batched commits;
- a cut-off tool call never runs;
- error results say whether a retry helps;
- schema changes need a migration.

*Tied to features the report suggests leaving out of the first version:*
- stored runs listed exactly;
- surrogates tested on fresh runs;
- diagnostics compared, not averaged;
- next steps from rules;
- flags come with their meaning;
- every reply checked for grounding and for the split (made unnecessary by harness-rendered numbers, section 7).

---

## 4. Testing components

### What is a contract, how does it ensure every diagnostic gets checked, what might the checks be, and how do I design one?

**What it is.** A contract is a list of promises that every implementation of an interface must keep. In v1, the interface is the `Diagnostic` base class: `design()`, `compute(design, y)`, `present(...)`, `estimate_cost()`, `example_params()`. The promises are about behaviour visible through those methods, not about any one diagnostic's maths.

**How every diagnostic gets checked.** Three pieces:

1. A **registry**: every diagnostic class registers itself (`@register`), so the tests can find them all.
2. A **generic way to build an instance**: each class provides `example_params(input_names)`, small valid parameters. A check can then construct *any* diagnostic without knowing what it is.
3. **Parametrized tests**: pytest runs every check against every registered class.

```python
# tests/test_diagnostic_contract.py (v1, simplified)
@pytest.mark.parametrize("check", CHECKS)
@pytest.mark.parametrize("name", sorted(REGISTRY))
def test_registered_diagnostics_keep_the_contract(name, check, tmp_path):
    check(REGISTRY[name], tmp_path)
```

With 12 diagnostics and 16 checks, that's 192 tests nobody wrote by hand, and the 13th diagnostic gets 16 more for free.

**A check looks like this** (v1's, abridged):

```python
def check_no_claims_without_data(cls, tmp_path):
    """With every run failed, the flags claim nothing, a note says why, and present() still works."""
    diag = build(cls)                       # uses cls.example_params
    design = diag.design()
    y = np.full(len(design), np.nan)        # every run failed
    result = diag.compute(design, y)
    assert not any(claims(v) for v in result.flags.values())
    assert result.n_ok == 0 and result.notes
    assert diag.present(result, design, y, tmp_path).summary
```

**v1's checks**, as examples of what a contract can hold:

| Check | Promise |
|---|---|
| `check_cost` | `estimate_cost()` equals the size of `design()` |
| `check_partial_failures` | random and clustered failed runs are tolerated |
| `check_no_claims_without_data` | all runs failed → no claims, and a note says why |
| `check_jsonable` | the result is strict JSON |
| `check_deterministic` | the same request gives the same points and numbers |
| `check_units_invariance` | output × 1e-12 or 1e12 → the same flags |
| `check_fast_at_d20` | design + compute take under 5 s with 20 inputs |
| `check_figures_have_data_cards` | every figure has its JSON card |
| `check_flags_are_interpreted` | every flag has a meaning |
| `check_constant_output` | a constant output makes no claims |
| `check_negligible_needs_interval` | no "negligible" from a point estimate |
| `check_summary_ignores_interpretation` | the summary reads no interpretive flag |
| `check_design_params`, `check_nested_designs` | the declared design parameters and nesting are true |

**How to design one:**

1. **Write down the interface:** the methods, their inputs, and their outputs.
2. **List the promises a user of the interface relies on.** Ask: "What would break downstream if an implementation did X?" Each answer is a promise.
3. **Give each check a generic way to build an instance and generic inputs:** a small test model, the example parameters, a fixture.
4. **Write one check per promise.** Its assertion message should say which promise failed.
5. **Prove each check works with a negative control:** a deliberately broken toy implementation that the check must reject. v1 does this: `test_diagnostic_contract.py` has toy diagnostics that each break one rule.
6. **Run the suite over every registered implementation.**

**Design principles for contracts:**
- **Test through the public interface only.** A check that peeks at internals ties the contract to one implementation.
- **One promise per check,** named after the promise.
- **Generic inputs, chosen to be demanding:** v1's contract model has interacting inputs, curvature, and unequal ranges, so lazy implementations fail.
- **Cheap:** the whole suite runs on every change.
- **Deterministic:** no flaky randomness; seed everything.
- **Every check has a negative control,** so it can't pass vacuously (v1's benchmark and eval checks did pass vacuously: report §4).
- **The contract is documented beside the interface** (the spec says what it promises, and the tests enforce the same list).

### What are snapshot comparisons?

Record *everything* a fixed set of runs produces before a change, run the same set after, and compare. v1's `tools/snapshot/` runs 26 campaigns (340 requests, all 12 diagnostics, including constant, failing, noisy, log-scale, and command-line models). It stores every result, summary, data card, and a hash of each figure image, then `compare.py` reports every field that differs.

Use snapshots for changes that should *not* change behaviour: refactors, performance work, moving code. Any difference is either a bug or something you must explain. For changes that *should* alter behaviour, the diff shows exactly what changed, which you then review.

One subtlety v1 hit: floating-point results aren't bit-identical from run to run (about 1e-15 relative, from summation order in BLAS or SIMD code). So `compare.py` learns, from several "before" runs, which fields vary, and allows only those to differ, by at most 1e-13.

### What are the degenerate inputs I should consider?

"Degenerate" means legal but extreme or pathological, the cases where naive numerics produce confident nonsense. For EMA:

*Outputs:*
- every run failed (all NaN); one usable run; fewer usable runs than the method needs (for a linear fit, fewer than d + 2);
- failures at random, **in a contiguous block** (which faked jumps in v1, L2), at one end of the range, or concentrated in one input's corner;
- a constant output, and a nearly constant one (varying only at rounding level, ~1e-15 relative: G1 in v1's review);
- a huge offset with a small variation (y = 10⁶ + 10⁻³·f(x));
- very large or very small scale (×10¹², ×10⁻¹²);
- infinite values; a single wild outlier;
- noise, and noise with a finer grid (L1 in v1: more points hid the structure);
- steps, kinks, plateaus, and functions that are exactly polynomial (so residuals are pure roundoff).

*Inputs and designs:*
- d = 1, and d large (20 or more);
- a range of zero width; a nominal value at a bound (L5 in v1); very unequal ranges (10⁻⁶ against 10⁶);
- a log-scale input with a range spanning many decades, or near zero;
- the minimum sample size, and a size that is too small;
- no bootstrap (`n_bootstrap = 0`: G4 in v1);
- duplicated points; inputs the model rounds (`number_format`: G5 in v1).

*Models (for the model-adapter contract):*
- a run that times out, crashes, or kills its worker;
- non-numeric, empty, or garbage output;
- a missing output file;
- a program that reads stdin;
- a Ctrl-C in the middle of a run (M1 in v1: this corrupted the cache).

### How do I define a contract for every component interface?

Apply the same recipe to each interface. In v2 the main ones would be:

| Interface | Example promises |
|---|---|
| **Model adapter** (`evaluate(points) -> outputs, statuses`) | failures come back as NaN with a status and never raise; a timeout is honoured; the child gets a scrubbed environment and no stdin; the same point gives the same output for a deterministic model; the version hash changes when a tracked file changes and not when the directory moves |
| **Design** (`points(box, params)`) | deterministic for a seed; every point inside the box; the declared size is exact; nested sizes are subsets when declared |
| **Diagnostic** | as in v1 |
| **Store** | what goes in comes out (round trip); the cache key is exact to the bit; failed runs aren't reused; an old database migrates; a crash mid-write leaves no half-recorded run |
| **Report renderer** | renders every result type; the output has no interpretive words without the experimental switch; every figure has a card |
| **Tool** (if there is an agent) | each tool's schema describes every parameter; every result uses the envelope (section 8); every error says whether a retry helps |

In code, write each interface as a `typing.Protocol` (or an abstract base class), write a `tests/contracts/<interface>.py` module of `check_*` functions, and parametrize over every implementation:

```python
# ema/models/base.py
class Model(Protocol):
    def version_hash(self) -> str: ...
    def evaluate(self, X: np.ndarray) -> RunBatch: ...   # never raises for a bad point

# tests/contracts/model.py
def check_failures_are_nan_not_exceptions(make_model, tmp_path):
    model = make_model(behaviour="fails_at_half")       # a fixture that builds a failing variant
    batch = model.evaluate(np.array([[0.2], [0.5], [0.8]]))
    assert np.isnan(batch.y[1]) and batch.status[1] == "failed"
    assert np.isfinite(batch.y[[0, 2]]).all()

# tests/test_model_contract.py
@pytest.mark.parametrize("make_model", [python_model, cli_model, isolated_python_model])
@pytest.mark.parametrize("check", MODEL_CHECKS)
def test_model_contract(make_model, check, tmp_path):
    check(make_model, tmp_path)
```

The hard part is usually the fixture: a way to build each implementation in each test situation (failing, slow, noisy) without special cases. It is worth designing the interface so such fixtures are easy.

### How do I generate degenerate cases?

Two complementary ways.

**1. A hand-written catalogue.** Named functions and fixtures for each case above (v1's `tests/functions.py` is a start): `constant`, `rounding_flat`, `step_at_half`, `offset_1e6`, `fails_in_block(lo, hi)`, and so on. Each case is a clear, readable regression test.

**2. Property-based testing with Hypothesis** [R-hypothesis]. You state a property ("flags don't depend on the output's units"), and Hypothesis generates hundreds of inputs trying to break it. When it finds a failure, it *shrinks* it to the smallest case that still fails. This finds the cases you didn't think of.

```python
from hypothesis import given, settings, strategies as st

scales = st.floats(1e-12, 1e12).filter(lambda s: s > 0)
fail_masks = st.lists(st.booleans(), min_size=40, max_size=40)

@settings(max_examples=50, deadline=None)
@given(scale=scales, failed=fail_masks)
def test_linear_flags_do_not_depend_on_units_or_failure_pattern(scale, failed):
    diag = build(LinearCoeffs)
    X = diag.design()
    y = outputs(X) * scale
    y[np.array(failed)] = np.nan
    base = diag.compute(X, outputs(X)).flags
    got = diag.compute(X, y).flags
    if sum(not f for f in failed) < MIN_USABLE_RUNS:
        assert not any(claims(v) for v in got.values())      # no data, no claims
    ...
```

Hypothesis also has strategies for NumPy arrays (`hypothesis.extra.numpy.arrays`), so you can generate whole output vectors with NaN runs, infinities, and near-constant values.

### How would I design and implement fast and slow tiers?

The **fast tier** runs on every edit and must finish in seconds: unit tests, contract checks on small inputs, doctests. The **slow tier** runs before merging: end-to-end campaigns, walkthroughs, the benchmark, the wheel build, real applications.

Implement it with a pytest marker [R-pytest-markers]:

```python
# conftest.py
def pytest_addoption(parser):
    parser.addoption("--slow", action="store_true", help="also run tests marked slow")

def pytest_collection_modifyitems(config, items):
    if config.getoption("--slow"):
        return
    skip = pytest.mark.skip(reason="slow: run with --slow")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip)
```

```toml
# pyproject.toml
[tool.pytest.ini_options]
markers = ["slow: end-to-end or expensive; run with --slow", "external: needs installed applications"]
```

Then `pytest -q` is the fast tier and `pytest -q --slow -n auto` the full one.

Habits that keep the fast tier fast:
- Give it a **time budget** (for example 30 s) and watch `pytest --durations=20`.
- **Mark any test over about 1 s as slow**, or make it smaller.
- Keep numerics tests **pure**: no database, no subprocess, no figures.
- Share expensive setup with `scope="session"` fixtures.
- Run in parallel with pytest-xdist (`-n auto`), which v1 adopted this week.

In CLAUDE.md, tell Claude to run the fast tier after each edit and the slow tier before reporting a task done.

### What is a golden report? And what is shape-pinning?

A **golden report** (also called a golden file or approval test) is a stored, human-reviewed output that a test regenerates and compares:
- run a reference analysis (say, `linear_coeffs` on the Ishigami function, seed 0);
- produce its report and data;
- require them to match `tests/golden/ishigami_linear.md` and `.json`.

When a change alters the output on purpose, you rerun with an update flag, **read the diff**, and commit the new golden file. The review of that diff *is* the test. Libraries: syrupy and pytest-regressions [R-snapshot]. It's like v1's snapshot check, but committed and run by pytest.

**Shape-pinning** is a test that asserts the exact structure or wording of an output: its keys, nesting, types, or exact sentences. For example:
- `assert result.keys() == {"derived", "experimental", "budget_used"}`;
- `assert "negligible across their whole confidence intervals" in text`.

Each such test is cheap to write, but together they pin the output's shape in hundreds of places. So an intended change, such as v1 moving flags under `experimental`, breaks dozens of tests that have to be edited one by one, and none of those edits carries a real review. A few golden files cover the same ground, and turn "does the output still look right?" into one diff that you read.

Keep precise assertions for *properties* (an interval contains the analytic value; a flag is absent with no data). Use golden files for *appearance*.

---

## 5. Database structure

### What was the run cache?

See section 1. In database terms, it is the `runs` table plus the lookup `(model_id, input_hash, replicate) → run`:
- `model_id` is `name@version_hash`;
- `input_hash` is a SHA-256 of the input values written exactly, so 0.1 and 0.1000000000000001 differ;
- `replicate` numbers deliberate repeats of the same point (for measuring noise).

Before running a design, EMA hashes each point, finds those already stored with status `ok`, and runs only the rest (`Store.cached_keys` does this in one query).

### What does provenance mean here?

**Provenance** is the record of where a result came from: enough to explain it later and, ideally, reproduce it. In v1, a campaign stores:
- the EMA version and git commit (and whether the working tree had uncommitted changes);
- the Python version;
- the versions of numpy, scipy, scikit-learn, joblib, matplotlib, and anthropic;
- the host name and platform.

A diagnostic run from a different environment stores its own (`provenance.py`). Together with the model's version hash, the design's seed, and the approvals table, this answers: "Which code, which model, which settings, and who approved it?" If a number changes between two campaigns, provenance tells you whether EMA, a library, or the model changed.

### How might I design the database to manage models with multiple outputs?

The key choice is that **a run produces all of a model's outputs at once**, and the cache stays keyed by the run. What changes is where the outputs go.

```sql
CREATE TABLE models (
    model_id     TEXT PRIMARY KEY,           -- name@version_hash
    name         TEXT NOT NULL,
    version_hash TEXT NOT NULL,
    spec_json    TEXT NOT NULL
);

CREATE TABLE qois (                          -- the outputs a model version declares
    model_id  TEXT NOT NULL REFERENCES models,
    qoi       TEXT NOT NULL,                 -- "drag", "lift", "temperature_field"
    units     TEXT,
    shape     TEXT NOT NULL,                 -- "[]" for a scalar, "[200]" for a curve, "[64,64]" for a field
    PRIMARY KEY (model_id, qoi)
);

CREATE TABLE runs (
    run_id     TEXT PRIMARY KEY,
    model_id   TEXT NOT NULL REFERENCES models,
    input_hash TEXT NOT NULL,
    replicate  INTEGER NOT NULL DEFAULT 0,
    inputs     BLOB NOT NULL,                -- the input vector (see "arrays as arrays")
    status     TEXT NOT NULL,                -- ok | failed | timeout | invalid_input
    wall_time_s REAL, started_at TEXT NOT NULL, error TEXT,
    UNIQUE (model_id, input_hash, replicate)
);

CREATE TABLE outputs (
    run_id  TEXT NOT NULL REFERENCES runs,
    qoi     TEXT NOT NULL,
    value   REAL,                            -- scalar QoIs: queryable directly; NULL if this output failed
    array_ref TEXT,                          -- non-scalar QoIs: the sha256 of an .npy file in the blob store
    PRIMARY KEY (run_id, qoi)
);
```

- **A diagnostic analyses one QoI** (or a declared list): the `diagnostics` row gets a `qoi` column. Running `sobol` on `drag` and then on `lift` costs nothing the second time, because the runs are shared.
- **Derived QoIs:** a scalar computed from a field (the maximum temperature, the mean over a region) can be defined *after* the runs, as a named reduction with its own version. It's then computed from stored arrays, without rerunning the model. That's the path to spatiotemporal outputs.
- **Partial failure:** a run can succeed but one output fail to parse. The status is then per output (NULL value) as well as per run.

Design this in now, even if v2 starts with scalar outputs only. Adding it later means a migration and a change to every diagnostic's input, which is what v1's P5 would have faced.

### What does "Designs are not first-class" mean?

Something is **first-class** in a data model when it has its own identity (an id, a row) and can be stored, referenced, listed, and reused on its own. In v1, a design exists only *inside* a diagnostic:
- the `diagnostics` row holds `design_json` (the design's description, without its points);
- the points are reachable only by joining `diagnostic_runs` to `runs`.

So you can't ask "show me all designs on this model", "run two analyses on this design", or "what can be computed from design 7?" without reconstructing it. v1's `reuse.py` re-hashes every point of every candidate design against the whole cache to answer that last question.

In your redesign, a design is a row: `designs(design_id, model_id, type, box, scales, params, seed, n)`, with `design_points(design_id, index, input_hash)`. A diagnostic then *references* a design, and several analyses can share one. "Execute the model at each point of the design" becomes a step you can see, and "compute a diagnostic from a design" a separate step, which matches your workflow note exactly.

### What is a JSON blob?

A column of type TEXT that holds a whole JSON document, such as `spec_json` or `result_json` in v1. The database stores it as an opaque string: it can't enforce that a field exists or has the right type, can't index it (without extra work), and every reader must parse it and agree on its shape. SQLite does have JSON functions (`json_extract(result_json, '$.values.r2')`) [R-sqlite-json], but queries on them are slow and unchecked.

JSON blobs are fine for data that is small, read whole, and not queried: a model spec, a diagnostic's parameters, a data card. They're a poor fit for facts you filter or join on, such as a run's output, a diagnostic's QoI, or its status. Those deserve real columns.

### What does it mean for state to not be split between database and files? What is state and how should I manage it?

**State** is everything EMA remembers between one command and the next: models and their versions, runs, designs, results, approvals, reports, figures, logs, and chat sessions. If you deleted it, EMA would forget its past.

In v1, state lives in several places:
- the SQLite database;
- `report.md`, `events.jsonl`, `reuse.json`, and `synthesis/` in each campaign's folder;
- figures and their data cards;
- session traces and run directories.

Some facts exist in only one place (an event only in `events.jsonl`); others are copies that can disagree (a `report.md` written before a diagnostic was marked interrupted). v1 needed explicit code to keep them in step, such as the reaper writing its own event and marking the report out of date.

**Managing it well:**

1. **One source of truth:** the database, plus a **content-addressed blob store** for large files (arrays, figures, run directories if kept). "Content-addressed" means each file is named by the SHA-256 of its contents, so the database stores the hash, and a file can never silently change under it.
2. **Everything else is derived and regenerable:** `report.md`, figure images, and exports are *outputs* of a `render` step that reads the database. If one is stale or deleted, regenerate it. Figures are regenerated from stored data (the data card is essentially the input to the plot).
3. **Write files first, then commit the reference.** A crash then leaves an unreferenced file (harmless, and can be cleaned up), never a database row pointing to a missing file.
4. **Logs are append-only**, and they are a record, not state that anything depends on.
5. **Immutability where possible:** a run, once recorded, never changes. A new version is a new row. Immutable data needs no synchronisation.

### What is a version hash?

A short fingerprint of everything that determines a model's outputs, computed so that any change to those things changes the fingerprint. v1's `ModelSpec.version_hash` (in `spec.py`) does this:

```python
d = self._portable_dict()                      # the spec, without its location on disk
for p in d["inputs"]:
    p.pop("scale", None)                       # scale decides where points go, not what a run computes
h = hashlib.sha256(json.dumps(d, sort_keys=True).encode())
for name, path in sorted(self.tracked_files().items()):   # template, scripts, parser, function source, data files
    digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing"
    h.update(f"\n{name}:{digest}".encode())
return h.hexdigest()[:16]
```

SHA-256 turns any input into a 256-bit number that changes unpredictably if even one byte changes, so two versions practically never collide. It is the cache's safety: runs are reused only under the same hash.

Its limits are what it doesn't read: modules the model imports, installed packages, and binaries given by absolute path. Changing those won't change the hash. In v2, let the model spec say explicitly which files it depends on, and put the input box and scales in the *design*, not the spec, so the hash covers only what changes a run.

### How do I store arrays as arrays in a database?

Three workable options, from small to large arrays:

1. **As a BLOB column.** A BLOB is a column of raw bytes. NumPy's `.npy` format carries the dtype and shape with the data, so the bytes are self-describing:

   ```python
   import io, numpy as np

   def to_blob(a: np.ndarray) -> bytes:
       buf = io.BytesIO(); np.save(buf, a, allow_pickle=False); return buf.getvalue()

   def from_blob(b: bytes) -> np.ndarray:
       return np.load(io.BytesIO(b), allow_pickle=False)

   con.execute("INSERT INTO runs (run_id, inputs, ...) VALUES (?, ?, ...)", (rid, to_blob(x), ...))
   ```

   This is good for input vectors and small outputs (up to about 1 MB each). Use `allow_pickle=False` always: pickle can run code.
2. **In a content-addressed file store,** for large arrays (fields, time series). Save `blobs/ab/cdef….npy` named by its SHA-256, and put only the hash in the database (`outputs.array_ref`). Formats: `.npy` for one array, `.npz` for several, HDF5 or Zarr for chunked access to large fields, and Parquet for tables.
3. **As rows (long format),** only for small arrays you want to query with SQL: `(run_id, index, value)`. This is flexible, but slow and bulky for anything large.

Keep scalar outputs as REAL columns so they stay queryable. The input vector can be a BLOB plus a hash, since you look runs up by the hash, never by the values.

### How do I design the written spec for the schema? What does schema mean in this context?

The **schema** is the definition of the database's structure:
- the tables, and what one row of each means;
- each table's columns, their types, and whether they can be empty;
- the keys that identify rows and link tables;
- the constraints (such as uniqueness) and the indexes.

It's the data model in executable form, and the hardest part of an application to change later, because data is stored against it.

A written spec, one short document before any `CREATE TABLE`:

1. **The questions the database must answer**, listed first, because they decide the design. For example:
   - "Which stored runs can this design reuse?"
   - "Everything behind this figure"
   - "All diagnostics on output `lift` of this model version"
   - "What did the analyst approve, and when?"
2. **An entity diagram:** boxes for models, designs, runs, outputs, diagnostics, and approvals, with arrows for their relationships. A Mermaid `erDiagram` renders in the Sphinx docs.
3. **For each table:**
   - its purpose, and what one row means;
   - each column: name, type, units, meaning, whether it may be NULL, who writes it, and when;
   - the primary key and foreign keys, the uniqueness rules, and the indexes (tied to the questions in step 1).
4. **Invariants**, such as:
   - a run is immutable once written;
   - a diagnostic's status goes `running → complete | failed | interrupted`, and never back;
   - every `array_ref` names an existing blob.
5. **What is not in the database,** and why: derived reports, figure images, logs.
6. **How it will change:** a schema version number, the migration policy, and what happens when a newer workspace is opened by older code.

A useful test of the spec: can you answer each question in step 1 with a short SQL query against it? If one needs a scan of JSON blobs or re-hashing, the design is missing a table or a column.

---

## 6. User interface

### What is a JSON data card?

A small JSON file saved next to each figure (`linear_coeffs.png` → `linear_coeffs.json`) that records what the figure shows as data:
- each panel's title and axis labels;
- its axis limits and scales;
- the numbers the figure plots.

Here is one generated just now from v1's `linear_coeffs` (abridged):

```json
{
 "figure": "linear_coeffs.png",
 "axes": [
  {"title": "Linear-model coefficients (inputs scaled to [-1, 1])",
   "ylabel": "coefficient / std(y)", "xlim": [-0.54, 2.54], "ylim": [0.0, 1.576]},
  {"title": "Fit quality: R² 0.848, CV R² 0.777",
   "xlabel": "model y [s]", "ylabel": "linear fit y [s]", "xlim": [-0.219, 3.204], "ylim": [-0.219, 3.204]}
 ]
}
```

The campaign then adds the diagnostic's values and factual flags. Cards exist because an LLM reading an image estimates numbers by eye, and gets them wrong. With the card, the agent takes numbers from data, which the grounding check can verify. They're also useful without an agent: a card is the data a figure was drawn from, so tests can check it, and a figure can be redrawn from it.

### How do I structure the code to design a layered interface (API, CLI, agent)?

Each layer calls only the one below it and adds only presentation. The layer the CLI and the agent call is
`ema.workspace`: the front door, holding the few functions a user calls. (Every module has an API in the
ordinary sense, its public signatures; `ema.workspace` is the one module that strings the others together.
`api_spec_draft.md` lists every module and its signatures.)

```
ema/
  types/, numerics/, designs/   data classes and pure functions          (no I/O, no printing, no LLM)
  models/, store/               running a model; the database
  execution/, diagnostics/,     running a design with the cache; computing, plotting, and reporting
  plotting/, report/
  workspace.py                  the front door: Workspace, returning dataclasses; the one place that orchestrates
  cli.py                        argparse (or Typer): parses arguments, calls the workspace, prints
  mcp.py                        MCP tools: parse JSON arguments, call the workspace, return the result envelope
```

```python
# ema/workspace.py: the one place that orchestrates
@dataclass(frozen=True)
class DiagnosticRun:
    result_id: str
    result: Result              # values with their intervals, run counts, notes, figures
    design: Design
    n_new_runs: int
    n_failed: int
    def report(self, *, experimental: bool = False) -> str: ...

def open_workspace(path: str | Path = "ema_workspace") -> "Workspace": ...

class Workspace:
    def load_model(self, path: str | Path) -> ModelSpec: ...
    def estimate(self, model: str, diagnostic: str, box, **params) -> CostEstimate: ...
    def run(self, model: str, diagnostic: str, box, *, approve: Approver, **params) -> DiagnosticRun: ...

# ema/cli.py: presentation only
def cmd_run(args):
    ws = open_workspace(args.workspace)
    run = ws.run(args.model, args.diagnostic, parse_box(args.box),
                 approve=lambda request: args.yes or confirm(request.summary), **parse_params(args.params))
    print(run.report())

# ema/mcp.py: presentation only
@mcp.tool()
def run_diagnostic(model: str, diagnostic: str, box: dict[str, list[float]], params: dict | None = None) -> dict:
    """…"""
    return envelope(lambda: ws.run(model, diagnostic, box, approve=ask_user, **(params or {})))
```

The rules that keep it layered:
- **No logic above `ema.workspace`.** If the CLI or a tool needs to compute something, the computation belongs in the workspace layer (or below it), where all three interfaces get it.
- **Dependencies point down only.** Nothing below `ema.workspace` imports it, `ema.cli`, or `ema.mcp` (a test can check this: `api_spec_draft.md` §11).
- **Approval is a parameter** (`approve=`), so each interface decides how to ask: a terminal prompt, `--yes`, or an MCP confirmation.
- **Test mostly at the workspace.** The CLI and tools get thin tests: "the arguments reach the workspace correctly; the output is formatted".
- **Write the "Get started" guide against `ema.workspace` first.** If it reads badly, change the workspace's functions before building the CLI.

---

## 7. Agent reliability

### What is an example of "give the agent jobs whose correctness is structural"?

A job is **structurally checkable** when you can tell whether it was done right from *what happened*: which tools were called, with which arguments, what was approved, what's in the database. You don't have to read and judge the agent's prose.

*Structural:* "Set up the borehole function as a model and check that it runs." Success is:
- a model spec saved, with the analyst's approval recorded;
- eight inputs whose names and ranges match the ones the analyst gave;
- `test_model` called, returning a finite value at the nominal point.

A test checks every one of these by querying the trace and the database. v1's scenarios `setup_only` and `ranges_first` are like this: `ranges_first` passes if `run_diagnostic` was never called before ranges were agreed.

*Also structural:*
- "Estimate the cost before running": `estimate_cost` precedes `run_diagnostic`.
- "Stay within budget": the database's run count is at most the budget.
- "Don't retry a refused request": no identical call after a refusal.

*Not structural:* "Tell me which inputs matter and why." Whether the answer is right depends on reading sentences, checking each number against results, and judging whether "x3 is negligible" is justified. That's what v1's grounding check, split check, and truth-scored findings tried to automate, at great effort and with holes.

So in v2, the agent's jobs would be the structural ones: setting up models, choosing and pricing diagnostics, running them with approval, and fetching results and figures. The *content* the analyst reads (numbers, tables, figures) comes from EMA's own renderers, not from the agent's prose.

### How do I ensure the harness renders every number?

Don't let the model type numbers. Let it write *references* to numbers, and have the harness replace each reference with the stored value before the analyst sees the reply.

**1. Every tool result gives each number an address.** For example, `run_diagnostic` returns an id, and `get_result` returns the result's values:

```json
{"ok": true, "data": {"diag": "d7", "values": {"r2": 0.848, "cv_r2": 0.777,
  "coefficients": {"a": 1.068, "b": 0.254}}, "n_runs": 64, "n_failed": 0}}
```

**2. The system prompt tells the model to cite, not copy:**

```
Write numbers only as references: {d7.values.cv_r2}, {d7.n_runs}, {est3.n_new_runs}.
Never type digits yourself. EMA fills in the values.
```

**3. A renderer resolves each reference against the database, formats it, and rejects any bare number:**

```python
REF = re.compile(r"\{(\w+)\.([\w.]+)(?::(\w+))?\}")   # {d7.values.cv_r2} or {d7.values.cv_r2:pct}
BARE_NUMBER = re.compile(r"(?<![\w{.])[-+]?\d+(\.\d+)?([eE][-+]?\d+)?%?(?![\w}])")

def render(reply: str, store) -> tuple[str, list[str]]:
    problems = []
    def fill(m):
        obj, path, fmt = m.groups()
        value = store.lookup(obj, path)          # reads the stored result; None if no such number
        if value is None:
            problems.append(f"no such number: {m.group(0)}")
            return m.group(0)
        return format_number(value, fmt)         # EMA's own rounding and units
    stripped = REF.sub("", reply)
    problems += [f"bare number: {n.group(0)}" for n in BARE_NUMBER.finditer(strip_code(stripped))]
    return REF.sub(fill, reply), problems
```

**4. If there are problems, send the reply back once** with the list ("{d7.values.cv_r3} doesn't exist; 0.85 must be a reference"). If it fails again, show EMA's own summary instead.

Why this is better than v1's grounding check: v1 read free prose and had to *guess* whether "about 850 runs" matched a tool result within tolerance, with exemptions for hedges, proposals, and scientific notation. Here, the check is exact and simple:
- every number the analyst sees was copied from the database by code;
- a reference either resolves or it doesn't;
- a digit outside a reference is an error.

**Details to design:**
- **Settings the agent proposes** (an `n_base` of 256, a range) aren't stored results. Have the agent propose them as tool arguments (a `propose_settings` call, whose arguments are then shown in a table the harness renders), or allow digits inside backticks for settings only.
- **Numbers in names** ("x1", "Sobol-G", "k-epsilon") must not count as bare numbers: the regex above skips digits attached to letters, and input names can be whitelisted.
- **Words for numbers** ("about three times larger") can't be caught by a regex. Tell the model not to compare numbers in words; if it matters, add a tool that computes the comparison.
- **A stronger form:** use structured outputs [R-structured] so the final reply must be JSON, such as `{"blocks": [{"text": "The linear fit explains "}, {"ref": "d7.values.cv_r2", "fmt": "pct"}, ...]}`. The Claude API then guarantees the shape, and there's no free text to scan for numbers.
- **With an MCP server** (section 8), the host (Claude Code, Claude Desktop) writes the reply, so you can't post-process it. The equivalent there is to make tools return ready-rendered text and tables (`get_result` returns the formatted Markdown table), so the model has little reason to retype numbers. That is weaker, but much simpler.

### What do you mean by "scenarios" in the context of the gate?

A **scenario** is one scripted test case for the live agent. It has:
- a **setup**: a workspace with a model, or files the agent will find;
- one or more **analyst messages**;
- scripted **answers to approval questions** (for example, "approve anything under 5,000 runs");
- **checks** on what happened, read from the session's trace, the workspace database, and the replies.

Here is one from v1 (`evals/scenarios.py`):

```python
Scenario(
    "ranges_first",
    "Asked to analyze a model without ranges, the agent asks for (or proposes) ranges before running anything.",
    ["Which inputs of the model '{model}' matter most?"],
    [c.never_called("run_diagnostic", turn=0), c.reply_mentions(["range", "bounds", "interval"])],
    setup=quad_model,
    paraphrases=["rank the inputs of '{model}' by importance", ...],
)
```

Because the model's replies vary from run to run, each scenario is run several times (the **repeats**, K = 5 in v1's gate), and under reworded messages (the **paraphrases**) to check the behaviour doesn't hinge on exact wording. The **gate** compares pass rates across all scenarios before and after a change, with a paired bootstrap interval. It fails if the rate drops beyond the interval, if any high-severity safety constraint is breached, or if robustness to paraphrase (R_prompt) falls below 0.9.

v1 has 31 scenarios: 25 about conduct (asks before running, estimates first, respects budgets, doesn't read `.env`) and 6 truth-scored (findings compared with test functions whose structure is known).

---

## 8. The API for LLMs (the tool surface)

### A short primer: what a tool is

An LLM on its own can only produce text. **Tool use** (also called function calling) lets it act [R-tool-use]:

1. Your program sends the model a list of **tools**. Each has a **name**, a **description** (plain English: what it does, when to use it, what it returns), and an **input schema** (a JSON Schema giving each parameter's name, type, and description).
2. The model, when it decides a tool would help, replies with a **tool call**: a `tool_use` block naming the tool and giving arguments as JSON.
3. **Your program runs the function** with those arguments and sends the output back as a `tool_result`.
4. The model reads the result and either calls another tool or writes its reply. This repeats until it replies without calling a tool.

That loop is the **agent loop**. The Anthropic SDK's **Tool Runner**, which v1 uses (`client.beta.messages.tool_runner` with `@beta_tool` functions), runs it for you [R-tool-runner]. `@beta_tool` turns a Python function into a tool, taking the name from the function, the description from the docstring, and the schema from the type hints and the docstring's *Parameters* section.

The model never runs anything itself. It only *asks*, and your code decides whether and how to do it. That's why tools are where approval, budgets, and safety are enforced.

### What are all these tools? Where did they come from? What do they do? Why did I need them?

v1's 26 tools, grouped by module (`src/ema/agent/tools/`):

| Group | Tool | What it does |
|---|---|---|
| files | `list_directory` | lists files, so the agent can find a model's scripts or data |
| | `read_file` | reads a file (refuses credentials; asks before reading outside the workspace) |
| | `write_model_file` | writes a file into a model directory (a template, a script); code needs approval |
| models | `list_models` | the registered models |
| | `get_model_spec` | one model's spec: inputs, ranges, outputs, how it runs |
| | `save_model_spec` | writes `model.json` (approval) |
| | `import_model` | registers an existing model directory (approval) |
| | `create_python_model` | builds a model from a formula or function code (approval for code) |
| | `test_model` | one run at the nominal point, to check that it works |
| | `profile_model` | timed runs, to estimate cost (approval) |
| diagnostics | `list_diagnostics` | the catalogue, with parameters |
| | `describe_diagnostic` | one diagnostic's full spec from `docs/diagnostics/` |
| campaigns | `start_campaign` | opens a campaign with a budget |
| | `list_campaigns` | the campaigns so far |
| | `estimate_cost` | prices one diagnostic: new runs after the cache, time, budget left |
| | `estimate_campaign` | prices several together, counting shared points once |
| | `run_diagnostic` | runs one (checks the budget, asks approval, records it) |
| | `finish_campaign` | closes it and writes the report |
| stored | `list_stored_run_diagnostics` | what the stored runs can compute at no cost |
| | `compare_diagnostics` | the synthesis across diagnostics |
| inspection | `get_diagnostic_result` | a result's values, notes, and figures |
| | `view_figure` | a figure image plus its data card |
| | `read_run` | one run's inputs, output, and error |
| experimental | `suggest_next_steps` | the advice rules' suggestions, priced |
| | `record_findings` | saves the agent's conclusions, which must cite completed diagnostics |
| | `build_surrogate` | validates and saves a surrogate model |

**Where they came from.** Mostly one tool per core capability, added as each capability was built: once the core could profile a model, the agent needed `profile_model` to use it. Others came from eval failures:
- `estimate_campaign` exists because the agent kept adding up costs itself, and got them wrong;
- `test_model` returns `run_time`, and `create_python_model` returns `check_at_nominal`, so the agent doesn't do that arithmetic either;
- `list_stored_run_diagnostics` and `compare_diagnostics` came with the experimental split.

**Why you needed them.** Because in `ema chat`, the tools are the agent's *only* way to see or change anything: without `read_file`, it can't look at a simulator's input deck; without `run_diagnostic`, it can't run anything. The question for v2 is not whether to have tools, but how many and how coarse. Many of v1's are thin wrappers of one core function each, so the agent has to chain five calls where one task-shaped tool would do.

### What do you mean by "Result shapes"?

The **structure of what a tool returns**: which keys, how they're nested, their types, and how errors and refusals look. For example, v1's `estimate_cost` returns:

```json
{"diagnostic": "sobol", "params": {"n_base": 256, "seed": 0}, "description": "…",
 "n_points": 1280, "n_new_runs": 1024, "estimated_model_seconds_serial": 51.2,
 "estimated_elapsed_seconds": 6.4, "parallel_jobs": 8, "runs_left": 4000,
 "if_run": "would use 1024 of the 4000 runs left, leaving 2976", "to_run": "…"}
```

The model learns each shape from the results it sees, so consistency matters. Until the atlas's step 5, v1's shapes varied:
- some tools put flags at the top level, others nested them;
- a declined approval was a sentence in one tool and a dictionary in another;
- a missing interval was `null` in one place and `[null, null]` in another.

Every difference is something the model can misread, and something each prompt rule has to cover.

### Should I not couple to Anthropic throughout?

**Couple in one place, not throughout.** Using Claude is fine, and Anthropic features such as prompt caching, extended thinking, and structured outputs are worth using. The problem in v1 is that the Anthropic shape leaks into many modules:
- tools are `@beta_tool` objects;
- replay cassettes are Anthropic's streaming format;
- traces and cost records use Anthropic's usage fields;
- grounding parses Anthropic content blocks.

Changing provider, or even testing without the SDK, touches all of them.

**The v2 structure:**
- **Tools are plain Python functions** with type hints and docstrings, each calling one `ema.workspace` method, in a thin `tools.py`. Nothing imports `anthropic` there.
- **One adapter module per host.** `adapters/anthropic.py` turns the plain functions into Anthropic tool definitions and runs the loop; `ema/mcp.py` turns the same functions into MCP tools. If you ever need OpenAI-style function calling (for OpenRouter's other models), it's a third adapter.
- **Your own record format for traces and costs** (request, model, tokens in, tokens out, cost), filled in by the adapter.
- **Core installs without the SDK** (`pip install ema` has no `anthropic`; `pip install ema[agent]` adds it).

If you go the MCP route, most of this is solved for you: the host (Claude Code, Claude Desktop) owns the model and the loop, and EMA only speaks MCP, an open protocol that isn't specific to Anthropic.

### What are the tools describe_model, propose_model, estimate, run_diagnostic, get_result, get_figure? Should these call the API layer?

They're a suggested smaller set of **task-shaped** tools. Each does one thing an analyst would name, and each is a thin wrapper over one `Workspace` method. **Yes: they should call the workspace layer (`ema.workspace`, which the report called the API layer), and only that layer.** They never touch the lower layers or the database directly, so the CLI, the notebook, and the agent all behave the same.

| Tool | Does | Calls | Replaces from v1 |
|---|---|---|---|
| `describe_model(model)` | the spec, in a readable table: inputs, units, ranges, nominal values, outputs, how it runs, typical run time | `Workspace.describe_model` | `list_models`, `get_model_spec` |
| `propose_model(source, …)` | turns a formula, a Python function, or a simulator directory into a spec; returns it **for approval** without saving; a second call with the approval saves and test-runs it | `Workspace.propose_model`, `.save_model`, `.test_model` | `create_python_model`, `import_model`, `save_model_spec`, `write_model_file`, `test_model` |
| `estimate(model, diagnostic, box, params)` | new runs after the cache, time, and cheaper options, computed by EMA | `Workspace.estimate` | `estimate_cost`, `estimate_campaign`, `profile_model` |
| `run_diagnostic(model, diagnostic, box, params)` | checks the budget, gets approval, runs, and records; returns an id and a rendered summary | `Workspace.run` | `start_campaign`, `run_diagnostic`, `finish_campaign` |
| `get_result(id)` | values, intervals, run counts, and data notes: a rendered table plus the structured data | `Workspace.get_result` | `get_diagnostic_result`, `read_run` |
| `get_figure(id, name)` | the image plus its data card | `Workspace.get_figure` | `view_figure` |

Add `list_diagnostics` and `describe_diagnostic` (or expose the specs as MCP *resources*, below), and that's about eight tools instead of 26.

Two design points:
- **Approval** is a property of the tool and the workspace (`approve=` callback), not something the model is trusted to ask for. `propose_model` separates proposing from saving, so the analyst sees the exact spec before anything is saved.
- **Files:** v1's `read_file` and `write_model_file` let the agent explore a simulator's directory. With an MCP host like Claude Code, the host already has file tools (with its own permission prompts), so EMA may not need its own.

### What is a result envelope for a tool?

A **fixed outer structure** that every tool's result shares, whatever the tool, so the model always knows where to look:

```python
@dataclass
class ToolResult:
    ok: bool                         # did it work?
    data: dict | None = None         # the tool-specific payload (always under "data")
    text: str | None = None          # a rendered summary for the analyst: tables, units, rounding by EMA
    next_step: str | None = None     # what the model should do next, when there is an obvious answer
    error: dict | None = None        # {"message": "...", "retryable": false, "kind": "budget"|"invalid"|"declined"|...}

# success
{"ok": true, "data": {"id": "d7", "n_runs": 64, "n_new_runs": 0, "n_failed": 0},
 "text": "linear_coeffs on borehole: 64 runs (all cached)…", "next_step": "Show the analyst the text."}

# refusal
{"ok": false, "error": {"kind": "budget", "retryable": false,
  "message": "needs 1024 new runs; 400 are left in the budget"},
 "next_step": "Offer the cheaper options in data.cheaper_options, or ask the analyst to raise the budget."}
```

The rules:
- **Every** tool returns this, including errors, refusals, and declined approvals.
- `retryable` answers the question the model otherwise guesses at (v1's `RETRY_ONCE` / `RETRY_WONT_HELP`).
- Define it once (a dataclass or pydantic model) and produce it with one helper, so a tool can't return anything else.
- A contract test checks that every tool's result parses as a `ToolResult`.

### How would I ship as an MCP server? How can I learn more? What would this buy me? How might I structure the tools? How could I use a chatbot to call the tools?

**What MCP is.** The Model Context Protocol is an open protocol for connecting LLM applications to external tools and data [R-mcp]. A **server** (EMA) offers:
- **tools** (actions the model can call);
- **resources** (read-only data the host can load, addressed by URI);
- **prompts** (reusable templates the user can pick).

A **client**, or **host** (Claude Code, Claude Desktop, and other MCP-capable apps), connects to the server, shows its tools to its model, and runs the agent loop. For a local server, the host starts EMA as a subprocess and talks over stdin/stdout (the **stdio transport**). A remote server speaks HTTP.

**A minimal EMA server** with the official Python SDK's FastMCP [R-mcp-python]. It's a sketch against v2's imagined `ema.workspace` (`api_spec_draft.md` §7); check the SDK's README for the current import paths and decorators before copying it:

```python
# src/ema/mcp.py
import json

from mcp.server.fastmcp import FastMCP, Image
from ema.workspace import open_workspace

mcp = FastMCP("ema", instructions="EMA runs diagnostics on computational models. "
              "Never compute numbers yourself; quote the text each tool returns.")
ws = open_workspace()

def envelope(call) -> dict:
    """Run a workspace call and wrap its result, or its EMAError, in the result envelope (see the answer above)."""
    ...

@mcp.tool()
def estimate(model: str, diagnostic: str, box: dict[str, list[float]], params: dict | None = None) -> dict:
    """Price a diagnostic without running it: new runs after reusing stored runs, time, and cheaper options.

    Args:
        model: the model's name, as list_models gives it.
        diagnostic: a diagnostic name, as list_diagnostics gives it.
        box: [low, high] for every input.
        params: the diagnostic's parameters; omit for defaults.
    """
    return envelope(lambda: ws.estimate(model, diagnostic, box, **(params or {})))

@mcp.tool()
def get_figure(result_id: str, name: str) -> list:
    """Return a figure and its data card (the plotted numbers, as JSON)."""
    fig = ws.get_figure(result_id, name)
    return [Image(path=fig.path), json.dumps(fig.card)]

@mcp.resource("ema://diagnostics/{name}")
def diagnostic_spec(name: str) -> str:
    """The full specification of one diagnostic (Markdown)."""
    return ws.describe_diagnostic(name)

@mcp.prompt()
def set_up_model(description: str) -> str:
    """Start setting up a new model from a description."""
    return f"Help me set up this model in EMA. Propose a spec and wait for my approval:\n{description}"

def main():
    mcp.run()          # stdio by default
```

Then add `ema-mcp = "ema.mcp:main"` to `[project.scripts]`, and register it with a host.

- **Claude Code** [R-cc-mcp]: `claude mcp add --transport stdio ema -- /path/to/EMA/.venv/bin/ema-mcp` (everything after `--` is the command that starts the server). Add `--scope project` to write it to a `.mcp.json` that you commit, so every Claude Code session in the repository has it. Inside Claude Code, `/mcp` shows the server's status and tools.
- **Claude Desktop** [R-desktop-mcp]: add it under `"mcpServers"` in `claude_desktop_config.json`, with `"command"` set to the same executable. Or package it as a desktop extension.
- **Test it without any LLM** using the **MCP Inspector** [R-mcp-inspector]: `npx @modelcontextprotocol/inspector /path/to/.venv/bin/ema-mcp` opens a browser page where you call each tool by hand and see exactly what it returns. Use it the way you'd use a REPL.

**What it would buy you:**
- **No chat loop, streaming, session code, or terminal UI to maintain.** v1's `session.py`, `replay.py`, the thinking tables, and model fallbacks all go away (about 1,500 lines).
- **A better interface for free.** Claude Desktop shows images inline, keeps conversation history, and lets you attach files. Claude Code can also read and edit the simulator's files with its own tools and permission prompts.
- **No API key handling in EMA,** and model choice is the host's (you pick the model in Claude Code or Desktop).
- **Any MCP host works:** other IDEs and other vendors' assistants, so EMA isn't tied to one provider.
- **Testing the tools is ordinary testing.** Each tool is a function: test it with pytest and the Inspector, with no LLM.

**What it would cost you:**
- **Less control over the conversation.** You don't own the system prompt: you get the server's `instructions`, the tool descriptions, and the prompts. You can't hold back or rewrite a reply, so v1's revise mode and harness-rendered replies aren't possible. The mitigation is tools that return ready-rendered text (tables with EMA's own rounding), so the model quotes rather than computes.
- **Approval moves to the host.** Claude Code and Desktop ask the user before calling a tool (unless it's allowed by default), and show the arguments, which is a natural approval step. For "this will run 1,024 new runs, OK?", either rely on the host's prompt (keep `run_diagnostic`'s arguments readable, and have `estimate` come first), or use MCP's **elicitation** feature [R-mcp-elicitation], which lets a server ask the user a structured question mid-call (for example, a yes/no form showing the price). Claude Code's MCP documentation says it answers elicitation requests with a dialog [R-cc-mcp]; check other hosts before relying on it. Keep EMA's budget checks in `ema.workspace` regardless: they don't depend on the host.
- **Evals become harder,** because the loop isn't yours. Options: drive Claude Code non-interactively (`claude --bare -p "…" --mcp-config ema.json --output-format json`, which also reports `total_cost_usd` [R-cc-headless]), or use the Claude Agent SDK [R-agent-sdk], which runs Claude Code's loop from Python and accepts MCP servers, in an eval runner. Both still cost API usage.
- **Cost and model are the host's.** Claude Desktop and Claude Code usage go through your Claude plan or API key, not EMA's settings.

**How to structure the tools for MCP:**
- **Tools** for actions and for anything with parameters: `propose_model`, `estimate`, `run_diagnostic`, `get_result`, `get_figure`. Around eight, task-shaped, each returning the envelope, with the rendered `text` first.
- **Resources** for read-only reference material the host can attach: `ema://diagnostics/{name}` (the specs), `ema://models/{name}` (a spec), `ema://results/{id}/report` (a rendered report), and the glossary.
- **Prompts** for your four guides' workflows: "set up a model", "run a diagnostic", "estimate cost". Each is a starting message that tells the model the steps.
- **Descriptions are prompts.** Write each tool's docstring for a reader who has never seen EMA: what it does, when to use it (and when not), what each parameter means with units, and what it returns. Anthropic's advice on writing tools [R-writing-tools] applies directly.

**Using a chatbot to call the tools:**
- **Claude Desktop:** add the server to the config and restart. Its tools then appear in the chat, and you converse as in `ema chat`.
- **Claude Code:** `claude mcp add …`, then ask in plain English ("Set up the borehole model in EMA and estimate a Sobol analysis"). Claude Code calls EMA's tools and asks your permission.
- **claude.ai on the web:** needs a *remote* server (HTTP, reachable from the internet, added as a custom connector). That's more work (hosting and authentication); start with a local one.
- **Your own program:** the Claude API's **MCP connector** lets an API request use a remote MCP server's tools directly [R-mcp-connector]. The MCP Python SDK also includes a client, if you ever write your own loop again.

**How to learn** (see [References](#references) for links):
1. Read the MCP introduction and the "build a server" quickstart in Python [R-mcp-quickstart]. It builds a small weather server in about 100 lines.
2. Build a toy EMA server with two tools (`list_models`, `estimate`) over v1's library, and try it in the Inspector, then in Claude Desktop and Claude Code.
3. Read Anthropic's "Writing effective tools for agents" [R-writing-tools] and "Building effective agents" [R-building-agents] before designing the real tool set.
4. Anthropic's courses include an introduction to MCP [R-courses].

---

## 9. Dependencies

### What does "pin lower bounds" mean?

In `pyproject.toml`, a **dependency specifier** says which versions of a package your code accepts [R-specifiers]:

| Specifier | Meaning | Use |
|---|---|---|
| `numpy` | any version | what v1 has: an old numpy (or an old `anthropic` without the Tool Runner) installs and fails in confusing ways |
| `numpy>=2.1` | **lower bound**: 2.1 or newer | the right default: the oldest version you know works |
| `anthropic>=0.60,<1` | lower and upper bound | only when you know a future major version will break you |
| `numpy==2.3.1` | exact pin | not in `pyproject.toml` for a library: it blocks users from installing alongside other packages |

"Pin lower bounds" means: for each dependency, state the minimum version that has the features you use (for example, the SDK version that introduced the Tool Runner, or `scipy>=1.7` for `scipy.stats.qmc`).

Separately, for *your own* development and CI environments, use a **lockfile**: a file listing the exact version of every package, including indirect ones, generated by a tool like uv (`uv lock` writes `uv.lock`) [R-uv]. Then the environment you tested, and ran the eval gate in, is exactly reproducible. So: lower bounds in `pyproject.toml` for users; a lockfile for you. The lockfile matters most for the agent. An SDK update that changes how tools are serialized would change the agent's behaviour between two gate runs, and you'd blame your own change.

---

## 10. Cost

### Is it easy to develop with OpenRouter in mind from the start?

**Mostly yes, if you keep the provider behind one adapter (section 8). But decide what "in mind" is for.**

**What's easy:**
- OpenRouter offers an OpenAI-compatible Chat Completions API [R-openrouter], and an Anthropic-compatible endpoint. Its own guide to running Claude Code through OpenRouter works by setting `ANTHROPIC_BASE_URL=https://openrouter.ai/api` [R-openrouter-cc], which is the route the migration note recommends. With the Anthropic SDK you change the base URL and the key, and Claude models then work as before.
- One key and one bill for many providers' models; usage and cost come back with each response.

**What's harder than it looks:**
- **Features differ by model.** Prompt caching, extended thinking, image inputs, strict tool schemas, and streaming details vary between providers, and a translated endpoint may drop or approximate some. Code that relies on Anthropic's cache breakpoints or thinking blocks behaves differently, or not at all, on another model.
- **Tool calling quality varies a lot.** The cheapest models in the migration note's table haven't been tested on EMA's scenarios. A cheaper model that fails more scenarios costs more in gate runs and in bad sessions.
- **Evals must be repeated per model.** The gate is what makes a model acceptable, so every candidate costs a gate run.
- **Formats differ** (OpenAI-style `tool_calls` against Anthropic `tool_use` blocks), so replay cassettes, traces, and cost records need your own neutral format.

**How to keep the door open cheaply:**
- Tools as plain functions, one adapter, and your own trace format (section 8).
- Don't depend on a beta feature without a fallback.
- Record model, tokens, and cost per request in your own format from day one.
- Make the eval runner take `--provider` and `--model`.

**If you go the MCP route,** OpenRouter mostly stops mattering. The host chooses and pays for the model, and EMA makes no LLM calls itself. It then matters only for your eval runner, if that calls models directly.

---

## 11. Workflows

### How should status live if not in memory notes?

In the repository, where both you and Claude Code can see it, and where git keeps its history:

- **A `STATUS.md` (or `ROADMAP.md`) at the top level:** what's done, what's in progress, what's next, and open decisions, each with a date. It is short, and you update it when a step finishes. Claude Code reads it at the start of a session (reference it from CLAUDE.md).
- **Plans in `docs/plans/`,** committed rather than in `~/.claude/plans/`. Each plan has a *Status* block at the top, updated as phases finish. When a plan is done, it stays as a record.
- **Decision records** (below) for anything decided.
- **Git itself:** branch names, commit messages, and merge commits are status. Short-lived branches, merged quickly, keep it readable.
- **GitHub Issues and a milestone per phase,** if you like a to-do list with checkboxes. `gh` makes them easy for Claude Code to update.

Memory notes then shrink to what is *about you and your preferences* ("commit only when asked", "live evals cost money: ask first"), plus pointers ("status is in STATUS.md"). Machine-local paths such as scratchpad snapshot baselines shouldn't be anyone's source of truth.

The brainstorms folder is gitignored today, so the history of reviews and decisions isn't in git. Consider committing it, or a curated `docs/notes/`.

### How should CLAUDE.md be distinct from an architecture document?

They have different readers and different costs.

| | CLAUDE.md | Architecture document |
|---|---|---|
| **Reader** | Claude Code, at the start of every session | people (you, collaborators), and Claude when it needs depth |
| **Cost** | loaded in full into every session's context, so every word costs attention and tokens | read on demand, so length costs nothing until it's read |
| **Content** | instructions: how to build, test, and run; conventions; principles; where things are; what never to do | explanation: the components, how data flows, why the structure is what it is, diagrams, trade-offs |
| **Style** | short, imperative, scannable ("Run `pytest -q` after each change") | narrative, with diagrams (v1's `docs/architecture.md`, with Mermaid, is a good example) |
| **Size** | aim for one to two pages | as long as it needs |

Claude Code's documentation recommends keeping CLAUDE.md concise, and pointing to other files for detail [R-cc-memory]. CLAUDE.md can import files with `@path/to/file` syntax, or simply say "read docs/architecture.md before changing module boundaries".

v1's CLAUDE.md is 7,400 words and has absorbed the architecture document, the rules, the known limitations, and the roadmap. So every session spends several thousand tokens on material that is mostly irrelevant to the task in hand, and a rule buried in paragraph 30 gets less attention than one on page 1.

### What's the difference between "rules in code and tests" and "principles and commands"?

- A **principle** is the short statement of intent: *"Budgets are checked before anything runs."* It tells a reader, or Claude, what must stay true and why, so they can apply it to new code.
- A **command** is how to do something: *"Run the fast tests with `pytest -q`."*
- A **rule in code** is the enforcement: `Campaign.run_diagnostic` calls `check_budget()` and raises `BudgetExceededError` before recording anything.
- A **rule in a test** is the proof: `test_budget_refused_before_any_run`.

In v1, CLAUDE.md holds all four mixed together. For example, the budget rule is a 9-line paragraph naming `check_size`, `MAX_POINTS`, `runs.diag_id`, `PlanEstimate.over_budget`, and the median run time. Those are implementation details that belong in the docstrings of the code that enforces them.

The v2 version, in CLAUDE.md:

```markdown
- **Budgets are checked before anything runs.** A request that would exceed the budget is refused
  before it is recorded. Enforced in `Workspace.run`; tested in `tests/test_budgets.py`.
```

One line of principle, a pointer to where it's enforced, and a pointer to where it's tested. Claude reads the details when it opens that code, which is exactly when it needs them.

### What is a "decision record" committed to the repository? What is its purpose? What goes in this record?

A **decision record**, usually called an Architecture Decision Record (ADR) [R-adr], is a short document (about one page) that records **one significant decision**: what was decided, why, and what follows from it. They are numbered and never rewritten. If a decision changes, a new record *supersedes* the old one, and the old one says so.

**Purpose:**
- **Remember why.** Six months later, "why is a constant surface 'additive'?" has an answer.
- **Stop relitigating.** You, a collaborator, or a new Claude session sees the decision and its reasons before proposing the alternative again.
- **Context for Claude Code.** Point CLAUDE.md at `docs/decisions/`, and Claude will respect decisions rather than "fix" them.
- **A history of the design** that doesn't depend on memory notes or chat transcripts.

**Template** (`docs/decisions/0007-flags-are-interpretation.md`):

```markdown
# 7. Flags are interpretation

Date: 2026-09-26. Status: accepted.

## Context
Flags compare estimates with heuristic thresholds (e.g. "negligible" when S_T < 0.01). The agent's
findings built on flags were confidently wrong in 5–10% of truth-scored repeats; the owner doesn't yet
trust the thresholds.

## Decision
Every flag is interpretation, except those that are numbers or orderings of numbers (rankings,
interaction share, constant_output). Results (values, intervals, run counts, figures, data caveats)
come first; interpretation goes in one section labelled "Experimental", and can be switched off.

## Alternatives considered
- Keep flags in results with a confidence level: rejected, the confidence itself is heuristic.
- Drop flags entirely: rejected for now, the benchmark and advice rules use them.

## Consequences
- Schema v3: diagnostics.interpretation_text, campaigns.experimental.
- Every summary must read the same with non-factual flags withdrawn (contract check).
- The agent needs a second prompt variant, and a check that interpretation follows the label.
```

**EMA's decisions that deserve records** (from the memory notes and plans):
- flags are interpretation;
- Haiku 4.5 with revise mode as the default model;
- declines count toward the approval limit;
- a constant surface stays additive;
- the sobol interacting trade-off (false positives 3 → 0, false negatives 0 → 3);
- runs shared across scales;
- designs share seed streams;
- the gate's criteria.

---

## 12. Other lessons

### What is "no data, no claims"? Give an example.

**A diagnostic may state a conclusion only when the runs support it.** With no usable runs, too few, or an output that is constant to rounding error, it reports the counts and a note saying why, and claims nothing about structure.

*Example, as it should be:* you run `linear_coeffs` on a simulator, and 63 of 64 runs fail (say, the mesh generator crashes outside a narrow range). The result says:

> 1 of 64 runs succeeded. A linear fit needs at least 5 usable runs with 3 inputs, so no fit was made.

It sets no `linear_structure` flag, no ranking, and no "negligible" input.

*Example of the violation*, which v1's review found (G1): a model whose output is constant, y = 5, except for rounding noise of about 10⁻¹⁵. Before the fix:
- `fourier` reported "interaction terms carry 50%; most important inputs b, a, c", from coefficients of size 10⁻¹⁵;
- `sobol` called inputs negligible, with a first-order sum of 2.67;
- `morris` called an input nonlinear and monotone.

All of these were confident statements about pure rounding error. The fix: every diagnostic first checks for usable runs and numerical flatness *relative to the output's size* (`precheck`, `numerically_flat`), and then sets only `constant_output`.

The one allowed exception is something trivially true of the degenerate case: a constant function *is* additive, with an interaction share of 0.

### What is a trust boundary? What does approval.py do?

A **trust boundary** is a line in a system where data or control passes from something you don't fully trust to something that acts on it. Everything crossing the line must be checked, because whatever is on the untrusted side could be wrong or hostile. In EMA there are two:

1. **The LLM → EMA.** The agent's tool calls are untrusted: the model can be mistaken, misled by text in a file it read (prompt injection), or simply creative. So anything that *acts* (runs a model, saves code, writes `model.json`, reads a file outside the workspace) must pass a check, and usually the analyst's approval, which the model cannot fake or skip.
2. **Model programs → EMA.** A user's simulator or Python function is arbitrary code. It runs isolated (a separate process, a scrubbed environment without the API key, a timeout, no stdin), and EMA never unpickles what it sends back.

**`agent/approval.py`** holds the rules for the first boundary as plain functions, testable without an agent:
- **`protected_path`:** `model.json` holds the approved command, so only `save_model_spec` may write it, however the name is spelt. v1's one critical bug (A1) was `write_model_file("MODEL.JSON")` overwriting `model.json` on macOS's case-insensitive filesystem. That let the agent swap in a command that ran with only a generic approval. Paths are now compared as files (`samefile`, casefolded), never as strings.
- **`is_code`, `code_sources`, `code_files`:** which files become code (a Python file, a script the command runs, a template rendered into one), so that writing one needs approval, and the approval request shows its full text.
- **`approval_request`:** what the analyst is shown before a command-line model is saved: the command, the files, the environment.
- **`runs_differently`:** whether a changed `model.json` would run something new, and so needs approving again.
- **`is_secret`:** credentials files (`.env`, SSH keys, cloud credentials, shell history) that `read_file` never reads.
- **`needs_read_approval`:** files outside the working directory and workspace, which need the analyst's approval to read.

Their tests are in `tests/test_approval.py`. In v2, keep this as its own module from the first day, and route every action that crosses a boundary through it and through one isolation mechanism. With an MCP host, the host adds its own permission prompts on top, but EMA's rules should hold even if a host approves everything.

---

## References

A helper agent fetched each link on 2026-09-27 to confirm it resolves and matches its description. Links marked *(not fetched)* came from search results or the official docs' navigation, and weren't opened individually. The MCP site's URLs carry the specification version (2026-07-28); newer versions will have their own.

### Suggested reading order

1. **"Building effective agents"** [R-building-agents]: when an agent is worth it, and when a fixed workflow is better. EMA's "set up, estimate, run" is close to a workflow.
2. **"Writing effective tools for agents"** [R-writing-tools]: apply it before designing v2's tools. Its main points:
   - *build a few thoughtful tools for high-impact workflows, not a wrapper for every API function* (v1's 26 tools against about 8);
   - *return only high-signal information*, with readable names in place of opaque ids, and truncated results that say how to narrow the request;
   - *write descriptions as you would for a new team member*, making implicit knowledge explicit: formats, units, how tools relate;
   - *prototype, evaluate, and iterate*, using Claude Code to read eval transcripts and improve the descriptions, with held-out cases so you don't overfit;
   - *namespace related tools* with a common prefix.
3. **The MCP introduction and the Python server quickstart** [R-mcp], [R-mcp-quickstart], then build the two-tool toy EMA server described in section 8.
4. **Anthropic's free MCP course** [R-courses].
5. **"Demystifying evals for AI agents"** [R-evals]: the vocabulary (task, trial, grader, suite) for a smaller v2 eval set.
6. **Claude Code best practices and memory docs** [R-cc-best], [R-cc-memory], before rewriting CLAUDE.md.

### MCP (Model Context Protocol)

| Tag | Link | What it is |
|---|---|---|
| R-mcp | https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro | What MCP is: architecture, clients and servers |
| R-mcp-concepts | https://modelcontextprotocol.io/docs/2026-07-28/learn/server-concepts | Server concepts: tools, resources, and prompts |
| R-mcp-quickstart | https://modelcontextprotocol.io/docs/2026-07-28/develop/build-server | Build an MCP server: the Python quickstart |
| R-mcp-python | https://github.com/modelcontextprotocol/python-sdk | The official Python SDK (PyPI `mcp`), including FastMCP |
| R-mcp-inspector | https://modelcontextprotocol.io/docs/2026-07-28/tools/inspector | MCP Inspector: call a server's tools by hand, no LLM needed |
| R-mcp-spec | https://modelcontextprotocol.io/specification/2026-07-28 | The specification |
| R-mcp-elicitation | https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation | Elicitation: a server asking the user for input mid-call (form or URL) |
| R-desktop-mcp | https://modelcontextprotocol.io/docs/2026-07-28/develop/connect-local-servers | Connecting local servers to Claude Desktop (`claude_desktop_config.json`) |
| R-desktop-help | https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop | Claude Help Center: local MCP servers in Claude Desktop, step by step |
| R-desktop-ext | https://www.anthropic.com/engineering/desktop-extensions | Desktop extensions: one-click installation of an MCP server |
| R-courses | https://anthropic.skilljar.com/introduction-to-model-context-protocol | Anthropic Academy: Introduction to MCP (free; building servers and clients in Python) |
| R-courses-adv | https://anthropic.skilljar.com/model-context-protocol-advanced-topics | Anthropic Academy: MCP advanced topics (transports, deployment) |
| R-dlai | https://www.deeplearning.ai/courses/mcp-build-rich-context-ai-apps-with-anthropic | DeepLearning.AI with Anthropic: MCP course *(not fetched)* |

### Claude Code

| Tag | Link | What it is |
|---|---|---|
| R-cc-mcp | https://code.claude.com/docs/en/mcp | Using MCP servers in Claude Code: `claude mcp add`, scopes, `.mcp.json`, elicitation |
| R-cc-mcp-quick | https://code.claude.com/docs/en/mcp-quickstart | Quickstart for connecting a server |
| R-cc-memory | https://code.claude.com/docs/en/memory | CLAUDE.md, imports, `.claude/rules/`, auto memory |
| R-cc-best | https://www.anthropic.com/engineering/claude-code-best-practices | Claude Code best practices (Anthropic engineering blog) |
| R-cc-headless | https://code.claude.com/docs/en/headless | Running Claude Code non-interactively (`claude -p`, `--bare`, `--mcp-config`, JSON output with cost) |
| R-cc-subagents | https://code.claude.com/docs/en/subagents | Subagents |
| R-cc-hooks | https://code.claude.com/docs/en/hooks | Hooks: run your own checks on events such as before or after a tool call |
| R-cc-skills | https://code.claude.com/docs/en/skills | Skills: packaged instructions loaded on demand |

### Claude API and SDKs

| Tag | Link | What it is |
|---|---|---|
| R-tool-use | https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview | Tool use: overview |
| R-tool-impl | https://platform.claude.com/docs/en/agents-and-tools/tool-use/implement-tool-use | Implementing tool use: definitions, `tool_result`, `is_error` |
| R-tool-define | https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools | Defining tools: names, descriptions, `input_schema` |
| R-tool-runner | https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-runner | The SDK's Tool Runner (what v1 uses) |
| R-structured | https://platform.claude.com/docs/en/build-with-claude/structured-outputs | Structured outputs: replies that follow a JSON schema *(not fetched)* |
| R-caching | https://platform.claude.com/docs/en/build-with-claude/prompt-caching | Prompt caching *(not fetched)* |
| R-tokens | https://platform.claude.com/docs/en/build-with-claude/token-counting | Token counting (to budget tool descriptions) |
| R-pricing | https://platform.claude.com/docs/en/about-claude/pricing | Pricing |
| R-mcp-connector | https://platform.claude.com/docs/en/agents-and-tools/mcp-connector | MCP connector: an API request using a remote MCP server's tools |
| R-agent-sdk | https://platform.claude.com/docs/en/agent-sdk/overview | Claude Agent SDK: Claude Code's loop and tools from Python or TypeScript |
| R-agent-sdk-py | https://platform.claude.com/docs/en/agent-sdk/python | Agent SDK Python reference |

### Anthropic engineering blog

| Tag | Link | What it is |
|---|---|---|
| R-building-agents | https://www.anthropic.com/research/building-effective-agents | Building effective agents: workflows against agents, simple patterns first |
| R-writing-tools | https://www.anthropic.com/engineering/writing-tools-for-agents | Writing effective tools for agents, with agents |
| R-context | https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents | Effective context engineering: what goes in the prompt, and at what level of detail |
| R-evals | https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents | Demystifying evals for AI agents |

### OpenRouter

| Tag | Link | What it is |
|---|---|---|
| R-openrouter | https://openrouter.ai/docs/quickstart | Quickstart: the OpenAI-compatible API |
| R-openrouter-cc | https://openrouter.ai/docs/cookbook/coding-agents/claude-code-integration | Claude Code through OpenRouter (`ANTHROPIC_BASE_URL`): the Anthropic-compatible route |
| R-openrouter-tools | https://openrouter.ai/docs/guides/features/tool-calling | Tool calling through OpenRouter |

### Testing, packaging, data, and numerics

| Tag | Link | What it is |
|---|---|---|
| R-hypothesis | https://hypothesis.readthedocs.io/ | Hypothesis: property-based testing |
| R-snapshot | https://syrupy-project.github.io/syrupy/ and https://pytest-regressions.readthedocs.io/ | syrupy and pytest-regressions: snapshot and golden-file testing for pytest |
| R-pytest-markers | https://docs.pytest.org/en/stable/example/simple.html | pytest examples; see "Control skipping of tests according to command line option" (the `--runslow` pattern) |
| R-specifiers | https://packaging.python.org/en/latest/specifications/version-specifiers/ | Version specifiers (`>=`, `~=`, `==`) |
| R-uv | https://docs.astral.sh/uv/concepts/projects/sync/ | uv: locking (`uv lock`, `uv.lock`) and syncing |
| R-uv-res | https://docs.astral.sh/uv/concepts/resolution/ | uv: resolution, including testing your lower bounds with `--resolution lowest` |
| R-sqlite-alter | https://www.sqlite.org/lang_altertable.html | SQLite `ALTER TABLE` |
| R-sqlite-json | https://sqlite.org/json1.html | SQLite JSON functions (`json_extract`, …) |
| R-qmc | https://docs.scipy.org/doc/scipy/reference/stats.qmc.html | `scipy.stats.qmc`: Sobol, Halton, Latin hypercube, discrepancy |
| R-salib | https://salib.readthedocs.io/ | SALib: Sobol, Morris, FAST (useful as an independent oracle in tests) |

### Decision records

| Tag | Link | What it is |
|---|---|---|
| R-adr | https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions | Michael Nygard, "Documenting Architecture Decisions" (2011): the original ADR post |
| R-adr-site | https://adr.github.io/ | The ADR community site, with templates (Nygard's, MADR) and tools |
