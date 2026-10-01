# Architecture: packages, layers, and modules

**Status:** accepted (TODO step 9; 0056). **Updated:** 2026-10-01 (0057: the trust rules placed). **Depends on:** P1–P7;
`scope.md`; `use_cases.md` (U1–U9); `model_interface.md` (M1–M21); `designs.md` (G1–G17);
`diagnostics/shared.md` (S1–S10) and the six diagnostic specs; `uncertainty.md` (V1–V7); `contracts.md`
(C1–C56); `data_model.md` (Q1–Q12, W1–W6, I1–I12; Q13–Q15 added by 0056); `export.md` (E1–E7); records 0005, 0008, 0010, 0015–0022,
0024–0030, 0032–0036, 0040, 0041, 0046, 0047, 0049, 0050, 0053–0055, 0057; `trust.md` (T1–T10). Rewritten from the specs' "Architecture
(step 9)" asks and the consistency review's "Step 9 inputs"; the draft of 2026-09-28 (`api_spec_draft.md`) is
replaced.

> Every package and module in v2.0, what each is for, its layer, and its public names, with signatures, so
> each module's code and contract tests can be written against it. Signatures are Python stubs (`...` for the
> body); every public class is a frozen dataclass unless marked otherwise, and nothing public returns a bare
> `dict`. A mapping field is made read-only (`MappingProxyType`) in `__post_init__`, and a default mapping is
> `field(default_factory=dict)`. A class holding numpy arrays is `eq=False` (a dataclass's own equality can't
> compare arrays); the results compare by their JSON (§3), and contract tests compare designs and batches with
> `np.array_equal`, field by field (C14, C20). Every type with a `text` field prints as that text. Array shapes are in
> comments: `(n, d)` is n points in d model parameters.
>
> **Words.** The *workspace layer* (`ema.workspace`, layer 4) is the front door that users, the CLI, and the
> MCP server call. "API" has its ordinary meaning: the public names of any module.

---

## 1. Layers and rules

| Layer | Packages | What it holds | I/O |
|---|---|---|---|
| 0: types | `ema.types` | the domain's data classes and errors; the one canonical-JSON encoder, the hashes and ids (`identity.py`); number formatting | none |
| 1: pure | `ema.numerics` \| `ema.designs` | the basis, the Gram spectrum, fits, interval methods, the tolerance function \| samplers and design generators | none |
| 2: adapters | `ema.models` \| `ema.store` | running a model (three phases, the sandbox, output parsers) \| the database, the workspace's files, the run lock | processes, files |
| 3a: output | `ema.plotting` \| `ema.report` | figures with their data cards \| the Markdown report, and a PDF through pandoc | files |
| 3b: services | `ema.runner` \| `ema.approval` \| `ema.diagnostics` | new runs, one call at a time, under an approval \| asking for and recording approvals and confirmations \| the six diagnostics and the shared precheck | through layers 2 and 3a |
| 4: workspace | `ema.workspace` | the front door; the one place that orchestrates | through layers 2–3 |
| 5: interfaces | `ema.cli` \| `ema.mcp` | parse the input, call one workspace function, show EMA's text | terminal, stdio |

`|` separates siblings, which never import each other. `ema.reference_models` (§11) is data beside the
layers: no module in `ema` imports it (a forbidden contract, §10). Layer 3 is split in two so that the diagnostics can draw
figures; the numbers 0–5 stay as the other specs cite them ("layers 0–1", "layer 4").

```text
ema.cli   ema.mcp                                   5  interfaces
      \     /
   ema.workspace                                    4  workspace
   /     |        \
ema.runner  ema.approval  ema.diagnostics           3b services
   |          |           /      |      \
   |          |    ema.plotting  ema.report         3a output
   |          |        |            |
ema.models   ema.store |            |               2  adapters
   |  \______/  |      |            |
ema.numerics   ema.designs                          1  pure
        \        /
        ema.types                                   0  types
```

### Rules

| Id | Rule | Why | Enforced by |
|---|---|---|---|
| AR1 | **One-way imports.** A module imports only from layers below its own, and from its own package; siblings (`\|`) never import each other. | The notebook, the CLI, and the MCP server behave the same, and a lower layer can be tested without the upper ones. | import-linter's layers contract (§10) |
| AR2 | **No I/O in layers 0–1:** no files, processes, database, clock, or randomness without a seed argument. | Layers 0–1 are checked with known-answer tests and no fixtures; P4. | a forbidden contract on `os`, `pathlib`, `subprocess`, `sqlite3`, `shutil`, `tempfile`, `time`, `socket`, the standard library's `random`, and `matplotlib` (or an AST test, §10); Ruff's NPY002 |
| AR3 | **The interfaces hold no logic.** `ema.cli` and `ema.mcp` import only `ema.workspace` and `ema.types`; every number they show is text EMA rendered (C54, C55; P1). | A computation in an interface would differ between the notebook, the CLI, and the agent. | a forbidden contract |
| AR4 | **Only `ema.runner` runs a model:** it is the only importer of the execute phase, `ema.models.execute` (P3). | One place checks the approval before every run. | a forbidden contract |
| AR5 | **Only `ema.store` opens the database,** and only the main process writes it (0015). | The store's invariants (I1–I12) hold in one module. | a forbidden contract on `sqlite3` |
| AR6 | **No LLM SDK anywhere** (P1). | No number EMA produces can come from an LLM. | a forbidden contract on `anthropic`, `openai`, `google` (its SDKs), `langchain`, `langchain_core`, `litellm`, `mistralai`, `cohere`, `ollama` |
| AR7 | **`ema/__init__.py` only re-exports;** no module in `ema` imports the root package. | No import cycles through the root; `import ema.types` doesn't load matplotlib or the sandbox. | an AST test (§10); the root's re-exports are lazy (PEP 562 `__getattr__`) |

These are architecture rules, not principles (record 0056): P1–P7 protect what a user sees, and these protect
the code; the held candidate "One-way layers" in `principles.md` is answered here.

- **§12 of the old draft, settled here:**
  - *Where `version_hash` lives:* the hash is a pure function in `ema.types.identity`, beside the point hash,
    the run id, and the reuse key (one place, `data_model.md` §3.4); reading and hashing the files is
    `ema.models`'s. Layer 1 needs no exception to AR2.
  - *Whether `report` imports `diagnostics`:* no. The report renders a stored diagnostic result and its model
    spec, and nothing else, so a report rebuilt from the store is byte-identical (P1's test, S10).

---

## 2. Directory layout

```text
src/ema/
  __init__.py                 lazy re-exports: open_workspace, Workspace, ask, the result types, the errors (AR7)
  types/                      layer 0
    identity.py               TrackedFile; canonical JSON, point hash, version hash, ids, the reuse key, alpha
                              as a Fraction
    text.py                   fmt (S3), durations
    streams.py                spawned streams (SeedSequence with a spawn key), for designs and diagnostics
    model.py                  ModelParameter, Limits, PredictionSpec, parsers' settings, PythonFunction,
                              CommandLine, InputDeck, FileEntry, Keep, ModelSpec
    space.py                  Scale, Range, ModelParameterSpace
    design.py                 DesignIdentity, Line, Design
    runs.py                   RunStatus, FailureKind, Run, RunKey, Resolution, RunColumns, RunBatch,
                              Price
    results.py                Estimate, IntervalInfo, EstimateTable, Observation, ObservationTable, Note,
                              Figure, Counts, MeasuredNoisy, Provenance, DiagnosticResult, ResultSummary,
                              Reproduction
    requests.py               Request, TestRunRequest, ApprovalRequest, ConfirmationRequest, Approver,
                              Progress
    summaries.py              ModelSummary, ModelDescription, Proposal, Report, LoadingSummary,
                              DiagnosticSummary, DiagnosticParameterInfo, RunInfo
    errors.py                 EMAError and its subclasses
  numerics/                   layer 1
    basis.py                  Basis, the basis registry, total_degree (Legendre; ported from v1)
    gram.py                   the Gram spectrum, degrees above the floor, the rate
    fitting.py                least squares, the rank rule, R², the relative residual, PRESS
    sobol.py                  Sobol indices and √E_k from orthonormal coefficients
    stats.py                  rank correlation, binned index
    intervals.py              IntervalMethod, Estimator, the registry, bootstrap
    tolerance.py              P6's one tolerance function
  designs/                    layer 1
    samplers.py               Sampler, the registry, random
    generators.py             DesignGenerator, the registry, MAX_DESIGN_POINTS
    point.py  uniform.py  convergent.py  lines.py      the generators
  models/                     layer 2
    spec.py                   LoadedModel, load_spec, stored_model, save_spec, resolve_program
    files.py                  hash_files, same_file, is_within, check_files
    prepare.py  execute.py  collect.py                  the three phases of a call (0015)
    parsers.py                OutputParser, the registry, regex, json, csv (0027)
    processes.py              ModelProcesses: the model versions' children, owned by the workspace
    sandbox.py  _worker.py    the isolated child (ported from v1 after re-review, 0026); BASE_ENV,
                              model_environment (trust.md)
  store/                      layer 2 (data_model.md §10)
    schema.sql  records.py  store.py  migrations.py
    layout.py                 Layout: the workspace's paths
    lock.py                   the run lock
  plotting/                   layer 3a
    figures.py                new_figure, save (PNG and data card), axis_label, strip
  report/                     layer 3a
    render.py                 render (S1–S4), EXPLAIN_INTERVALS
    pdf.py                    to_pdf, through pandoc (0018)
  runner.py                   layer 3b: resolve, price, run_new, read_batch
  approval.py                 layer 3b: ask_approval, ask_confirmation, ask
  diagnostics/                layer 3b
    base.py                   Diagnostic, DiagnosticParameter, Transform, AnalysisContext, Computation,
                              the registry, evaluate (the precheck)
    point_run.py  scatter.py  coordinate_lines.py  lines.py  linear_model.py  polynomial_model.py
    _lines.py                 the per-line computation coordinate lines and lines share
  workspace/                  layer 4
    __init__.py               open_workspace, Workspace, ResultRef
    _evaluate.py              the order of one diagnostic evaluation (§7)
    _export.py                export (E1–E7)
    _reproduce.py             reproduce (U8)
  cli.py                      layer 5
  mcp/                        layer 5
    server.py                 the tools and resources; ELICITATION_TIMEOUT_S
    tools.md                  the tool descriptions and the server's instructions, one reviewed file (0019)
  reference_models/           not counted in the 8,000 lines (scope); §11
tests/
  contracts/                  one module of check_* functions per interface (§9)
  unit/  integration/  slow/
```

## 3. Layer 0: `ema.types`

The vocabulary of the whole application: data, and pure functions of it. It imports only the standard
library's pure modules (`dataclasses`, `enum`, `json`, `hashlib`, `struct`, `fractions`, `math`, `types`,
`typing`, `unicodedata` for the spec's hidden-character check (0057), `datetime` for the type of stored
timestamps, never for the clock) and numpy.

### `types/identity.py`

Every rule of `data_model.md` §3.4, in one place.

```python
def canonical_json(x: object) -> str: ...              # sort_keys, compact, ensure_ascii=False, allow_nan=False
def sha256_hex(data: bytes | str) -> str: ...
def point_hash(point: Sequence[float]) -> str: ...      # little-endian float64 bytes, 8·d
def version_hash(spec: ModelSpec, files: Sequence[TrackedFile]) -> str: ...
    # the canonical spec without location and settings, and each file as (relative path, sha256, shared);
    # the digests are given: reading the files is ema.models's
def run_id(model_version_id: str, point_hash: str, replicate: int, attempt: int) -> str: ...
def batch_call_id(run_ids: np.ndarray | Sequence[str]) -> str: ...
    # ids as 32-byte arrays or hex strings hash the same: each is taken as its hex form
def approval_id(model_version_id: str, asked_for: str, request: Request | TestRunRequest, new: int,
                reused: int, n_before: int) -> str: ...
def reuse_key(model_version_id: str, request: Request, run_ids: np.ndarray | Sequence[str],
              versions: Mapping[str, str]) -> str: ...  # the result id is its hash (C50, 0054); ids as
                                                        # batch_call_id takes them
def decimal_fraction(x: float | str) -> Fraction: ...   # alpha: Fraction(repr(x)), or the JSON text (0047)
def model_version_label(name: str, model_version_id: str) -> str: ...   # "name@" and 12 hex digits

@dataclass(frozen=True)
class TrackedFile:
    path: str                         # relative, with "/"
    sha256: str
    shared: bool
```

### `types/streams.py`

```python
def spawned(seed: int, *key: int) -> np.random.Generator: ...
    # Generator(PCG64(SeedSequence(seed, spawn_key=key))): random lines' streams (key j, designs.md) and a
    # diagnostic's own draws (key tag ≥ 2³², shared.md, made in ema.diagnostics and handed to the interval
    # method as its stream); here, in layer 0, so ema.designs and ema.diagnostics share it
```

### `types/text.py`

```python
def fmt(x: float) -> str: ...          # format(x, ".4g") with an ASCII minus (S3, 0044)
def duration(seconds: float) -> str: ...   # "about 3 h 12 min"; the price's wording (U2)
```

### `types/model.py`

`model_interface.md`'s spec, one dataclass per part. `ModelSpec.from_json` validates everything that needs
no file: names (lowercase model names; identifiers, unique across model parameters and model predictions;
no `ema_` prefix, M21), `noisy: true` refused (M18), nominal values inside limits, required fields, and
**unknown keys refused, naming the key**. Checks that need files (templates' names, M10; unlisted imports,
M17) are `ema.models.load_spec`'s.

```python
@dataclass(frozen=True)
class Limits:
    lower: float | None = None
    lower_strict: bool = False          # "gt" when True, "ge" when False
    upper: float | None = None
    upper_strict: bool = False
    def contains(self, x: float) -> bool: ...

@dataclass(frozen=True)
class ModelParameter:
    name: str
    units: str                          # "" when dimensionless
    description: str
    nominal: float
    limits: Limits = Limits()

@dataclass(frozen=True)
class RegexParser:
    file: str                           # relative to the run directory, or "stdout" or "stderr"
    pattern: str                        # one group, or a group named "value"
    match: Literal["first", "last"] = "last"
@dataclass(frozen=True)
class JsonParser:
    file: str
    key: str                            # dotted; integer parts index lists
@dataclass(frozen=True)
class CsvParser:
    file: str
    column: str | int
    row: int = -1
    delimiter: str = ","
ParserSpec = RegexParser | JsonParser | CsvParser

@dataclass(frozen=True)
class PredictionSpec:
    name: str
    units: str
    description: str
    parser: ParserSpec | None = None    # required for a command-line model, refused for a Python function

@dataclass(frozen=True)
class FileEntry:
    path: str
    shared: bool = False

@dataclass(frozen=True)
class PythonFunction:
    function: str                       # "file.py:f"
    batch: bool = False

@dataclass(frozen=True)
class InputDeck:
    template: str
    writes: str                         # relative, no ".."

@dataclass(frozen=True)
class CommandLine:
    command: tuple[str, ...]
    input_decks: tuple[InputDeck, ...] = ()

class Keep(Enum):
    ALL = "all"; INCOMPLETE = "incomplete"; NONE = "none"

@dataclass(frozen=True)
class ModelSpec:
    name: str
    description: str
    interface: PythonFunction | CommandLine
    parameters: tuple[ModelParameter, ...]
    predictions: tuple[PredictionSpec, ...]
    files: tuple[FileEntry, ...] = ()
    env: Mapping[str, str] = field(default_factory=dict)    # both kinds of model (trust.md, 0057)
    pass_env: tuple[str, ...] = ()      # names passed from EMA's environment; values not in the model version
    noisy: bool = False                 # only False in v2.0 (0021)
    keep: Keep = Keep.ALL               # settings: not in the model version (0029)
    batch_size: int | None = None
    timeout_s: float = 3600.0

    @classmethod
    def from_json(cls, text: str) -> "ModelSpec": ...   # raises SpecError naming the field; also checks
        # trust.md's T7 (path shapes on "/"-separated parts, credentials-file names, EMA's own file names,
        # one-line strings with no hidden character, duplicate keys) and T8 (variable names), and an env
        # PATH's empty or relative entries (T2)
    def to_json(self) -> str: ...                       # every field, defaults filled in, paths with "/"
    def versioned_json(self) -> str: ...                # without keep, batch_size, timeout_s (§3.4)
    def parameter(self, name: str) -> ModelParameter: ...
    def prediction(self, name: str | None) -> PredictionSpec: ...   # None: the only one, or refused
```

**The model spec's fields** (the review's ask; the JSON keys are the field names):

| Field | Type | Required | Default | In the model version |
|---|---|---|---|---|
| `name` | model name | yes | | yes |
| `description` | text | yes | | yes |
| `interface` | `"python_function"` or `"command_line"` | yes | | yes |
| `function` | `"file.py:f"` | Python function: yes; else refused | | yes; the file is tracked |
| `batch` | bool | no (Python function only) | false | yes |
| `command` | list of strings | command line: yes; else refused | | yes |
| `input_decks` | list of `{template, writes}` | no (command line only) | `[]` | yes; the templates are tracked |
| `env` | mapping of strings | no (both kinds, 0057) | `{}` | yes |
| `pass_env` | list of variable names | no (both kinds, 0057) | `[]` | the names; not their values |
| `files` | list of a path or `{path, shared}` | no | `[]` | yes; each file is tracked |
| `parameters` | list, at least one | yes | | yes |
| a parameter's `name`, `units`, `nominal`, `description` | | yes (`units` may be `""`) | | yes |
| a parameter's `limits` | `{gt or ge, lt or le}` | no | none | yes |
| `predictions` | list, at least one | yes | | yes |
| a prediction's `name`, `units`, `description` | | yes | | yes |
| a prediction's `parser` | `{kind, …}` (0027) | command line: yes; Python function: refused | `match` last; `row` −1; `delimiter` `,` | yes |
| `noisy` | bool | no | false; `true` refused (M18) | yes |
| `keep` | `all`, `incomplete`, `none` | no | `all` | no (0029) |
| `batch_size` | integer ≥ 1 | no (batch only) | all of a design's new runs | no (0029) |
| `timeout_s` | number > 0 | no | 3600 | no (0029) |
| any other key | | refused, naming it | | |

### `types/space.py`

The model parameter space (`designs.md`): a hyperrectangle of ranges, and held values. Generators reach it
only through its membership test, its unit maps, and line clipping, so a later shape (the hyperellipsoid,
0005) is one new class with the same methods.

```python
class Scale(Enum):
    LINEAR = "linear"; LOG = "log"

@dataclass(frozen=True)
class Range:
    lo: float
    hi: float
    scale: Scale = Scale.LINEAR

@dataclass(frozen=True)
class ModelParameterSpace:
    ranges: Mapping[str, Range]               # varied model parameters
    held: Mapping[str, float]                 # held values the space gives

    @classmethod
    def parse(cls, form: Mapping[str, Any]) -> "ModelParameterSpace": ...
        # designs.md's JSON form; a 2-tuple is accepted where JSON has a 2-list
    @classmethod
    def at_point(cls, spec: ModelSpec, x: Mapping[str, float]) -> "ModelParameterSpace": ...   # the point design's (0049)
    def validate(self, spec: ModelSpec) -> None: ...   # G15, M6: names, lo < hi, log lo > 0, limits; RequestError
    def varied(self, spec: ModelSpec) -> tuple[str, ...]: ...   # in the spec's order (G16)
    def complete(self, spec: ModelSpec, Xv: np.ndarray) -> np.ndarray: ...   # (n, d_varied) → (n, d_all), held filled
    def to_unit(self, spec: ModelSpec, X: np.ndarray) -> np.ndarray: ...     # z in [-1, 1] (0047)
    def from_unit(self, spec: ModelSpec, Z: np.ndarray) -> np.ndarray: ...   # clamped; faces exact
    def from_cube(self, spec: ModelSpec, U: np.ndarray) -> np.ndarray: ...   # the sampler's [0, 1)^d rows → points
                                                       # (designs.md: sampling the unit cube)
    def contains(self, spec: ModelSpec, X: np.ndarray) -> np.ndarray: ...
    def clip_line(self, spec: ModelSpec, anchor_z: np.ndarray,
                  direction_z: np.ndarray) -> tuple[float, float]: ...       # the segment's t range
    def canonical(self) -> Mapping[str, Any]: ...      # every range as {"range": [lo, hi], "scale": …}
```

### `types/design.py`

```python
@dataclass(frozen=True)
class DesignIdentity:
    """A design's identity (0046, data_model.md §3.4): stored with each result and approval, so a design can
    be rebuilt without today's code deciding it."""
    model_version_id: str
    kind: str                                 # "point", "uniform", "convergent", "lines",
                                              # "coordinate_lines", "random_lines"
    space: Mapping[str, Any]                  # canonical form
    params: Mapping[str, Any]                 # the generator's parameters; alpha as its decimal string
    seed: int
    sampler: str | None                       # with its version, for uniform and convergent
    sampler_version: str | None
    generator_version: str
    def canonical(self) -> Mapping[str, Any]: ...

@dataclass(frozen=True)
class Line:
    anchor: tuple[float, ...]                 # model parameter units
    direction: tuple[float, ...]              # unit coordinates
    ends: tuple[tuple[float, ...], tuple[float, ...]]
    rows: tuple[int, int]                     # its rows [start, stop) in the design

@dataclass(frozen=True, eq=False)
class Design:
    identity: DesignIdentity | None           # None only for the test run (data_model.md §5.4)
    points: np.ndarray                        # (n, d), every model parameter, in the spec's order
    replicates: np.ndarray                    # (n,)
    levels: tuple[int, ...] | None            # convergent: n_0 … n_L
    lines: tuple[Line, ...] | None            # lines: anchor, direction, ends, and rows, each
    def __len__(self) -> int: ...
```

### `types/runs.py`

```python
class RunStatus(Enum):
    OK = "ok"; FAILED = "failed"

class FailureKind(Enum):
    ERROR = "error"; TIMEOUT = "timeout"; UNREAD = "unread"

@dataclass(frozen=True)
class Run:
    """One stored run (data_model.md §5.6, §5.8)."""
    run_id: str
    model_version_id: str
    point: tuple[float, ...]                  # every model parameter, in the spec's order
    replicate: int
    attempt: int
    status: RunStatus
    kind: FailureKind | None
    reason: str | None
    stderr_tail: str | None
    exit_code: int | None
    predictions: Mapping[str, float | None]   # every model prediction of an ok run; None where missing
    missing: Mapping[str, str]                # each missing model prediction's reason
    time_s: float
    batch_call_id: str | None
    host: str
    program: str
    approval_id: str

@dataclass(frozen=True)
class RunKey:
    """A new run to make: its key (data_model.md §3.4) and its id."""
    point: tuple[float, ...]
    point_hash: str
    replicate: int
    attempt: int
    run_id: str

@dataclass(frozen=True, eq=False)
class Resolution:
    """A design resolved against the store (Q1): what pricing, approval, and running share."""
    design: Design
    model_version_id: str
    row_runs: np.ndarray                      # (n,) each design row's stored run id (32 bytes), or zeros when new
    row_keys: np.ndarray                      # (n,) each new row's index into new_keys, or -1 when stored
    new_keys: tuple[RunKey, ...]              # distinct (point, replicate) keys to run, attempts set (C47);
                                              # each RunKey.run_id is known before the run (§3.4)
    reused_failed: int

@dataclass(frozen=True, eq=False)
class RunColumns:
    """Stored runs, one row each, in the order asked for (Q7, Q15): columns, so 10⁷ rows (the design cap) cost
    tens of bytes each, not a Run object each."""
    run_ids: np.ndarray                       # (n,) 32-byte ids
    points: np.ndarray | None                 # (n, d): Q7 fills it (export, failed_runs); a run batch uses
                                              # its design's points, and Q15 leaves it None
    replicates: np.ndarray                    # (n,)
    status: np.ndarray                        # (n,) RunStatus codes
    kind: np.ndarray                          # (n,) FailureKind codes; -1 when ok
    values: Mapping[str, np.ndarray]          # model prediction → (n,); NaN where missing or failed
    reasons: Mapping[str, str]                # failed run id (hex) → its one-line reason
    missing: Mapping[str, Mapping[str, str]]  # model prediction → ok run id (hex) → why it is missing
                                              # ("plate.out: pattern not found"), so y's note never shows z's
    time_s: np.ndarray                        # (n,)
    host: np.ndarray                          # (n,) str
    program: np.ndarray                       # (n,) str
    batch_call_ids: np.ndarray                # (n,) 32-byte ids, or zeros
    approval_ids: np.ndarray                  # (n,) 32-byte ids

@dataclass(frozen=True, eq=False)
class RunBatch:
    """The runs a diagnostic receives, one row per design row, in design order (C56)."""
    design: Design
    runs: RunColumns
    new: np.ndarray                           # (n,) bool: made by this diagnostic evaluation (E6)
    def usable(self, prediction: str) -> np.ndarray: ...   # (n,) bool: ok and read (0022)
    def run_id(self, row: int) -> str: ...

@dataclass(frozen=True)
class Price:
    new: int
    reused: int
    reused_failed: int
    time_s: float | None                      # None: "unknown" (P3)
    from_runs: int                            # the stored runs the time is from (Q2)
    text: str                                 # "96 new runs, 1 reused, about 3 h 12 min (from 1 stored run)"
```

### `types/results.py`

```python
@dataclass(frozen=True)
class Estimate:
    key: str                                  # stable, not shown: "mean", "std", "slope", "S_T" (C5)
    label: str                                # the row's name: "E", "mean", "S_T,a"
    value: float
    interval: tuple[float, float] | None      # None: "none", with the reason (0041)
    reason: str | None

@dataclass(frozen=True)
class IntervalInfo:
    method: str                               # "bootstrap", or a fake's name (C19)
    settings: Mapping[str, Any]               # resamples, percentiles, seed, distinct runs …
    n_usable: int
    undefined: Mapping[str, int]              # undefined resamples per estimate, when any (V4)

@dataclass(frozen=True)
class EstimateTable:
    key: str                                  # stable, not shown: "rank_correlation", "sobol_total" (C5)
    title: str
    columns: tuple[str, ...]
    estimates: tuple[Estimate, ...]
    units: str                                # "" when dimensionless
    interval: IntervalInfo                    # the line under the table (S4)

@dataclass(frozen=True)
class Observation:
    key: str                                  # stable, not shown: "min", "max", "spread", "rate", "kind" (C5)
    label: str
    value: float | int | str                  # a number, or a run's kind for the point run's rows
    units: str

@dataclass(frozen=True)
class ObservationTable:
    key: str                                  # stable, not shown: "shared", "line_rates"
    title: str                                # says what it is of: "Of the 200 usable runs" (0034)
    columns: tuple[str, ...]
    rows: tuple[tuple[Observation, ...], ...]

@dataclass(frozen=True)
class Note:
    code: str                                 # "not_usable", "reused_failed", "too_few", "all_failed",
                                              # "no_usable", "constant", "measured_noisy", or a diagnostic's own
    text: str                                 # rendered by EMA, numbers by fmt

@dataclass(frozen=True)
class Figure:
    name: str
    png: str                                  # file names in the result's directory
    card: str
    caption: str

@dataclass(frozen=True)
class Counts:
    rows: int
    runs: int                                 # distinct runs
    new: int
    reused: int
    failed: Mapping[FailureKind, int]
    missing: int                              # ok, but missing this model prediction
    usable: int

@dataclass(frozen=True)
class MeasuredNoisy:
    """One point run that measured a model version noisy in one model prediction (data_model.md §5.11)."""
    result_id: str
    model_version_id: str
    prediction: str
    point: tuple[float, ...]
    runs: int
    std: float | None
    made_at: datetime | None                  # set by W5, read by Q10; copied whole into a provenance (§5.12)

@dataclass(frozen=True, eq=False)
class Provenance:
    """P5, data_model.md §5.9; enough to replay after the result is deleted (0055). Equal when its canonical
    JSON is (it holds an array, which a dataclass's own equality can't compare)."""
    ema: str
    numpy: str
    scipy: str
    matplotlib: str
    model_version_id: str
    request: Request
    design: DesignIdentity
    run_ids: np.ndarray                       # (n,) one per design row, in design order (32 bytes each);
                                              # hex strings in JSON
    approval_id: str | None                   # its own new runs' approval (0054)
    spawn_tags: tuple[int, ...]
    measured_noisy_read: tuple[MeasuredNoisy, ...]

@dataclass(frozen=True, eq=False)
class DiagnosticResult:
    """Numbers only (P2). Refuses to be built with no estimate, observation, or note (0036). Equal when its
    to_json is (C17's "loads back equal"; I11)."""
    result_id: str
    diagnostic: str
    title: str                                # the diagnostic's title, for the report's (S1)
    model_version_id: str
    prediction: str
    counts: Counts
    header_rows: tuple[tuple[str, str], ...]  # the diagnostic's own rows (S1): the polynomial model's Fit
    notes: tuple[Note, ...]
    estimates: tuple[EstimateTable, ...]
    observations: tuple[ObservationTable, ...]
    figures: tuple[Figure, ...]
    extra: tuple[EstimateTable, ...]          # estimates kept in the result and its data cards, not the
                                              # report: the polynomial model's coefficients, each labeled
                                              # by its multi-index, with its interval (0041)
    measured_noisy: MeasuredNoisy | None      # the point run's record, when it measured variation
                                              # (point_run.md); W5 writes it to measured_noisy (C52)
    provenance: Provenance                    # required, no default (P5)
    shown: ResultSummary | None = field(default=None, compare=False)
        # set by the workspace when it returns a result: its short id and EMA's text; not stored, not
        # compared, and left out of to_json; the result prints as shown.text
    def to_json(self) -> str: ...             # strict JSON; "none" as null with its reason (C17)
    @classmethod
    def from_json(cls, text: str) -> "DiagnosticResult": ...

@dataclass(frozen=True)
class ResultSummary:
    result_id: str
    short_id: str                             # the shortest unique prefix (Q11)
    model_version: str                        # "beam@91c0…" label
    diagnostic: str
    prediction: str
    runs: int
    failed: int
    made_at: datetime
    text: str

@dataclass(frozen=True)
class Reproduction:
    result_id: str
    result: DiagnosticResult                  # the replayed result
    identical: bool | None                    # None: no original to compare (a provenance alone, its result
                                              # deleted and not given)
    differences: tuple[str, ...]              # "2 estimates", "data card scatter_E", "report"
    provenance_differences: tuple[str, ...]   # "numpy: 2.3.1 here, 2.4.0 there"
    text: str                                 # U8's message
```

### `types/requests.py`

```python
@dataclass(frozen=True)
class Request:
    """What one diagnostic evaluation is asked for (glossary); canonical, defaults filled in (§3.4)."""
    diagnostic: str
    prediction: str
    space: Mapping[str, Any] | None           # canonical; None for the point run (U7)
    params: Mapping[str, Any]                 # every diagnostic parameter, the seed included
    def canonical(self) -> Mapping[str, Any]: ...

@dataclass(frozen=True)
class TestRunRequest:
    """The test run's request: {"test_run": {"point": […]}} (data_model.md §3.4)."""
    point: tuple[float, ...]                  # the nominal point
    def canonical(self) -> Mapping[str, Any]: ...

@dataclass(frozen=True)
class ApprovalRequest:
    asked_for: Literal["diagnostic_evaluation", "test_run"]
    model_version: str                        # label
    price: Price
    first_for_version: bool                   # then the details below are shown (U2)
    command: tuple[str, ...] | None
    program: str | None                       # the resolved program path (0029)
    templates: Mapping[str, str]              # name → text
    files: tuple[str, ...]
    function: str | None                      # a Python function's "file.py:f", shown in place of the command
    env: Mapping[str, str]                    # the spec's env (trust.md)
    pass_env: Mapping[str, bool]              # each name: set in EMA's environment or not; never its value
    text: str                                 # the whole question, rendered by EMA (trust.md: hidden characters
                                              # as codes; strings EMA didn't write in code spans or fenced blocks)

@dataclass(frozen=True)
class ConfirmationRequest:
    spec_path: str                            # absolute, the parent resolved through its links (T6)
    replaces: str | None                      # what the model's name means now, when it is loaded (0054)
    spec_text: str
    text: str

Approver = Callable[[ApprovalRequest | ConfirmationRequest], bool]
    # an Exception raised by it counts as no; KeyboardInterrupt passes through

@dataclass(frozen=True)
class Progress:
    phase: Literal["runs", "analysis"]
    done: int
    total: int
    text: str                                 # "40/96 runs"; "bootstrap: 230 of 1000 refits, about 6 min left";
                                              # "A: 14161 × 1771, 200 MB" (PM10)
```

### `types/summaries.py`

```python
@dataclass(frozen=True)
class ModelSummary:
    name: str
    model_version: str                        # label
    parameters: tuple[str, ...]
    predictions: tuple[str, ...]
    spec_path: str
    text: str

@dataclass(frozen=True)
class ModelDescription:
    model: ModelSummary
    spec: ModelSpec
    text: str                                 # the model parameters, units, nominal values, limits, predictions

@dataclass(frozen=True)
class Proposal:
    """A model spec an MCP client drafted, validated and rendered; nothing saved (U9)."""
    spec: ModelSpec
    path: str                                 # the absolute path save_model's confirmation would show (T6)
    spec_text: str                            # the file's exact text
    missing_files: tuple[str, ...]            # files it names that don't exist yet
    text: str

@dataclass(frozen=True)
class Report:
    """Prints as its Markdown."""
    result_id: str
    markdown: str
    path: str                                 # <workspace>/results/<result id>/report.md
    pdf: str | None

@dataclass(frozen=True)
class LoadingSummary:
    model: ModelSummary
    new_version: bool
    replaced: str | None                      # "was heat@b204… at /old/dir"
    changed_files: tuple[str, ...]            # "solver.cfg changed" (U6)
    warnings: tuple[str, ...]                 # unlisted imports (M17)
    text: str

@dataclass(frozen=True)
class DiagnosticParameterInfo:
    name: str
    type: str                                 # "integer ≥ 1", "decimal in (0, 1)", "model parameter space", …
    default: Any | None
    default_text: str                         # "2(d + 1)", "the only one"
    meaning: str
    changes_design: str                       # "yes", "no", or the spec's wording
    json_schema: Mapping[str, Any]            # for the MCP server (C55)

@dataclass(frozen=True)
class DiagnosticSummary:
    name: str
    summary: str
    takes_space: bool
    parameters: tuple[DiagnosticParameterInfo, ...]
    text: str

@dataclass(frozen=True)
class RunInfo:
    run_id: str
    short_id: str
    row: int | None
    point: Mapping[str, float]
    replicate: int
    status: RunStatus
    kind: FailureKind | None
    reason: str | None
    predictions: Mapping[str, float | None]   # an ok run's model predictions; None where missing
    run_dir: str | None                       # None when not kept (0020)
    batch_dir: str | None                     # a batch call's directory, when kept (0025)
    text: str
```

Every type with a `text` field prints as that text (`__str__`), so `print(ws.report(r))` and `print(check)`
show what EMA rendered, and the interfaces format no number themselves (AR3).

### `types/errors.py`

Each error carries `retryable` as a class attribute, so the interfaces can say whether trying again can help.

| Error | Raised when | Retryable |
|---|---|---|
| `EMAError` | the base of every error EMA raises on purpose | |
| `SpecError` | a model spec doesn't validate (field named) | no |
| `RequestError` | a space, a diagnostic parameter, or a design request is refused (G14, G15, M6) | no |
| `DesignTooLarge` (a `RequestError`) | the size is over `MAX_DESIGN_POINTS` (G5) | no |
| `ApprovalDeclined` | the answer was no, or none came; nothing ran | yes |
| `CannotAsk` (an `ApprovalDeclined`) | `approve=None` or `confirm=None`: nobody can be asked (an MCP client without elicitation); nothing asked or recorded | no |
| `ModelChanged` | a tracked file changed since loading, or during an evaluation (U6, M16), naming it | no |
| `NotFound` | no such model, diagnostic, result, or run | no |
| `AmbiguousId` | a prefix names several ids, listed (Q11) | no |
| `WorkspaceBusy` | another process holds the run lock, named | yes |
| `WorkspaceVersion` | the workspace's schema is newer than this EMA (`data_model.md` §11) | no |
| `PandocMissing` | a PDF is asked for without pandoc or lualatex, or lualatex stops on a missing package or font; says what to install (0018, 0059) | no |
| `PdfFailed` | lualatex stops for any other reason (with LaTeX's error line), or a figure is missing from the PDF (0059) | no |
| `PathRefused` | an MCP path argument outside the root, inside a workspace, with a hidden character, or naming a credentials file; a drafted spec's file resolving outside the root (`trust.md`, T5, T7). A spec naming a credentials file is a `SpecError`. | no |

## 4. Layer 1: `ema.numerics` and `ema.designs`

Pure functions of arrays (AR2). Every random draw takes a seed, or a `np.random.Generator` made by
`ema.types.streams.spawned` (layer 0), which `ema.designs` and `ema.diagnostics` share.

### The four interfaces kept as seams

Each has a registry (`register`, `get`, `names`), its v2.0 implementation, and a fake registered in the tests
through the same `register`, removed by a fixture: no monkeypatching (C19, C28–C30). A name with no
implementation is refused with "<kind> X comes in a later version" (`designs.md`, `polynomial_model.md`).
There are no plugin entry points in v2.0; adding them later is about 30 lines, on these registries.

```python
# designs/samplers.py (designs.md, Samplers; C28)
class Sampler(Protocol):
    name: str
    version: str
    nested: bool
    balanced_sizes: Literal["any", "powers_of_2"]
    rate: Fraction                                      # r; 1/2 for random
    def unit_rows(self, seed: int, d: int, start: int, stop: int) -> np.ndarray: ...   # (stop - start, d) in [0, 1)

# designs/generators.py (designs.md, Generators; C20–C27)
MAX_DESIGN_POINTS = 10_000_000
class DesignGenerator(Protocol):
    name: str
    version: str
    def size(self, request: DesignIdentity, spec: ModelSpec) -> int: ...      # closed form (G3)
    def build(self, request: DesignIdentity, spec: ModelSpec,
              start: int = 0, stop: int | None = None) -> Design: ...       # refuses over the cap first (G5, G6)

# numerics/basis.py (polynomial_model.md; C29)
class Basis(Protocol):
    name: str
    def terms(self, d: int, degree: int) -> np.ndarray: ...       # (P, d) multi-indices, the constant first
    def n_terms(self, d: int, degree: int) -> int: ...            # without building them
    def evaluate(self, Z: np.ndarray, terms: np.ndarray) -> np.ndarray: ...   # (n, P), orthonormal on [-1, 1]^d

# numerics/intervals.py (uncertainty.md, the interface; C30)
@dataclass(frozen=True)
class Estimator:
    """One computation per resample, giving one or more estimates: a fit's coefficients, R², and residual
    come from one refit, not one refit per number."""
    name: str
    labels: tuple[str, ...]                             # the estimates it gives, in order
    fn: Callable[[np.ndarray], np.ndarray]              # run indices → (len(labels),) values; NaN where undefined
    distinct: bool                                      # "distinct runs" (V3)

@dataclass(frozen=True)
class Interval:
    bounds: tuple[float, float] | None
    reason: str | None
    undefined: int

class IntervalMethod(Protocol):
    name: str
    settings: Mapping[str, Any]
    def intervals(self, usable: np.ndarray, levels: np.ndarray | None,
                  estimators: Sequence[Estimator], stream: np.random.Generator,
                  on_step: Callable[[int, int], None] | None = None) -> dict[str, tuple[Interval, ...]]: ...
        # estimator name → one Interval per label; undefined resamples are dropped and counted per label (V4)
        # on_step(done, total): the analysis's progress (PM10); an exception from it stops the method
```

### `ema.numerics`

| Module | Public names | From |
|---|---|---|
| `basis.py` | `Basis`, `register`, `get`, `names`, `TotalDegree` (Legendre) | `polynomial_model.md`; v1's `core/legendre.py`, ported after re-review |
| `gram.py` | `gram_coefficients(y) -> np.ndarray` (c_k of evenly spaced samples); `tail(c) -> np.ndarray` (T(k)); `degrees_above_floor(T, floor) -> int` (k*); `decay_rate(T, k_star, min_degrees) -> tuple[float, float] \| None` (rate and intercept, or none) | `coordinate_lines.md`, `lines.md` (0038) |
| `fitting.py` | `Fit` (coefficients, residuals, rank, leverages); `least_squares(A, y) -> Fit`, `rank(A) -> int` (0051's rule), `press(A, y, fit) -> float`, `r2`, `relative_residual` | `linear_model.md`, `polynomial_model.md`; no k-fold cross-validation |
| `sobol.py` | `sobol_indices(coef, terms) -> (first, total)`, `degree_energy(coef, terms)` (√E_k) | `polynomial_model.md` |
| `stats.py` | `rank_correlation(x, y)`, `binned_index(x, y, bins)` | `scatter.md` |
| `intervals.py` | `Estimator`, `Interval`, `IntervalMethod`, `register`, `get`, `names`, `Bootstrap`; `BOOTSTRAP_RESAMPLES`, `BOOTSTRAP_PERCENTILES`, `BOOTSTRAP_MIN_DEFINED` | `uncertainty.md`; no `convergence_interval` (0040) |
| `tolerance.py` | `tolerance(values, rel) -> float`: `rel` × the range of the values (P6's one function) | P6 |

### `ema.designs`

| Module | Public names | From |
|---|---|---|
| `samplers.py` | `Sampler`, `register`, `get`, `names`, `Random` | `designs.md`, Samplers (0032) |
| `generators.py` | `DesignGenerator`, `register`, `get`, `names`, `MAX_DESIGN_POINTS` | `designs.md`, Shared rules |
| `point.py` | `Point`: `x`, `repeats` | Point (0011, 0049) |
| `uniform.py` | `Uniform`: `n`, `seed`, `sampler` | Uniform |
| `convergent.py` | `Convergent`: `n_min`, `alpha` (a `Fraction`), `level`, `seed`, `sampler`; sizes ⌈n_min·alpha^(−l/r)⌉ in exact arithmetic | Convergent (0047) |
| `lines.py` | `GivenLines`: `lines`, `n`; `CoordinateLines`: `n`, `anchor`; `RandomLines`: `m`, `n`, `seed` | Lines (0047, 0051) |

## 5. Layer 2: `ema.models` and `ema.store`

### `ema.models`

What a model is to EMA (`model_interface.md`), with a run's three phases in place of the draft's
`Model.evaluate` (0015). Only plain, serializable data (paths, the command, the keys) passes between the
phases, so a later parallel or remote executor replaces `execute` alone. `ema.models` never imports
`ema.store` (AR1); the runner gives it the workspace's paths.

```python
# models/spec.py
@dataclass(frozen=True)
class LoadedModel:
    spec: ModelSpec
    spec_path: str                       # absolute
    model_dir: str
    files: tuple[TrackedFile, ...]       # hashed at loading
    model_version_id: str                # version_hash(spec, files)
    warnings: tuple[str, ...]            # unlisted local imports (M17)

def load_spec(path: str) -> LoadedModel: ...       # reads, validates (M10, M17, M18, M21), hashes; SpecError
def stored_model(spec: ModelSpec, files: tuple[TrackedFile, ...], spec_path: str) -> LoadedModel: ...
    # plain values, since ema.models can't import ema.store (AR1): the workspace passes Q14's stored spec,
    # with the current loading's settings (Q3: keep, batch_size, timeout_s) set on it, its tracked files,
    # and the loading's spec path. Runs use the stored spec; an edited spec file takes effect only when
    # it is loaded again (0054). The tracked files are checked before each call (check_files).
def save_spec(spec: ModelSpec, path: str) -> None: ...   # for save_model; refuses to overwrite a different file;
    # writes with an exclusive create, so a file that appears meanwhile is kept (T6)
def resolve_program(model: LoadedModel) -> str | None: ...   # against the model's own PATH (model_environment)
    # the command's program, resolved as execute will (or the child's interpreter), for the first
    # approval's question before any run (U2, 0029)

# models/files.py
def hash_files(spec: ModelSpec, model_dir: str) -> tuple[TrackedFile, ...]: ...
def same_file(a: str, b: str) -> bool: ...          # samefile; case-folded where the file system is (T1, C33)
def is_within(path: str, directory: str) -> bool: ...   # the resolved path, or its nearest existing parent,
    # is the directory or below it, as files (T1, T5); a named file whose link resolves to a credentials
    # file is refused at loading (T7)
def check_files(model: LoadedModel) -> None: ...    # before every call; ModelChanged naming the file (M16, C34)

# models/processes.py
class ModelProcesses:                    # not frozen; owned by the Workspace, passed to execute
    def close(self) -> None: ...         # stops every model version's child (0026)

# models/prepare.py   (RunKey is ema.types's)
@dataclass(frozen=True)
class PreparedCall:
    keys: tuple[RunKey, ...]             # one, or a batch call's (0025)
    approval_id: str                     # recorded with each run (C48)
    run_dirs: tuple[str, ...]
    call_dir: str                        # the run directory, or the batch directory beside them
    command: tuple[str, ...] | None      # a command-line model's
    env: Mapping[str, str]               # the whole environment the model gets (model_environment, trust.md)
    timeout_s: float

def prepare(model: LoadedModel, keys: Sequence[RunKey], runs_dir: str, shared_dir: str) -> PreparedCall: ...
    # writes point.json, the input decks (M10's number rule), copied files, links to shared copies (M15)

# models/execute.py   (imported only by ema.runner: AR4)
@dataclass(frozen=True)
class ExecutedCall:
    prepared: PreparedCall
    exit_code: int | None
    timed_out: bool
    error: str | None                    # the one-line reason for a crash, where known
    time_s: float
    host: str
    program: str                         # resolved path; the child's interpreter for a Python function (0029)

def execute(model: LoadedModel, call: PreparedCall, processes: ModelProcesses) -> ExecutedCall: ...
    # a command: no shell, its own process group, stdin /dev/null (M2, M20); a Python function: its
    # isolated child, started in `processes` when it has none (M9); streams to stdout.txt and stderr.txt;
    # Ctrl-C kills the call and re-raises

# models/collect.py
def collect(model: LoadedModel, call: ExecutedCall) -> tuple[Run, ...]: ...
    # model predictions from files only: the parsers, or predictions.json (M13); status and kind (0043);
    # run.json in each run directory; never raises for a point (M1)

# models/parsers.py   (0027; C45)
class OutputParser(Protocol):
    kind: str
    def read(self, settings: ParserSpec, run_dir: str) -> tuple[float | None, str | None]: ...
        # the value, or None with the reason; never follows a link out of the run directory
def register(p: OutputParser) -> None: ...
def get(kind: str) -> OutputParser: ...
def names() -> tuple[str, ...]: ...
```

`sandbox.py` and `_worker.py` hold the isolated child: one long-lived child per model version, JSON (or
arrays in a format that runs no code) and never pickle, killed on a timeout, a crash, or Ctrl-C, and started
again for the next call (0026, M9). Ported from v1's `core/models/_sandbox.py` and `_worker.py` after
re-review; the environment it passes is `trust.md`'s. The child runs in its own process group, killed whole;
it is started by its worker's path, and replaces its `sys.path` with EMA's, made absolute, received over its
pipe; its streams never reach EMA's stdout. `run.json` and `predictions.json` are written without following a
link the model left there, and run and batch directories deleted without following links (`trust.md`, T9).
`load_spec` never imports the function's file: M17 parses it (`ast`).

### `ema.store`

Exactly `data_model.md` §10: `schema.sql`, `records.py`, `store.py` (one function per write W1–W6 and read
Q1–Q15, each citing its id), `migrations.py`; and:

- `layout.py`: the workspace's paths (`ema.db`, `run.lock`, `runs/`, `files/`, `results/`);
- `lock.py`: the run lock: `fcntl.flock(LOCK_EX | LOCK_NB)` on a descriptor of `run.lock` kept open while it is
  held, so it excludes a second holder in the same process as well as in another (a per-process POSIX lock
  would not), and is released when the descriptor closes or the process exits. Only the workspace that makes
  runs takes it; prices, reads, and reports never do.
- **Migration:** the copy of `ema.db` is taken inside the migration's `BEGIN IMMEDIATE`, after the version is
  read again (`data_model.md` §11), so a second opener never copies a half-migrated file; the MCP server opens
  its two workspaces one after the other.
- **Connections:** one `Store` per thread that uses it (a SQLite connection stays on its thread). A process
  normally has one; the MCP server has two (§8). This replaces `data_model.md` §10's "one `Store` per process"
  (record 0056); only the main process writes, as before.

Three reads are added to `data_model.md` §8 (record 0056): Q13, so the runner checks an approval before each
call, not only W4 after it (P3: "refuses a new run unless an approval matches its model version hash and
point"); Q14, so a result's report, export, and replay use its own model version's spec, not the name's
latest (U6: "the old diagnostic result's report is unchanged"); and Q15, so a replay reads the runs a
provenance names after its result is deleted (U8, C51, §9 there).

| Q | Store function | Returns | SQL sketch | Index |
|---|---|---|---|---|
| Q13 | `approval_coverage(approval_id, keys) -> Coverage` | the approval's model version and answer, and which of one call's keys it covers and has no run for yet | `approvals` by key; per key, `approval_points` by key and `runs` by its unique key with that approval | primary keys; the runs' unique key |
| Q14 | `model_version(model_version_id) -> ModelVersion` | its spec and tracked files | by key | primary key |
| Q15 | `runs_by_id(run_ids) -> RunColumns` | one row per id given, a repeated id repeated (rows share runs, E2), in the order given, with their model predictions; an unknown id is `NotFound` | per chunk of 30,000 distinct ids, as Q1, then laid out in the order given | primary keys; `predictions` by its key's prefix |

Q7 and Q15 return `RunColumns` (`ema.types`), with no object per row: Q7 for export and `failed_runs` (points,
time, host, program, batch call, approval), Q15 for every run batch, through `read_batch`. Both read in chunks
of 30,000 rows, one statement each, so a writer in another connection waits at most one chunk's read.

```python
class Store:                                          # not frozen: holds the connection
    @classmethod
    def open(cls, path: str, *, create: bool = True) -> "Store": ...
        # migrates an older schema after copying ema.db; refuses a newer one (WorkspaceVersion); waits up to
        # BUSY_TIMEOUT_S = 60 s for another connection's lock (SQLite's busy timeout), so a read in one
        # connection delays a write in another instead of failing it; W4 retries past the timeout until it
        # commits, since its call has finished and its runs must be stored (C49); reads are chunked (below),
        # so the wait is one chunk's
    layout: Layout                                    # paths: db, lock, runs/, files/, results/ (layout.py's frozen
                                                      # dataclass; data_model.md §1)
    def run_lock(self) -> ContextManager[None]: ...   # WorkspaceBusy, naming the holder
    def result_directory(self, result_id: str) -> ContextManager[str]: ...
        # a temporary directory, renamed into place before record_result commits (§6 there). If results/<id>
        # exists: with a row (Q5), the temporary directory is discarded and the stored result is the answer,
        # with no W5; with no row, it is replaced. If W5 then finds the id stored (two identical requests at
        # once), it writes nothing, and what is in place stays: its report and data cards are byte-identical
    # W1–W6 and Q1–Q15, with data_model.md's names and signatures
    def close(self) -> None: ...
```

- **Record classes:** where `ema.types` has the class, the store returns it: `Run` (its model predictions
  folded in, for §10's `Run` and `Prediction`), `DiagnosticResult` (for §10's `Result`), `MeasuredNoisy`, and
  `DesignIdentity` (§3.4's JSON shape). `records.py` holds the store's own rows: `ModelVersion`, `Loading`,
  `Confirmation`, `Approval`, `ApprovedPoint`, `BatchCall`, `RunUsed` (W5's rows; Q7 and Q9 join it), `Coverage`. One class per concept;
  the workspace's `LoadingSummary` is what a user sees of a `Loading` (record 0056 updated `data_model.md`
  §10's table).
- **W6, `delete_result`,** has no workspace name in v2.0 (record 0056): no use case deletes a result, and U8's
  test deletes through the store (`data_model.md`).

## 6. Layer 3: output and services

### `ema.plotting` (3a)

```python
def new_figure(n_panels: int) -> tuple[matplotlib.figure.Figure, Sequence[matplotlib.axes.Axes]]: ...
def axis_label(name: str, units: str) -> str: ...     # "name [units]", or "name" when dimensionless (S9)
def strip(ax, x: np.ndarray, kinds: Sequence[FailureKind], log: bool) -> None: ...
    # runs not usable: one × each, below the axes, with the count in the label (shared.md, C12)
def save(fig, card: Mapping[str, Any], out_dir: str, name: str, caption: str) -> Figure: ...
    # the PNG and its data card: canonical JSON, indented 2, a final newline (S10); every point drawn from
    # a run has its run id (S9)
```

The Agg backend and fixed rcParams, set once in the module.

### `ema.report` (3a)

```python
EXPLAIN_INTERVALS: str                       # shared.md's sentence; its one home, since the report writes it

def render(result: DiagnosticResult, spec: ModelSpec) -> str: ...
    # S1's sections in order, the title from result.title; the header (S2); numbers by fmt (S3);
    # EXPLAIN_INTERVALS once, and the line under each estimates table (S4, 0042); ids as 12 hex digits (0055);
    # result.extra is not printed (0041); a pure function of its inputs, so a report rebuilt from the store
    # is byte-identical (P1)
def to_pdf(report_path: str) -> str: ...              # pandoc with lualatex, the fonts matplotlib's DejaVu; PandocMissing, PdfFailed (0018, 0059)
```

### `ema.runner` (3b)

The serial loop of 0015, and the only code that runs a model (AR4, P3). `Resolution` and `RunKey` are
`ema.types`'s, so `ema.approval`, a sibling, can take them (AR1).

```python
def resolve(design: Design, model: LoadedModel, store: Store, *, retry_failed: bool) -> Resolution: ...
    # Q1; a failed current run is new only with retry_failed, as the next attempt (C46, C47, 0010)
def price(resolution: Resolution, store: Store) -> Price: ...   # Q2: "unknown" with no stored runs (P3)
def run_new(model: LoadedModel, resolution: Resolution, approval_id: str, store: Store,
            processes: ModelProcesses, *,
            on_progress: Callable[[Progress], None] | None = None) -> int: ...
    # the caller holds store.run_lock() (§7). Before each call: Q13 for the call's keys, refusing a key the
    # approval doesn't cover, or another model version (P3), and check_files (M16). Calls of at most batch_size and never
    # more than remain approved, counted when a call starts (C48, M8); prepare → execute → collect → W4 →
    # delete the run directories keep doesn't keep (I5, M14). Ctrl-C: the call is killed, its directories
    # deleted, and KeyboardInterrupt re-raised, with every finished run stored (C49). Returns the runs made.
def read_batch(design: Design, run_ids: np.ndarray, store: Store, *, new_approval: str | None) -> RunBatch: ...
    # the given run for each design row, in design order (C56; Q15): the ids the workspace builds (the
    # resolution's row_runs, each new row's RunKey.run_id filled in through row_keys), or a provenance's ids
    # on a replay; a row is new when its
    # run's approval is new_approval (E6). Never "the current run now", so another process's retry can't
    # slip in.
```

### `ema.approval` (3b)

P3's one approval module ("from day 1"), and T3's record of every answer.

```python
def ask_approval(*, store: Store, model: LoadedModel, asked_for: str, request: Request | TestRunRequest,
                 design: DesignIdentity | None, resolution: Resolution, price: Price,
                 approve: Approver | None) -> str: ...
    # renders the question: the model version and the price; on the model version's first approval
    # (Q4), also the command and the program's path (resolve_program), or a Python function's `function`,
    # the input deck templates, the files, and the environment the spec sets (U2, 0029, trust.md); calls approve (an Exception, or no answer, is a no); records the answer and the question
    # (W3), with the approved points on a yes; returns the approval id, or raises ApprovalDeclined.
    # approve=None means nobody can be asked (an MCP client without elicitation): CannotAsk at once, with
    # nothing rendered or recorded, since nothing was asked (T3); the workspace checks it before the lock
def ask_confirmation(*, store: Store, spec_path: str, spec_text: str, confirm: Approver | None) -> None: ...
    # the same for saving a model spec an MCP client drafted (W2, 0049): the absolute path, what the name
    # means now, and the full text (T6); raises ApprovalDeclined on a no
def ask(question: ApprovalRequest | ConfirmationRequest) -> bool: ...
    # the terminal approver, ema.ask: prints question.text, reads y/N; end of input is a no
```

v1's approval rules that `scope.md` keeps (paths compared as files, credentials refused, the approval covering
what decides a run) are placed by `trust.md`, by layer (0057): asking and recording are here; the checks a
spec needs are in `ema.types.model` and `ema.models.files`; the environment in `ema.models.sandbox`; the
MCP root in `ema.workspace`.

### `ema.diagnostics` (3b)

```python
@dataclass(frozen=True)
class DiagnosticParameter:
    name: str
    type: str                                  # the spec's Type column
    default: Any | Callable[[int, Mapping[str, Any]], Any]   # a value, or a rule of d and the others (2P)
    default_text: str
    meaning: str
    changes_design: str                        # the spec's "Changes the design?" (C14)
    other_value: Any                           # a second valid value, for C14's check
    def parse(self, value: Any) -> Any: ...    # from Python, the CLI's text, or MCP's JSON; RequestError
    def json_schema(self) -> Mapping[str, Any]: ...   # C55

class Transform(Enum):                         # under y → a·y + b (C5)
    UNCHANGED = "unchanged"; SCALED = "times a"; AFFINE = "a·v + b"; SCALED_ONLY = "unchanged under a·y only"

class Diagnostic(Protocol):
    name: str                                  # "scatter"
    title: str                                 # "Scatter", for the report's title (S1)
    summary: str
    takes_space: bool                          # False for the point run (U7)
    parameters: tuple[DiagnosticParameter, ...]
        # every row of the spec's parameter table except `space` and `prediction`, which are run's own
        # arguments for every diagnostic; C14 checks `prediction` ("no") through the request
    interval_method: str | None                # "bootstrap", or None (uncertainty.md, Per diagnostic)
    spawn_tags: tuple[int, ...]                # C8
    has_estimates: bool                        # C9, C11
    header_rows: tuple[str, ...]               # the labels of its own header rows (C11): ("Fit",) or ()
    constant_note: bool                        # False for the point run: one value is its answer (PT6, C4)
    nesting: tuple[str, ...]                   # the claims C15 checks, by diagnostic parameter
    def observation_scope(self, n_usable: int, batch: RunBatch) -> str: ...
        # the shared observations' label (C10): "Of the 200 usable runs"; the point run's "Of the 5 runs at
        # the point"
    def transform(self, table_key: str, key: str) -> tuple[Transform, bool]: ...
        # each estimate's and observation cell's change under y → a·y + b, and whether it is computed through
        # a logarithm (C5), by its table's and its own stable keys, whatever the model's names; a cell that
        # holds a run's kind (the point run's rows) has key "kind", UNCHANGED
    def strips(self, batch: RunBatch, result: DiagnosticResult) -> Mapping[tuple[str, int], np.ndarray]: ...
        # (figure name, panel index in its data card) → the (n,) mask of the rows whose runs the panel draws, for each panel with a strip:
        # C12 checks that each of those runs that isn't usable appears once in the panel's data card
        # (all rows: the strip's count equals the header's)
    def example_request(self, d: int) -> Mapping[str, Any]: ...
    def min_runs(self, d: int, params: Mapping[str, Any]) -> tuple[int, str]: ...   # the minimum, and why (C3)
    def design_identity(self, space: ModelParameterSpace | None, params: Mapping[str, Any],
                        spec: ModelSpec, model_version_id: str) -> DesignIdentity: ...
        # space is None for the point run, which builds its own from x (ModelParameterSpace.at_point, 0049)
    def compute(self, batch: RunBatch, ctx: AnalysisContext, *, estimates_allowed: bool) -> Computation: ...
        # estimates_allowed is False below the minimum: observations only (C3); evaluate decides it
    def figures(self, batch: RunBatch, result: DiagnosticResult, ctx: AnalysisContext,
                out_dir: str) -> tuple[Figure, ...]: ...
        # from the stored runs and the stored result only (P1, 0037): a rebuild draws the same data cards;
        # numbers a figure needs beyond the result (the polynomial model's ŷ and ŷ₋ₖ) are recomputed from
        # the result's coefficients and the runs

@dataclass(frozen=True)
class AnalysisContext:
    request: Request
    spec: ModelSpec
    space: ModelParameterSpace
    interval_method: IntervalMethod | None     # from the registry by the diagnostic's name, so a fake
                                               # replaces it (C19)
    measured_noisy: tuple[MeasuredNoisy, ...]  # Q10's records, or a provenance's on a replay (C16, 0055)
    on_progress: Callable[[Progress], None] | None

@dataclass(frozen=True)
class Computation:
    estimates: tuple[EstimateTable, ...]
    observations: tuple[ObservationTable, ...]
    notes: tuple[Note, ...]                    # the diagnostic's own notes
    header_rows: tuple[tuple[str, str], ...]
    extra: tuple[EstimateTable, ...]           # kept out of the report (0041)
    measured_noisy: MeasuredNoisy | None       # the point run's, when it measured variation (point_run.md, W5);
                                               # evaluate fills its result id and model version

def evaluate(diagnostic: Diagnostic, batch: RunBatch, ctx: AnalysisContext,
             provenance: Provenance, result_id: str, out_dir: str) -> DiagnosticResult: ...
    # the only entry point: the shared precheck (usable runs, the minimum, constant; P6), the shared
    # observations (C10) and notes (shared.md, Notes), then compute; the result built and round-tripped
    # through its JSON (C17), then figures from that copy
def register(d: Diagnostic) -> None: ...
def get(name: str) -> Diagnostic: ...
def names() -> tuple[str, ...]: ...
```

| Module | Diagnostic | Design | Numbers | Interval method |
|---|---|---|---|---|
| `point_run.py` | point run | `point` | observations: the value, the replicates' spread; measured noisy (W5) | none |
| `scatter.py` | scatter | `uniform` | mean, standard deviation, rank correlations, binned indices | bootstrap |
| `coordinate_lines.py` | coordinate lines | `coordinate_lines` | per line: range, Gram degrees above the floor, rate (observations, 0038) | none |
| `lines.py` | lines (random or given) | `random_lines` or `lines` | as coordinate lines, through `_lines.py` | none |
| `linear_model.py` | linear model | `convergent` | coefficients, relative residual, R², LOO error; per-level observations | bootstrap |
| `polynomial_model.py` | polynomial model | `convergent` | relative residual, R², Sobol indices, √E_k, LOO error; coefficients in `extra` (0041); no active subspace or shadows (0039) | bootstrap |

**Progress (PM10).** One callback, `on_progress(Progress)`, for both phases: the runner's runs and the
analysis. The bootstrap reports through `IntervalMethod.intervals(on_step=…)`, and the polynomial model
reports A's shape and memory before it starts. An exception from the callback stops the diagnostic
evaluation: its runs are kept, and no diagnostic result is stored (C49).

## 7. Layer 4: `ema.workspace`

The only module the guides use, and the only one the CLI and the MCP server call (AR3). It computes nothing
itself: it calls the lower layers in the order the rules require (P3, P5, C50, C51), so that order is written
once. A `Workspace` object (OD-16, decided 2026-10-01) holds the open store and the model versions' children
(`ModelProcesses`).

```python
def open_workspace(path: str | os.PathLike = "ema_workspace", *, root: str | os.PathLike | None = None) -> "Workspace": ...
    # creates it, or opens it (an older schema migrated, a newer refused: data_model.md §11); with root,
    # every method that takes a path refuses one outside the root or inside a workspace, and a drafted
    # spec's file resolving outside the root (PathRefused; trust.md, T5; the MCP server's, 0057)

ResultRef = DiagnosticResult | str            # a result, or its id: any unique prefix of ≥ 4 hex digits (Q11)

class Workspace:                              # not frozen; a context manager; close() stops the children
    path: str

    # models
    def load_model(self, path: str | os.PathLike) -> LoadingSummary: ...                     # W1; U6's message; 0054
    def list_models(self) -> list[ModelSummary]: ...
    def describe_model(self, name: str) -> ModelDescription: ...
    def propose_model(self, spec: str | Mapping[str, Any], path: str | os.PathLike) -> Proposal: ...
        # validates and renders a drafted spec; saves nothing (U9)
    def save_model(self, spec: str | Mapping[str, Any], path: str | os.PathLike, *,
                   confirm: Approver | None) -> LoadingSummary: ...
        # validates as propose_model does (an invalid spec is refused, nothing asked); asks the confirmation
        # with the absolute path, what the name means now, and the full text (W2, T6): the path ends in .json,
        # its parent exists; a different existing file is refused before asking; the same bytes are asked as
        # "already saved, unchanged: load it?"; writes the file, and loads it (W1). One call per MCP tool.
    def test_model(self, name: str, *, approve: Approver | None) -> RunInfo: ...
        # the test run at the nominal point: priced and approved like any new run (0049); stored: no question

    # diagnostics
    def list_diagnostics(self) -> list[DiagnosticSummary]: ...
    def describe_diagnostic(self, name: str) -> DiagnosticSummary: ...
    def price(self, model: str, diagnostic: str, space: Mapping[str, Any] | ModelParameterSpace | None = None, *,
              prediction: str | None = None, retry_failed: bool = False, **params) -> Price: ...
    def run(self, model: str, diagnostic: str, space: Mapping[str, Any] | ModelParameterSpace | None = None, *,
            prediction: str | None = None, retry_failed: bool = False, approve: Approver | None,
            on_progress: Callable[[Progress], None] | None = None, **params) -> DiagnosticResult: ...

    # results
    def get_result(self, result: ResultRef) -> DiagnosticResult: ...                  # Q6
    def list_results(self, *, model: str | None = None, model_version: str | None = None,
                     diagnostic: str | None = None, prediction: str | None = None) -> list[ResultSummary]: ...
    def report(self, result: ResultRef, *, pdf: bool = False) -> Report: ...
        # rebuilds a missing result directory from the store (data_model.md §6); pdf through pandoc (0018)
    def failed_runs(self, result: ResultRef) -> list[RunInfo]: ...
        # every run not usable for the result's model prediction: failed, or missing it, with its reason
        # (U3); the note's "lists each one" (shared.md)
    def run_dirs(self, id: str, *, point: Mapping[str, float] | None = None) -> list[RunInfo]: ...
        # a run id: that run; a result and a point: its runs there, one per replicate (0020, Q9)
    def reproduce(self, result: ResultRef | Provenance) -> Reproduction: ...          # U8, 0055: replays, no runs
    def export(self, result: ResultRef, directory: str | os.PathLike) -> str: ...     # E1–E7 (_export.py)

    def close(self) -> None: ...              # stops the model children and closes the store
```

- **`approve` and `confirm` have no default.** They are called only when there are new runs, or a file to
  save (P3); a repeated request asks nothing (C50). `None` says nobody can be asked: new runs and saving are
  refused before any question, and nothing is recorded (the MCP server without elicitation, §8).
- **The point run takes no space** (U7); any other diagnostic without one is refused: "scatter needs a model
  parameter space".
- **Errors:** only `EMAError` subclasses are raised on purpose. A declined approval raises `ApprovalDeclined`
  ("declined: no runs made"), and a changed model file `ModelChanged`; U4's declined line and U6's refused
  line are written as `try: … except ema.ApprovalDeclined:` (and `ema.ModelChanged`), so the use cases run as
  written (C53; record 0056). Ctrl-C passes
  through as `KeyboardInterrupt`, with every finished run stored.
- **Diagnostic parameters** are keyword arguments (`n=200, seed=1`), parsed by the diagnostic's
  `DiagnosticParameter`s, the same parsing the CLI's `--param` and the MCP server's `params` use.
- **What is shown:** a `DiagnosticResult` the workspace returns carries `shown` (its short id and EMA's text:
  "Diagnostic result 3f2a: scatter on beam@91c0…, T_max; 200 runs: 200 new, 0 reused, 0 failed; report:
  ema report 3f2a"), which the CLI prints and the MCP server puts in `text`; it is not stored (§3).

### The public names and their budget

| # | Name | Use cases, records |
|---|---|---|
| 1 | `open_workspace` | U1–U8 |
| 2–7 | `load_model`, `list_models`, `describe_model`, `propose_model`, `save_model`, `test_model` | U1, U2, U6, U9; 0016, 0049, 0054 |
| 8–11 | `list_diagnostics`, `describe_diagnostic`, `price`, `run` | U1–U7; 0010, 0049 |
| 12–18 | `get_result`, `list_results`, `report`, `failed_runs`, `run_dirs`, `reproduce`, `export` | U3, U5, U6, U8; 0018, 0020, 0055 |
| 19 | `close` | |

**Counting rule:** `scope.md`'s: `open_workspace` and every public `Workspace` method, `close` included;
result types and errors are not counted, nor `ema.ask`, which is `ema.approval`'s. 19 of 20 (20 if `ema.ask`
were counted, as `use_cases.md`'s asks did). The draft's `get_figure` is gone: a result's figures are files in its
directory (`DiagnosticResult.figures`), and the MCP server serves them as resources (§8).

### One diagnostic evaluation, in order (`workspace/_evaluate.py`)

1. **The model:** its current loading (Q3) and model version (Q14), as a `LoadedModel` (`stored_model`); its
   tracked files hashed again, refused when they changed since loading, naming the file (U6, M16).
2. **The request:** the diagnostic from its registry; its parameters and the space parsed and checked, with
   defaults filled in (G15, M6); the canonical `Request`.
3. **The design:** its size from the request, refused over the cap (G5); then built.
4. **Resolve** (Q1), without the lock: each design row's stored run, or a new key; `retry_failed` makes the
   failed ones new (C47). Any number of processes may do this, and everything after it but step 6
   (`data_model.md` §10).
5. **No new keys:** the reuse key from the run ids and the versions (EMA, numpy, scipy, matplotlib); a stored
   result for it is returned, and nothing is written or asked (C50, I7); otherwise, on to step 7.
6. **New keys:** with `approve=None`, `CannotAsk` at once, before the lock. Otherwise the run lock is taken (a second process making runs is refused with `WorkspaceBusy`, naming
   it), and the design resolved again under it, so no other process's runs are priced as new; if no new keys
   remain, the lock is released and step 5 follows. Otherwise the price
   (Q2); the approval (`ema.approval`, W3), or `ApprovalDeclined`; the new runs (`ema.runner`: Q13 and the
   files checked before each call, W4 after it, the cap counted when a call starts); then the lock is
   released. The lock is held while the approval waits for its answer: one process makes runs at a time.
7. **The batch** (`read_batch`): each row's run from the latest resolution (step 6's, when it ran; steps 5
   and 7 both use it), with each new row's `RunKey.run_id` filled in by the workspace through `row_keys`, in design order (C56); the reuse key from those ids; the measured-noisy records for this model prediction (Q10).
8. **The analysis:** `ema.diagnostics.evaluate` (precheck, compute, figures) into the store's temporary result
   directory; `ema.report.render`; then one transaction: the result, its provenance, its runs, and a point
   run's measured-noisy rows (W5, C51, I8). If another process stored a result with the same id meanwhile
   (two identical requests at once), the stored result is returned and nothing more is written
   (`Store.result_directory`, §5; I7; record 0056 adds this to `data_model.md` §6 and W5).
9. **Return** the `DiagnosticResult`.

`test_model` follows steps 1, 4, and 6 for one point (the nominal point, replicate 0): a one-row `Design`
with no identity, the test run's request (a `TestRunRequest`, `data_model.md` §3.4), and no design in its
approval (W3's `design` is NULL for the test run).

**`reproduce`** (`workspace/_reproduce.py`; U8, `data_model.md` §9 Replay, 0055) takes a result (stored, or
read from an export's `result.json` with `DiagnosticResult.from_json`) or a bare `Provenance`, and writes
nothing:

- the design is rebuilt from the provenance's `design` identity; the batch is its run ids, in its order
  (`read_batch`, Q15, so a deleted result's runs are found); a row is new when its run's approval is the
  provenance's approval, so the header's counts are the original's;
- the model version's spec is Q14's, from the provenance's model version;
- the measured-noisy records are the provenance's `measured_noisy_read`, not Q10's, so a later point run
  changes no note;
- the replay keeps the original's result id and `Provenance` (versions included), so it differs from the
  original only where the numbers do; this EMA's versions are compared with the provenance's separately, into
  `provenance_differences` (U8: "Differs: 2 estimates. Provenance differs in numpy");
- the analysis, figures, and report run into a temporary directory, with no W5; the replayed result, its data
  cards, and its report are compared byte for byte with the original's (given, or the stored result whose id
  is the reuse key over the provenance's model version, request, run ids, and versions);
- with no original (a provenance alone, its result deleted and not given), `identical` is None and the replayed
  result is returned.

**`export`** (`workspace/_export.py`) writes `export.md`'s files from Q6 and Q7: `runs.csv` (`%.17g`, the
`ema_` columns), `result.json`, and a copy of the result's directory as `report/` (E1–E7).

## 8. Layer 5: the CLI and the MCP server

Presentation only (AR3): parse the input, call one workspace function, and show the `text` EMA rendered. Neither
formats a number (C54, C55; P1).

### `ema.cli`

13 commands of `scope.md`'s 15. A global `--workspace DIR` (default `ema_workspace`).

| Command | Calls |
|---|---|
| `ema model add PATH` | `load_model` |
| `ema model test NAME [--yes]` | `test_model` |
| `ema models [NAME]` | `list_models`, or `describe_model` |
| `ema diagnostics [NAME]` | `list_diagnostics`, or `describe_diagnostic` |
| `ema price MODEL DIAGNOSTIC [--space FILE] [--param k=v]… [--prediction P] [--retry-failed]` | `price` |
| `ema run MODEL DIAGNOSTIC [--space FILE] [--param k=v]… [--prediction P] [--retry-failed] [--yes]` | `run`; a progress line on stderr |
| `ema results [ID] [--model M] [--model-version V] [--diagnostic D] [--prediction P]` | `get_result`, or `list_results` |
| `ema report ID [--pdf]` | `report` (0018) |
| `ema failed-runs ID` | `failed_runs` (U3) |
| `ema run-dirs ID [--point FILE]` | `run_dirs` (0020) |
| `ema reproduce ID` | `reproduce` (U8) |
| `ema export ID DIR` | `export` (E1) |
| `ema mcp --root DIR` | starts the MCP server; `--root`, required and absolute (not `/`, nor inside a workspace), is the directory its path arguments may name (`trust.md`, T5, E7); a relative `--workspace` resolves against it |

- **`--space FILE`** is `designs.md`'s JSON form (U2); `--param k=v` is parsed by the diagnostic's
  `DiagnosticParameter` (a JSON value, or a bare string), as `run`'s keyword arguments are.
- **Approval:** the price and the question on stderr, then `Approve? [y/N]`. `--yes` approves the price in
  advance: the approval is still priced, shown, and recorded with its question and answer (W3). With no
  terminal and no `--yes`, there is no answer, which is a no.
- **Exit codes:** 0 success; 1 an `EMAError` (a declined approval included); 2 bad usage; 130 Ctrl-C.
- **Not in the CLI:** `propose_model` and `save_model`, which serve an MCP client; on the command line the
  analyst writes the spec and runs `ema model add`.

### `ema.mcp`

Started by `ema mcp`; needs the `ema[mcp]` extra (`scope.md`). Each tool is one workspace call (0016).

| Kind | Name | Calls |
|---|---|---|
| tool | `models(name?)` | `list_models`, or `describe_model` |
| tool | `diagnostics(name?)` | `list_diagnostics`, or `describe_diagnostic`: each parameter with its JSON schema (C55) |
| tool | `propose_model(spec, path)` | `propose_model` |
| tool | `save_model(spec, path)` | `save_model` (it validates, then asks), its confirmation by elicitation (0049) |
| tool | `test_model(name)` | `test_model`, its approval by elicitation |
| tool | `price(model, diagnostic, space?, params?, prediction?, retry_failed?)` | `price` |
| tool | `run_diagnostic(model, diagnostic, space?, params?, prediction?, retry_failed?)` | `run`, its approval by elicitation, its progress as MCP progress notifications |
| tool | `results(id?, model?, model_version?, diagnostic?, prediction?)` | `get_result`, or `list_results`; `data` leaves out the run ids (an export holds them) |
| tool | `failed_runs(id)` | `failed_runs` |
| tool | `export(id, directory)` | `export`, only inside the directory named when the server started (E7, step 10) |
| resource | `ema://results/{id}/report` | `report(id)`: byte-identical to the file (U9) |
| resource | `ema://results/{id}/figures/{name}.png` and `.json` | `report(id)`, then the figure's file and its data card in the result's directory |
| resource | `ema://diagnostics/{name}` | `describe_diagnostic` |

10 tools, `scope.md`'s cap (0016, 0053). Figures are resources, beside the report (record 0056).

- **The envelope:** every tool returns `{ok, data, text, see, error: {message, retryable}}`: `text` is EMA's
  rendering; `data` the returned type as strict JSON, with full ids and short ids; `see` the resources and
  tools that hold more, never advice on what to do (0017), such as "ema://results/3f2a…/report"; `error`
  from the `EMAError`, with its `retryable`.
- **Threads:** the MCP SDK is asynchronous, and the workspace is not. The server keeps two `Workspace`s on the
  same directory, each on its own dedicated thread (a `concurrent.futures.ThreadPoolExecutor` of one worker,
  so each SQLite connection stays on one thread): one for the tools that may run or write (`save_model`,
  `test_model`, `run_diagnostic`, `export`), one for the rest and the resources, so reads and prices answer
  while a run of hours goes on (`data_model.md` §10: any number of readers). The `Approver` blocks its thread
  while the elicitation is asked on the event loop (`asyncio.run_coroutine_threadsafe`); progress is sent the
  same way. Standard library only: no new dependency beside `mcp` (`scope.md`).
- **Approvals and confirmations** are asked by elicitation, with the same text as the terminal's; a declined
  elicitation is a no (0016), and so is one unanswered after `ELICITATION_TIMEOUT_S` = 900 s (a named
  constant in `mcp/server.py`, chosen here), which frees
  the run lock.
- **A client without elicitation** can't be asked, so `save_model`, `test_model`, and a run with new runs are
  refused before any question ("this client can't ask the analyst; use the CLI or Python"; P3), and no
  approval is recorded, since none was asked (T3). Reads, prices, and repeated requests work.
- **`params`** is one JSON object, described by `diagnostics(name)` (C55); `space` is `designs.md`'s JSON form.
- **The tool descriptions and the server's instructions** are one reviewed file, `ema/mcp/tools.md` (0019).
  The instructions ask the client to quote EMA's text, give result ids, and point the analyst to the report,
  rather than restate numbers (P1).
- **No tool writes a file that EMA runs** (U9): `save_model` writes a model spec only (0016).
- **Confined** (`trust.md`, T5): every path argument lies inside the root and outside any workspace;
  resources are looked up by name, never joined into a path; the instructions in `tools.md` say that
  reasons and stderr lines are quoted model output.

## 9. Contracts and tests

One contract module per interface (`contracts.md`), each a list of `check_*` functions run over every registered
implementation with `pytest.mark.parametrize`, with its toy and its broken toys.

| Interface | Contract module | Promises | Run over |
|---|---|---|---|
| `Diagnostic` | `tests/contracts/diagnostic.py` | C1–C19 | the six diagnostics and the toy, on run batches built directly |
| `DesignGenerator` | `tests/contracts/design.py` | C20–C27 | the six generators and the toy |
| `Sampler` | `tests/contracts/sampler.py` | C28 | `random`, a fake nested sampler, a fake sampler that isn't nested |
| `Basis` | `tests/contracts/basis.py` | C29 | `total_degree`, a fake |
| `IntervalMethod` | `tests/contracts/interval.py` | C30 | the bootstrap, a fake |
| the model adapter | `tests/contracts/model.py` | C31–C45 | a Python function, the same as a batch, and a command-line program (`tests/models/`), every Python model isolated (0026); the three parsers |
| `Store` | `tests/contracts/store.py` | C46–C52, C56; I1–I12 | the store; with the runner and millisecond models for C47–C49 (the cap counted at a call's start, an interrupt) |
| `Workspace` and CLI | `tests/contracts/workspace.py` | C53, C54 | the use cases U1–U9 (slow tier), the guides' examples, and every CLI command against its workspace function |
| MCP tools | `tests/contracts/tools.py` | C55 | every tool, through a scripted MCP client (U9) |

The fast tier also runs the import contracts (§10) and the terminology test (0008).

## 10. Enforcing the layers

The full set, as v2.0 ends. From the first build step, each contract lists only the layers and source
modules that exist, and grows as build steps add packages; a forbidden module may be named before it exists
(0059).

```toml
# pyproject.toml
[tool.importlinter]
root_package = "ema"
include_external_packages = true

[[tool.importlinter.contracts]]
name = "AR1 One-way layers"
type = "layers"
layers = [
    "ema.cli | ema.mcp",
    "ema.workspace",
    "ema.runner | ema.approval | ema.diagnostics",
    "ema.plotting | ema.report",
    "ema.models | ema.store",
    "ema.numerics | ema.designs",
    "ema.types",
]

[[tool.importlinter.contracts]]
name = "AR2 No I/O in layers 0-1"
type = "forbidden"
source_modules = ["ema.types", "ema.numerics", "ema.designs"]
forbidden_modules = ["os", "pathlib", "subprocess", "sqlite3", "shutil", "tempfile", "time", "random",
                     "socket", "matplotlib"]

[[tool.importlinter.contracts]]
name = "AR3 The interfaces call only the workspace"
type = "forbidden"
allow_indirect_imports = true
source_modules = ["ema.cli", "ema.mcp"]
forbidden_modules = ["ema.numerics", "ema.designs", "ema.models", "ema.store", "ema.plotting",
                     "ema.report", "ema.runner", "ema.approval", "ema.diagnostics"]

[[tool.importlinter.contracts]]
name = "AR4 Only the runner runs a model"
type = "forbidden"
allow_indirect_imports = true
source_modules = ["ema.types", "ema.numerics", "ema.designs", "ema.store", "ema.plotting", "ema.report",
                  "ema.approval", "ema.diagnostics", "ema.workspace", "ema.cli", "ema.mcp"]
forbidden_modules = ["ema.models.execute"]

[[tool.importlinter.contracts]]
name = "AR5 Only the store opens the database"
type = "forbidden"
allow_indirect_imports = true
source_modules = ["ema.types", "ema.numerics", "ema.designs", "ema.models", "ema.plotting", "ema.report",
                  "ema.runner", "ema.approval", "ema.diagnostics", "ema.workspace", "ema.cli", "ema.mcp"]
forbidden_modules = ["sqlite3"]

[[tool.importlinter.contracts]]
name = "AR6 No LLM SDK (P1)"
type = "forbidden"
source_modules = ["ema"]
forbidden_modules = ["anthropic", "openai", "google", "langchain", "langchain_core", "litellm",
                     "mistralai", "cohere", "ollama"]

[[tool.importlinter.contracts]]
name = "Reference models are data beside the layers"
type = "forbidden"
source_modules = ["ema.types", "ema.numerics", "ema.designs", "ema.models", "ema.store", "ema.plotting",
                  "ema.report", "ema.runner", "ema.approval", "ema.diagnostics", "ema.workspace", "ema.cli",
                  "ema.mcp"]
forbidden_modules = ["ema.reference_models"]
```

- **Indirect imports:** a forbidden contract also refuses chains through other `ema` modules unless
  `allow_indirect_imports` is set. AR3, AR4, and AR5 set it, since `ema.cli → ema.workspace → ema.store →
  sqlite3` is the design; AR2, AR6, and the reference models' contract don't, since no chain may reach those.
- **External packages** are named at their top level only (`google`, not `google.genai`), as grimp keeps them.
- **Standard-library modules** (AR2, AR5): import-linter sees them as external packages (checked at step 12
  with import-linter 2.15, 0059), so no AST test checks these lists; the first build step's AR2 contract
  confirms it on EMA's own code.
- **`ema.experimental`:** none in v2.0 (0017). P2's contract (nothing in layers 0–3 imports it) is added here
  with the package.
- **One AST test** in the fast tier checks what import-linter can't express: AR7 (no module imports the root
  `ema`), and that `ema/models/__init__.py` doesn't import `execute`, so AR4 can't be bypassed through the
  package's re-exports.
- `uv run lint-imports` runs in the fast tier (CLAUDE.md's fast-tier command, 0059).

## 11. Size

Source lines estimated per package against `scope.md`'s 8,000 (2026-10-01), from v1's counterparts and the
specs:

| Package | Estimate | Main parts |
|---|---|---|
| `ema.types` | 775 | the model spec's validation (~200, and ~75 for `trust.md`'s checks), the result types, `identity.py` (~100) |
| `ema.numerics` | 550 | the basis (ported, ~150), fits and PRESS, the bootstrap, the Gram spectrum |
| `ema.designs` | 350 | the `random` sampler, six generators (lines ~150) |
| `ema.models` | 1,300 | the sandbox and worker (ported, ~435 without v1's limits and withheld variables), the environment and path checks (~35), the three phases, parsers, `ModelProcesses` |
| `ema.store` | 700 | `data_model.md` §10 |
| `ema.plotting`, `ema.report` | 540 | escaping text EMA didn't write (~10) |
| `ema.runner`, `ema.approval` | 410 | the questions' rendering (`trust.md`) |
| `ema.diagnostics` | 2,000 | base and precheck ~300; the six, 150–400 each |
| `ema.workspace` | 610 | the evaluation's order ~250; export ~120 (E1–E7); reproduce ~60; the root (~10) |
| `ema.cli`, `ema.mcp` | 705 | `--root` |
| **Total** | **7,940** | 60 under the budget (0057 added about 80): tight, so each plan reports its package's count |

- **Reference models ship with `ema`,** in `ema/reference_models/` (each a model spec with its function or
  program), counted against their own 1,000 lines, not the 8,000. The get-started guide and the use cases'
  "Done when" tests load them from an installed EMA; `ema.reference_models.path(id)` gives one's directory.
- **Each build step's plan** measures its package against its line here, and reports an overrun.

## 12. Decisions

| Item | Decision | Record |
|---|---|---|
| "One-way layers" | architecture rules AR1–AR7, not a principle (prefix AR, since P3 cites "v1's bug A1") | 0056 |
| where `version_hash` lives | `ema.types.identity` (pure); file hashing in `ema.models` | this spec |
| whether `report` imports `diagnostics` | no | this spec |
| OD-16: a `Workspace` object or module functions | the object | 0056 |
| the workspace's names | 19 of 20, counted as §7 says | this spec |
| the use cases' `result.report()` and `ws.estimate` | `ws.report(result)` and `ws.price` | 0056 |
| the MCP tools (11 candidates, a cap of 10) | figures as resources; 10 tools | 0056 |
| W6's public name | none in v2.0 | 0056 |
| the approval checked before each call, not only after (P3) | a new store read, Q13, per call's keys | 0056 |
| a result's own model version's spec; runs by id for a replay | new store reads, Q14 and Q15 | 0056 |
| how long an unanswered elicitation waits | `ELICITATION_TIMEOUT_S` = 900 s, then a no | this spec |
| connections | one `Store` per thread (the MCP server holds two); `BUSY_TIMEOUT_S` = 60 s | 0056; this spec |
| the run lock's kind | `flock` on a held descriptor (excludes a second holder in the same process) | this spec |
| two identical requests at once | W5 on a stored id writes nothing and returns the stored result | 0056 |
| a client that can't be asked | `approve=None` / `confirm=None`: refused before any question, nothing recorded | this spec (T3 records questions asked) |
| the run lock | taken only when there are new runs, from resolving again through the last new run | this spec (`data_model.md` §10) |
| the space's class name | `ModelParameterSpace`, as 0005 says | 0005 |
| a declined approval, a changed file | raise `ApprovalDeclined`, `ModelChanged`; U4's and U6's lines show them | 0056 |
| reference models | ship in `ema/reference_models/` | this spec |
| the model's environment | `BASE_ENV`, `pass_env`, `env`, for both kinds of model | 0057 |
| the MCP root | `ema mcp --root DIR`, required; `open_workspace(..., root=)` | 0057 |
| v1's approval rules | placed by layer (§6) | 0057 |

## What this spec asks of other documents

- **Record 0056, applied 2026-10-01:**
  - `principles.md`: the candidate "One-way layers" removed (answered by AR1–AR7); P2's "`architecture.md` §11"
    becomes §10, which says the contract comes with the package.
  - `README.md`: the id prefix AR (architecture rule, `architecture.md`).
  - `use_cases.md`: `print(x.report())` becomes `print(ws.report(x))` (U1, U2, U3, U7); "`estimate` exists"
    becomes "`price` exists" (U1), and `estimate` becomes `price` in the asks; U4's declined level-2 line and
    U6's refused line are written as `try: … except`; U9's `get_result` becomes the `results`
    tool; the introduction's "provisional until that spec is accepted" goes, and U7's sentence on `run`'s
    signature.
  - `data_model.md`: §2 and §8 gain Q13 (which of one call's keys an approval covers and has no run for yet, for which
    model version: the runner, before each call), Q14 (a model version's spec and tracked files, by its id:
    `report`, export, `reproduce`), and Q15 (runs by id, in the order given: every run batch, and `reproduce`);
    §2's Q7 is asked by export and `failed_runs`, and Q7 and Q15 return `ema.types.RunColumns`, with no object
    per row; W5 on a result id already stored writes nothing and returns the stored result (two identical
    requests at once, I7); §6: a result directory already in place with a row is kept, and the new temporary one
    discarded; I9 is enforced by `read_batch`'s order (Q15) as well as Q7's `ORDER BY row`; §10:
    one `Store` per thread that uses it (the MCP server holds two) in place of "one `Store` per process",
    `records.py` holds the store's own rows rather than one class per table, the Read-by column gains Q13
    (`approvals`, `approval_points`, `runs`), Q14 (`model_versions`), and Q15 (`runs`, `predictions`), and the
    table names
    `ema.types`'s `Run` (with its model predictions, for `Run` and `Prediction`), `DiagnosticResult` (for
    `Result`), `MeasuredNoisy`, and `DesignIdentity`, and adds `Coverage`; W6's "a public name is step 9's"
    becomes "no public name in v2.0".
  - `contracts.md`: C53–C55 provisional until the guides (step 13) only; "`architecture.md` §10" becomes §9
    (three places); C54's Generalizes, "the held principle 'One-way layers'", becomes AR3.
  - `model_interface.md`: the note on `architecture.md`'s stubs says they follow this spec.
  - 0016's status: "its tool list amended by 0053 (export) and 0056 (figures as resources)".
  - `STATUS.md`: OD-16 decided (0056).
- **Trust (step 10):** done (`trust.md`, 0057).
- **Setup (step 12):** done (0059): import-linter sees standard-library imports (§10); CLAUDE.md's commands.
- **Guides (step 13):** each guide walked through against §7; any awkward step changes §7 first.
