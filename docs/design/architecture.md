# Architecture: packages, layers, and modules

**Status:** accepted (TODO step 9; 0056). **Updated:** 2026-10-01 (0057: the trust rules placed; 0059: the tooling;
0060: the guides; 0061: generators called with an identity, `ema.cli` over `ema.mcp`, the stderr tail, `remove_tree`; 0062: replays from stored points, `GOLDEN_UNIT_TOL`; 0063: `DesignStructure` in the provenance; 0064: §11's estimates; 0065: `unregister`, G18, a given line's direction); 2026-10-02 (the demo build's
choices, accepted: 0067: the space's array shapes, the registries' errors; 0068: no vector-vector BLAS, the
numerics' signatures; 0069: the trust names, `save_spec`'s errors; 0070: ids as `V32`, timestamps, the store's
columns, the `make` renderers; 0071: the three phases' and the child's names, AR4's sources; 0072: the store's
names, `current_keys`; 0073: the plotting helpers, `lines_through_anchor`; 0074: the runner's and the approval's
errors, the runner's contract; 0075: the diagnostics' base; 0076: the column-wise statistics; 0077: `_lines.py`;
0078: `_fits.py`; 0079: `dtrtrs`, `Name`; 0080: the workspace's paths, rebuilds, and texts, `model_names`,
`fenced`; 0081: the MCP server, `Stopped`, AR3's two contracts, export's PDF, a repeated request's text,
`describe_model`'s settings; 0082: the CLI; 0084: §11's measured counts against 11,000; 0085: the fits' in-sample
measures as observations; review round 1 of applying 0066–0085). **Depends on:** P1–P7; `scope.md`;
`use_cases.md` (U1–U9); `model_interface.md` (M1–M21); `designs.md` (G1–G18); `diagnostics/shared.md` (S1–S10)
and the six diagnostic specs; `uncertainty.md` (V1–V7);
`contracts.md` (C1–C56); `data_model.md` (Q1–Q12, W1–W6, I1–I12; Q13–Q15 added by 0056); `export.md` (E1–E7);
records 0005, 0008, 0010, 0015–0022, 0024–0030, 0032–0036, 0040, 0041, 0046, 0047, 0049, 0050, 0053–0055, 0057,
0067–0082, 0084, 0085;
`trust.md` (T1–T10). Rewritten from the specs' "Architecture (step 9)" asks and the consistency review's "Step 9
inputs"; the draft of 2026-09-28 (`api_spec_draft.md`) is replaced.

> Every package and module in v2.0, what each is for, its layer, and its public names, with signatures, so
> each module's code and contract tests can be written against it. Signatures are Python stubs (`...` for the
> body); every public class is a frozen dataclass unless marked otherwise, and nothing public returns a bare
> `dict`. A mapping field is made read-only (`MappingProxyType`) in `__post_init__`, and a default mapping is
> `field(default_factory=dict)`. A class holding numpy arrays is `eq=False` (a dataclass's own equality can't
> compare arrays); the results compare by their JSON (§3), and contract tests compare designs and batches with
> `np.array_equal`, field by field (C14, C20; C14 compares a design's arrays, not its identity, 0061). Every type with a `text` field prints as that text. Array shapes are in
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
| 5: interfaces | `ema.cli` over `ema.mcp` | parse the input, call one workspace function, show EMA's text | terminal, stdio |

`|` separates siblings, which never import each other. In layer 5, `ema.cli` sits above `ema.mcp`: its `mcp`
command imports `ema.mcp.server` lazily, and `ema.mcp` never imports `ema.cli` (0061). `ema.reference_models` (§11) is data beside the
layers: no module in `ema` imports it (a forbidden contract, §10). Layer 3 is split in two so that the diagnostics can draw
figures; the numbers 0–5 stay as the other specs cite them ("layers 0–1", "layer 4").

```text
ema.cli ──▶ ema.mcp                                 5  interfaces (0061)
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
| AR2 | **No I/O in layers 0–1:** no files, processes, database, clock, or randomness without a seed argument. | Layers 0–1 are checked with known-answer tests and no fixtures; P4. | a forbidden contract on `os`, `pathlib`, `subprocess`, `sqlite3`, `shutil`, `tempfile`, `time`, `socket`, the standard library's `random`, and `matplotlib` (§10); Ruff's NPY002 |
| AR3 | **The interfaces hold no logic.** `ema.cli` and `ema.mcp` import only `ema.workspace` and `ema.types`, and `ema.cli` imports `ema.mcp` lazily, in its `mcp` command only, which needs the `ema[mcp]` extra (0061); neither imports `numpy`, `scipy`, `matplotlib`, or `ema.reference_models` (0081); every number they show is text EMA rendered (C54, C55; P1). | A computation in an interface would differ between the notebook, the CLI, and the agent. | two forbidden contracts, one per interface (0081, 0082) |
| AR4 | **Only `ema.runner` runs a model:** it is the only importer of the execute phase, `ema.models.execute` (P3); `collect.py` names `ExecutedCall` under `TYPE_CHECKING` only (0071). | One place checks the approval before every run. | a forbidden contract, every other module of `ema.models` among its sources |
| AR5 | **Only `ema.store` opens the database,** and only the main process writes it (0015). | The store's invariants (I1–I12) hold in one module. | a forbidden contract on `sqlite3` |
| AR6 | **No LLM SDK anywhere** (P1). | No number EMA produces can come from an LLM. | a forbidden contract on `anthropic`, `openai`, `google` (its SDKs), `langchain`, `langchain_core`, `litellm`, `mistralai`, `cohere`, `ollama` |
| AR7 | **`ema/__init__.py` only re-exports;** no module in `ema` imports the root package. | No import cycles through the root; `import ema.types` doesn't load matplotlib or the sandbox. | an AST test (§10); the root's re-exports are lazy (PEP 562 `__getattr__`) |

Beside AR2, a rule for P4 (0068): **no vector-vector BLAS in `ema`**, whose results on Accelerate depend on the
operands' addresses. Inner products and norms of 1-D arrays go through `ema.numerics._vector`'s `dot` and `norm`,
and every matrix-vector product through its `matvec`; Ruff's banned-api rule (TID251) and an AST test enforce it
(§10).

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
  __init__.py                 lazy re-exports: open_workspace, Workspace, ResultRef, ask, the errors but Stopped
                              (re-exported by ema.types only, 0081 item 25), and the types the workspace returns
                              (AR7; 0080)
  types/                      layer 0
    identity.py               TrackedFile; canonical JSON, point hash, version hash, ids, the approval id, the
                              reuse key, alpha as a Fraction; ID_DTYPE, id_array, hex_ids (0070)
    text.py                   fmt (S3), durations, timestamps (0070)
    _values.py                reading numbers: a bool never one, an integral float an integer (0067, 0070)
    streams.py                spawned streams (SeedSequence with a spawn key), for designs and diagnostics
    model.py                  ModelParameter, Limits, PredictionSpec, parsers' settings, PythonFunction,
                              CommandLine, InputDeck, FileEntry, Keep, ModelSpec; hidden_character,
                              is_credentials_file, CREDENTIAL_WORDS, EMA_FILE_NAMES (trust.md; 0069)
    space.py                  Scale, Range, ModelParameterSpace
    design.py                 DesignIdentity, Line, Design, DesignStructure
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
    stats.py                  rank correlation, binned index, and their column-wise forms (0076)
    intervals.py              IntervalMethod, Estimator, the registry, bootstrap
    tolerance.py              P6's one tolerance function; is_constant (0068)
    _vector.py                dot, norm, matvec, centered: no vector-vector BLAS (P4, 0068)
  designs/                    layer 1
    samplers.py               Sampler, the registry, random
    generators.py             DesignGenerator, the registry, MAX_DESIGN_POINTS
    point.py  uniform.py  convergent.py  lines.py      the generators
    _common.py                the checks the generators share: check_identity, sampler_of, read_params, space_of,
                              rows (0067; check_identity's int seed, item 32)
  models/                     layer 2
    spec.py                   LoadedModel, load_spec, stored_model, save_spec, resolve_program
    files.py                  hash_files, same_file, is_within, check_files, remove_tree, leads_to_credentials,
                              open_regular, write_own (0069, 0071)
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
  runner.py                   layer 3b: resolve, price, run_new, read_batch, replay_batch
  approval.py                 layer 3b: ask_approval, ask_confirmation, ask
  diagnostics/                layer 3b
    base.py                   Diagnostic, DiagnosticParameter, Transform, AnalysisContext, Computation,
                              the registry, evaluate (the precheck)
    point_run.py  scatter.py  coordinate_lines.py  lines.py  linear_model.py  polynomial_model.py
    _lines.py                 the per-line computation coordinate lines and lines share (0077)
    _fits.py                  what the linear and polynomial models share: the fit's values, the bootstrap's two
                              estimators, the per-level table (0078)
  workspace/                  layer 4
    __init__.py               open_workspace, Workspace, ResultRef; ask, re-exported for the CLI (0080)
    _evaluate.py              the order of one diagnostic evaluation (§7)
    _export.py                export (E1–E7)
    _reproduce.py             reproduce (U8)
  cli.py                      layer 5: one module (0082)
  mcp/                        layer 5
    server.py                 the tools and resources; serve, ELICITATION_TIMEOUT_S, PROGRESS_INTERVAL_S
    __main__.py               python -m ema.mcp, as ema mcp (0081)
    tools.md                  the tool descriptions and the server's instructions, one reviewed file (0019)
  reference_models/           not counted in the 11,000 lines (scope, 0084); §11
tests/
  contracts/                  one module of check_* functions per interface (§9)
  support/                    the tests' shared helpers and fakes (LeanIntervalMethod, 0084 item 3)
  models/                     the toy models: python, batch, command_line, imports (contracts.md)
  unit/  slow/
```

## 3. Layer 0: `ema.types`

The vocabulary of the whole application: data, and pure functions of it. It imports only the standard
library's pure modules (`dataclasses`, `enum`, `json`, `hashlib`, `struct`, `fractions`, `math`, `types`,
`typing`, `collections.abc`, `re` and `keyword` for the model spec's own checks (0061), `unicodedata` for the spec's hidden-character check (0057), `datetime` for the type of stored
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

ID_DTYPE = np.dtype("V32")                              # ids in arrays: 32 raw bytes, kept whole (an S32 element
                                                        # drops trailing zero bytes); zeros mean none (0070)
def id_array(ids: np.ndarray | Sequence[str] | Sequence[bytes]) -> np.ndarray: ...   # every form batch_call_id
                                                        # takes → an (n,) ID_DTYPE array
def hex_ids(ids: np.ndarray | Sequence[str] | Sequence[bytes]) -> tuple[str, ...]: ...

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
def timestamp_text(when: datetime) -> str: ...      # every stored timestamp: ISO 8601 in UTC to the millisecond,
def parse_timestamp(text: str) -> datetime: ...     # "2026-10-01T14:03:07.123Z"; a naive datetime refused (0070)
def duration(seconds: float) -> str: ...   # the price's wording (U2), one rule (0061, 0062): rounded first,
    # then the unit chosen: under 10 s one significant digit ("about 0.2 s", "about 4 s"); under a minute whole
    # seconds; under an hour whole minutes ("about 40 min"); otherwise "about 3 h 12 min", or "about 2 h"
    # when the minutes are 0; each rounding half up on the decimal repr of the value, and a value that
    # rounds to its unit's limit written in the next unit; below 0.01 s, before rounding, "under 0.01 s"
    # (0063). Known answers: 0.004 s "under 0.01 s", 0.04 s "about 0.04 s", 0.2 s "about 0.2 s", 2.5 s
    # "about 3 s", 4.4 s "about 4 s", 9.96 s "about 10 s", 59.7 s "about 1 min", 90 s "about 2 min",
    # 3599 s "about 1 h", 7200 s "about 2 h", 11,520 s "about 3 h 12 min"
```

### `types/model.py`

`model_interface.md`'s spec, one dataclass per part. `ModelSpec.from_json` validates everything that needs
no file: names (lowercase model names; identifiers, unique across model parameters and model predictions;
no `ema_` prefix, M21), `noisy: true` refused (M18), nominal values inside limits, required fields, and
**unknown keys refused, naming the key**. Checks that need files (templates' names, M10; unlisted imports,
M17) are `ema.models.load_spec`'s. `trust.md`'s names that `ema.models`, `ema.approval`, and the workspace's root
check share are public here, and re-exported by `ema.types` (0069):

```python
def hidden_character(text: str) -> str | None: ...     # the first hidden character (T7), or None
def is_credentials_file(path: str) -> bool: ...        # by its "/"-separated parts' names (T7)
CREDENTIAL_WORDS: frozenset[str]
EMA_FILE_NAMES = ("point.json", "run.json", "predictions.json", "stdout.txt", "stderr.txt")

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
    def versioned_json(self) -> str: ...                # without keep, batch_size, timeout_s (data_model.md §3.4)
    def parameter(self, name: str) -> ModelParameter: ...           # RequestError for an unknown name (0067)
    def prediction(self, name: str | None) -> PredictionSpec: ...   # None: the only one, or refused (RequestError)
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
    def to_unit(self, spec: ModelSpec, X: np.ndarray) -> np.ndarray: ...     # (n, d_all) → (n, d_varied) z in [-1, 1];
                                                       # x clamped to [lo, hi] first, lo and hi exact (0047, 0061, 0067)
    def from_unit(self, spec: ModelSpec, Z: np.ndarray) -> np.ndarray: ...   # (n, d_varied) → (n, d_all); clamped;
                                                       # faces exact
    def from_cube(self, spec: ModelSpec, U: np.ndarray) -> np.ndarray: ...   # the sampler's (n, d_varied) rows in
                                                       # [0, 1) → (n, d_all) points (designs.md: sampling the unit
                                                       # cube); clamped to [lo, hi] on every scale (0067)
    def contains(self, spec: ModelSpec, X: np.ndarray) -> np.ndarray: ...    # (n, d_all) → (n,): varied values in
                                                       # their closed ranges, held values exactly equal (0067)
    def clip_line(self, spec: ModelSpec, anchor_z: np.ndarray,
                  direction_z: np.ndarray) -> tuple[float, float]: ...       # the segment's t range
    def canonical(self) -> Mapping[str, Any]: ...      # every range as {"range": [lo, hi], "scale": …}
```

### `types/design.py`

```python
@dataclass(frozen=True)
class DesignIdentity:
    """A design's identity (0046, data_model.md §3.4): stored with each result and approval. With the
    provenance's DesignStructure and the stored runs' points, a replay needs no generator; with today's
    generator at the identity's versions, the design can also be rebuilt (0063)."""
    model_version_id: str
    kind: str                                 # "point", "uniform", "convergent", "lines",
                                              # "coordinate_lines", "random_lines"
    space: Mapping[str, Any]                  # canonical form
    params: Mapping[str, Any]                 # the generator's parameters that aren't fields here (no seed,
                                              # sampler, or versions); alpha as its decimal string
    seed: int                                 # the request's seed, for every kind; only seeded generators
                                              # use it (0061)
    sampler: str | None                       # with its version, for uniform and convergent
    sampler_version: str | None
    generator_version: str
    def canonical(self) -> Mapping[str, Any]: ...

@dataclass(frozen=True)
class Line:
    anchor: tuple[float, ...]                 # model parameter units
    direction: tuple[float, ...]              # unit coordinates, one per varied model parameter; a given
                                              # line's as the user gave it, a random line's normalized (0065)
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

@dataclass(frozen=True)
class DesignStructure:
    """What a diagnostic reads from a design beyond its points and replicates (0063); kept in a
    result's provenance, so a replay builds its Design with no generator."""
    levels: tuple[int, ...] | None            # convergent: n_0 … n_L
    lines: tuple[Line, ...] | None            # lines: anchor, direction, ends, and rows, each
```

### `types/runs.py`

Ids in arrays are `ID_DTYPE` (`V32`), zeros meaning none; the status and kind codes in `RunColumns` are each
member's index (`code`, `from_code`: ok 0, failed 1; error 0, timeout 1, unread 2; −1 for an ok run's kind). These
types, and those of `results.py`, refuse with `ValueError` what a store check or a spec forbids: a bad record is a
mistake in EMA's code, not a user's request (0070).

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
    @classmethod
    def make(cls, model_version_id: str, point: Sequence[float], replicate: int, attempt: int) -> "RunKey": ...
        # computes the point hash and the run id (0070)

@dataclass(frozen=True, eq=False)
class Resolution:
    """A design resolved against the store (Q1): what pricing, approval, and running share."""
    design: Design
    model_version_id: str
    row_runs: np.ndarray                      # (n,) each design row's stored run id (32 bytes), or zeros when new
    row_keys: np.ndarray                      # (n,) each new row's index into new_keys, or -1 when stored
    new_keys: tuple[RunKey, ...]              # distinct (point, replicate) keys to run, attempts set (C47);
                                              # each RunKey.run_id is known before the run (data_model.md §3.4)
    reused_failed: int

@dataclass(frozen=True, eq=False)
class RunColumns:
    """Stored runs, one row each, in the order asked for (Q7, Q15): columns, so 10⁷ rows (the design cap) cost
    tens of bytes each, not a Run object each."""
    run_ids: np.ndarray                       # (n,) 32-byte ids
    points: np.ndarray | None                 # (n, d): Q7 fills it (export, failed_runs), and Q15 for a replay
                                              # (0062); a diagnostic reads its points from batch.design, which
                                              # a replay builds from these (0063)
    replicates: np.ndarray                    # (n,)
    status: np.ndarray                        # (n,) RunStatus codes
    kind: np.ndarray                          # (n,) FailureKind codes; -1 when ok
    values: Mapping[str, np.ndarray]          # model prediction → (n,); NaN where missing or failed
    reasons: Mapping[str, str]                # failed run id (hex) → its one-line reason
    stderr_tails: Mapping[str, str]           # failed run id (hex) → its stderr tail; Q7 fills it, Q15
                                              # leaves it empty (0061)
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
    @classmethod
    def make(cls, *, new: int, reused: int, reused_failed: int = 0, time_s: float | None,
             from_runs: int) -> "Price": ...  # the text's one renderer, the time by duration (0070)
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
    settings: Mapping[str, Any]               # JSON data: the method's own (resamples, percentiles, min_defined)
                                              # and the diagnostic's seed and distinct (0073, 0075)
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
    made_at: datetime | None                  # set by W5, read by Q10; copied whole into a provenance
                                              # (data_model.md §5.12); None in a result's own record, so a result
                                              # is a function of its request and runs (P4; 0072)

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
    design_structure: DesignStructure          # so a replay needs no generator (0063)
    def column(self) -> str: ...              # the store's provenance column: the versions, spawn tags, measured-
                                              # noisy records read, design structure (0070)
    @classmethod
    def from_columns(cls, column: str, *, model_version_id: str, request: str, design: str,
                     approval_id: str | None, run_ids: np.ndarray) -> "Provenance": ...
    def canonical(self) -> Mapping[str, Any]: ...   # the whole provenance, ids as hex: an export's, a bare replay's
    @classmethod
    def from_canonical(cls, form: Any) -> "Provenance": ...

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
    def column(self) -> str: ...              # the store's result column: title, counts, header rows, notes,
                                              # estimates, observations, figures, extra (0070); the rest has
                                              # columns and tables of its own, the run ids result_runs' rows
    @classmethod
    def from_columns(cls, *, result_id: str, model_version_id: str, diagnostic: str, prediction: str,
                     result: str, measured_noisy: MeasuredNoisy | None,
                     provenance: Provenance) -> "DiagnosticResult": ...

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
    @classmethod
    def make(cls, result: DiagnosticResult, *, short_id: str, model_version: str,
             made_at: datetime) -> "ResultSummary": ...   # §7's text (0070)

@dataclass(frozen=True)
class Reproduction:
    result_id: str
    result: DiagnosticResult                  # the replayed result
    identical: bool | None                    # None: no original to compare (a provenance alone, its result
                                              # deleted and not given)
    differences: tuple[str, ...]              # "2 estimates", "data card scatter_E", "report"
    provenance_differences: tuple[str, ...]   # "numpy: 2.3.1 here, 2.4.0 there"
    text: str                                 # U8's message
    @classmethod
    def make(cls, result: DiagnosticResult, *, result_id: str, short_id: str, identical: bool | None,
             differences: tuple[str, ...] = (), versions: tuple[tuple[str, str, str], ...] = (),
             design_differences: tuple[str, ...] = ()) -> "Reproduction": ...
        # U8's text; versions as (name, here, there); result_id the original's, which the replay keeps (0070)
```

### `types/requests.py`

```python
@dataclass(frozen=True)
class Request:
    """What one diagnostic evaluation is asked for (glossary); canonical, defaults filled in (data_model.md §3.4)."""
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
                                              # as codes; strings EMA didn't write in code spans or fenced blocks);
                                              # no prompt: the terminal adds "Approve? [y/N]", an elicitation its
                                              # form (0074)

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
    @classmethod
    def of_runs(cls, done: int, total: int) -> "Progress": ...   # "40/96 runs" (0070)
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
    spec: ModelSpec                           # the model version's, with the current loading's settings (keep,
                                              # batch_size, timeout_s), as its runs use them (0081)
    text: str                                 # the model parameters, units, nominal values and limits as the spec
                                              # writes them (repr, 0080), predictions; then the runs' settings:
                                              # "Runs: a timeout of 0.2 s per call; one point per call; run
                                              # directories kept: all"; a batch function "batches of up to N
                                              # points per call" (0081 item 32), or "one batch per call" with
                                              # no batch_size

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
    type: str                                 # "integer ≥ 1", "integer ≥ 0", "decimal in (0, 1)", …
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
    stderr_tail: str | None                   # a failed run's last 15 lines of stderr, shown in text as
                                              # quoted model output (trust.md, Model output and the MCP client; 0061)
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
| `EMAError` | the base of every error EMA raises on purpose; raised itself for a `Workspace` called from a thread other than the one that opened it (0080) | |
| `SpecError` | a model spec doesn't validate (field named) | no |
| `RequestError` | a space, a diagnostic parameter, or a design's identity is refused (G14, G15, G18, M6) | no |
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
| `PathRefused` | an MCP path argument outside the root, inside a workspace, with a hidden character, naming a credentials file, or too long for the file system; a drafted spec's file resolving outside the root (`trust.md`, T5, T7; 0080); a save path `save_spec` can't write as T6 says (0069); an export directory that isn't empty, or can't be made (0080). A spec naming a credentials file is a `SpecError`. | no |
| `Stopped` | an evaluation stopped between two runs, its caller having cancelled or left (the MCP server's `on_progress`: a cancelled call, a client gone, SIGTERM); every finished run is stored (0080, 0081) | no |

## 4. Layer 1: `ema.numerics` and `ema.designs`

Pure functions of arrays (AR2). Every random draw takes a seed, or a `np.random.Generator` made by
`ema.types.streams.spawned` (layer 0), which `ema.designs` and `ema.diagnostics` share.

### The four interfaces kept as seams

Each has a registry (`register`, `get`, `names`, `unregister`), its v2.0 implementation, and a fake registered in
the tests through the same `register`, removed by a fixture with `unregister`: no monkeypatching (C19, C28–C30).
`register` refuses a name already taken, and `unregister` a name not registered, each with `ValueError` (a mistake
in a test or a later plugin, not a user's request; 0067, 0068); a fixture that registers a
second version of a generator (C51) unregisters the first, and restores it afterwards (0065). Nothing in `ema`
calls `unregister`; the output parsers' and the diagnostics' registries (§5, §6) have it too. A name with no
implementation is refused by `get` with `RequestError`, "<kind> X comes in a later version" (`designs.md`,
`polynomial_model.md`; "sampler", "design generator", "basis", "interval method").
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
GOLDEN_UNIT_TOL = 1e-12                       # golden points across machines, in unit coordinates (G1, 0062)
class DesignGenerator(Protocol):
    name: str
    version: str
    def size(self, identity: DesignIdentity, spec: ModelSpec) -> int: ...     # closed form (G3)
    def build(self, identity: DesignIdentity, spec: ModelSpec,
              start: int = 0, stop: int | None = None) -> Design: ...       # refuses over the cap first (G5, G6)
    # stateless (0061): everything comes from the identity, whose params hold the names listed below; an
    # identity of another generator or sampler version is refused, naming both (RequestError; 0062)

# numerics/basis.py (polynomial_model.md; C29)
class Basis(Protocol):
    name: str
    def terms(self, d: int, degree: int) -> np.ndarray: ...       # (P, d) multi-indices, the constant first
    def n_terms(self, d: int, degree: int) -> int: ...            # without building them
    def evaluate(self, Z: np.ndarray, terms: np.ndarray) -> np.ndarray: ...   # (n, P), orthonormal on [-1, 1]^d

# numerics/intervals.py (uncertainty.md, the interface; C30)
@dataclass(frozen=True)
class Estimator:
    """One computation per resample, giving one or more estimates: a fit's coefficients (and the polynomial
    model's Sobol indices and √E_k) come from one refit, not one refit per number."""
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
    @property
    def settings(self) -> Mapping[str, Any]: ...        # read-only; JSON values, canonical_json writes them as
                                                        # they are; the bootstrap's a fresh dict each call (0068)
    def intervals(self, usable: np.ndarray, levels: np.ndarray | None,
                  estimators: Sequence[Estimator], stream: np.random.Generator,
                  on_step: Callable[[int, int], None] | None = None) -> dict[str, tuple[Interval, ...]]: ...
        # estimator name → one Interval per label; undefined resamples are dropped and counted per label (V4)
        # on_step(done, total): the analysis's progress (PM10); an exception from it stops the method
```

### `ema.numerics`

| Module | Public names | From |
|---|---|---|
| `basis.py` | `Basis`, `register`, `get`, `names`, `unregister`, `TotalDegree` (Legendre) | `polynomial_model.md`; v1's `core/legendre.py`, ported after re-review |
| `gram.py` | `gram_coefficients(y) -> np.ndarray` (c_k of evenly spaced samples; exactly (y₀, 0, …, 0) for a constant y); `tail(c) -> np.ndarray` (T(k), indexed by degree k = 0 … n − 1); `degrees_above_floor(T, floor) -> int` (k*, over the T it is given: the window and the absolute floor are the caller's); `decay_rate(T, k_star, min_degrees) -> tuple[float, float] \| None` (rate and intercept, or none) | `coordinate_lines.md`, `lines.md` (0038, 0068) |
| `fitting.py` | `Fit` (coefficients, residuals, rank, leverages; all but the rank NaN when the rank is below P, 0068); `least_squares(A, y) -> Fit` (QR, R solved with LAPACK's `dtrtrs`, 0079; its rank from R's singular values by 0051's rule), `rank(A) -> int` (0051's rule), `press(A, y, fit) -> float` (the LOO error, √Σ(r_k/(1 − h_kk))² / ‖y − ȳ‖), `r2(y, fit) -> float`, `relative_residual(y, fit) -> float`; each NaN where undefined (0068) | `linear_model.md`, `polynomial_model.md`; no k-fold cross-validation |
| `sobol.py` | `sobol_indices(coef, terms, *, y) -> (first, total)` (NaN arrays for a constant y, or V = 0; 0068), `degree_energy(coef, terms)` (√E_k) | `polynomial_model.md` |
| `stats.py` | `rank_correlation(x, y)`, `binned_index(x, y, bins)`, and their column-wise forms for the bootstrap, `rank_correlations(X, y)`, `binned_indices(X, y, bins)`, with `average_ranks(A)` (0076) | `scatter.md` |
| `intervals.py` | `Estimator`, `Interval`, `IntervalMethod`, `register`, `get`, `names`, `unregister`, `Bootstrap`; `BOOTSTRAP_RESAMPLES`, `BOOTSTRAP_PERCENTILES`, `BOOTSTRAP_MIN_DEFINED` | `uncertainty.md`; no `convergence_interval` (0040) |
| `tolerance.py` | `tolerance(values, rel) -> float`: `rel` × the range of the values (P6's one function); `is_constant(y) -> bool`: every value the same double, the one test of "constant" (0068) | P6 |

### `ema.designs`

| Module | Public names | From |
|---|---|---|
| `samplers.py` | `Sampler`, `register`, `get`, `names`, `unregister`, `Random` | `designs.md`, Samplers (0032) |
| `generators.py` | `DesignGenerator`, `register`, `get`, `names`, `unregister`, `MAX_DESIGN_POINTS`, `GOLDEN_UNIT_TOL` | `designs.md`, Shared rules |
| `point.py` | `Point`: `x`, `repeats` | Point (0011, 0049) |
| `uniform.py` | `Uniform`: `n` | Uniform |
| `convergent.py` | `Convergent`: `n_min`, `alpha` (its decimal string, read with `decimal_fraction`), `level`; sizes ⌈n_min·alpha^(−l/r)⌉ in exact arithmetic | Convergent (0047) |
| `lines.py` | `GivenLines`: `lines`, `n`; `CoordinateLines`: `n`, `anchor`; `RandomLines`: `m`, `n`; `SHARED_ANCHOR_TOL`; `lines_through_anchor(identity, spec) -> tuple[str, ...]`, the varied model parameters whose coordinate line has the anchor's run as its middle point, by the rule `CoordinateLines` builds with (the report's Design row; 0073) | Lines (0047, 0051) |

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

def load_spec(path: str) -> LoadedModel: ...       # reads, validates (M10, M17, M18, M21; a plain def's arguments
    # against the model parameters, 0081), hashes; SpecError. The model's directory is the spec's, its links
    # resolved (C33; 0069)
def stored_model(spec: ModelSpec, files: tuple[TrackedFile, ...], spec_path: str) -> LoadedModel: ...
    # plain values, since ema.models can't import ema.store (AR1): the workspace passes Q14's stored spec,
    # with the current loading's settings (Q3: keep, batch_size, timeout_s) set on it, its tracked files,
    # and the loading's spec path. Runs use the stored spec; an edited spec file takes effect only when
    # it is loaded again (0054). The tracked files are checked before each call (check_files).
def save_spec(spec: ModelSpec, path: str) -> None: ...   # for save_model; refuses to overwrite a different file;
    # writes with an exclusive create, so a file that appears meanwhile is kept (T6). PathRefused for the path (not
    # ending in .json, a missing directory, a link to nothing, another file there, one appearing first); SpecError
    # when from_json refuses the text it would write; the same bytes write nothing (0069)
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
def remove_tree(path: str) -> None: ...             # deletes a run or batch directory without following links;
    # used by prepare (a leftover directory) and ema.runner (keep) (trust.md, T9; 0061)
def leads_to_credentials(path: str, directory: str) -> str | None: ...   # its links' target, when a credentials
    # file (T7; 0069)
def open_regular(path: str) -> BinaryIO: ...        # a regular file only, never blocking on a FIFO or a device (0069)
def write_own(directory: str, name: str, data: bytes) -> None: ...   # one of EMA's files in a run or batch
    # directory, without following a link, created exclusively (T9; 0071)

# models/processes.py
MAX_CHILDREN = 4                         # the least recently used child stopped beyond it (0071)
class ModelProcesses:                    # not frozen; owned by the Workspace, passed to execute
    def child(self, model: LoadedModel) -> Child: ...   # the model version's; TypeError for a command line (0071)
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

def prepare(model: LoadedModel, keys: Sequence[RunKey], runs_dir: str, shared_dir: str, *,
            approval_id: str) -> PreparedCall: ...
    # writes point.json, the input decks (M10's number rule), copied files, links to shared copies (M15); a batch
    # model's every call has a batch directory, where the function runs with the listed files (0071)

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
    run_errors: tuple[str | None, ...]   # per run, why EMA couldn't write its predictions.json (kind error; 0071)

def execute(model: LoadedModel, call: PreparedCall, processes: ModelProcesses) -> ExecutedCall: ...
    # a command: no shell, its own process group, stdin /dev/null (M2, M20); a Python function: its
    # isolated child, started in `processes` when it has none (M9); streams to stdout.txt and stderr.txt;
    # Ctrl-C kills the call and re-raises

# models/collect.py
def collect(model: LoadedModel, call: ExecutedCall) -> tuple[Run, ...]: ...
    # model predictions from files only: the parsers, or predictions.json (M13); status and kind (0043);
    # run.json in each run directory; never raises for a point (M1). ExecutedCall is named under TYPE_CHECKING
    # only, so collect never imports execute (AR4; 0071)
STDERR_TAIL_LINES = 15
def stderr_tail(call_dir: str) -> str | None: ...   # a failed run's: the last lines of its call's stderr.txt, from
                                                    # its last 64 KiB, read inside the directory (0071)
def kept(model: LoadedModel, run: Run) -> bool: ... # the keep rule (incomplete: failed, or a prediction missing)
def keep_or_remove(model: LoadedModel, call: PreparedCall, runs: Sequence[Run]) -> None: ...
    # applies keep; a batch directory deleted with the last of its runs' (data_model.md §5.7)
def discard(call: PreparedCall) -> None: ...        # a stopped call's directories deleted (0028)

# models/parsers.py   (0027; C45)
class OutputParser(Protocol):
    kind: str
    def read(self, settings: ParserSpec, run_dir: str) -> tuple[float | None, str | None]: ...
        # the value, or None with the reason; never follows a link out of the run directory
def register(p: OutputParser) -> None: ...
def get(kind: str) -> OutputParser: ...    # KeyError: a kind from_json already refused; never a user's
def names() -> tuple[str, ...]: ...
def unregister(kind: str) -> None: ...      # tests only (0065)
def read(settings: ParserSpec, run_dir: str) -> tuple[float | None, str | None]: ...   # by the parser it names (M11)
def read_inside(directory: str, file: str, last: int | None = None) -> tuple[bytes | None, str | None]: ...
    # a file's bytes (its last `last` bytes), never following a link out of the directory; or None with the reason

# models/sandbox.py (0071)
BASE_ENV; START_TIMEOUT_S = 60.0; MAX_REPLY_BYTES = 64 << 20
def model_environment(spec: ModelSpec, environ: Mapping[str, str] | None = None) -> dict[str, str]: ...  # trust.md
def find_program(program: str, env: Mapping[str, str], directory: str | None) -> str | None: ...
    # a name on the model's own PATH, a path with a "/" against the run directory; for execute and resolve_program
class InterruptHeld: ...                 # Ctrl-C held while a process starts, delivered once it can be killed (M20)
def has_exited(proc) -> bool: ...        # without reaping it, so its group id can't be a new process's
def kill_group(proc) -> int: ...         # kills its group, then reaps it; Ctrl-C held meanwhile
def readable(fd: int, timeout_s: float) -> bool: ...
def reply_limit(n_runs: int, predictions: Sequence[str]) -> int: ...
    # MAX_REPLY_BYTES, and per run 640 bytes for each model prediction and one more, with the names as JSON writes
    # them, so a correct batch reply is never the child's death (M8, M1)
class Outcome: ...                       # one call of a child: runs, error, timed_out, traceback, time_s (from the
                                         # request's send to its reply; a new child's start and import not in it)
class Child: ...                         # one model version's isolated child; call(call_dir, points, env,
                                         # timeout_s) -> Outcome, close()
```

`sandbox.py` and `_worker.py` hold the isolated child: one long-lived child per model version, JSON (or
arrays in a format that runs no code) and never pickle, killed on a timeout, a crash, or Ctrl-C, and started
again for the next call (0026, M9). Ported from v1's `core/models/_sandbox.py` and `_worker.py` after
re-review; the environment it passes is `trust.md`'s. The child runs in its own process group, killed whole;
it is started by its worker's path, and replaces its `sys.path` with EMA's, made absolute, received over its
pipe; its streams never reach EMA's stdout. `run.json` and `predictions.json` are written without following a
link the model left there, and run and batch directories deleted without following links, by `remove_tree` (`trust.md`, T9; 0061).
`load_spec` never imports the function's file: M17 parses it (`ast`).

### `ema.store`

Exactly `data_model.md` §10: `schema.sql`, `records.py`, `store.py` (one function per write W1–W6 and read
Q1–Q15, each citing its id), `migrations.py`; and:

- `layout.py`: the workspace's paths (`ema.db`, `run.lock`, `runs/`, `files/`, `results/`): `Layout.of(root)`,
  `run_dir(id)` (a run's or a batch call's directory), `result_dir(id)` (0072);
- `lock.py`: the run lock: `fcntl.flock(LOCK_EX | LOCK_NB)` on a descriptor of `run.lock` kept open while it is
  held, so it excludes a second holder in the same process as well as in another (a per-process POSIX lock
  would not), and is released when the descriptor closes or the process exits. Only the workspace that makes
  runs takes it; prices, reads, and reports never do. The holder writes "process <pid> on <host>, since <time>"
  into `run.lock`, which `WorkspaceBusy` names. **Fork caveat** (0072): a child made by a bare `fork` shares the
  open file description, so keeps the lock held; the descriptor is non-inheritable, so the runner starts model
  processes with `subprocess` or `multiprocessing`'s "spawn", never "fork".
- `migrations.py`: `prepare(conn, db, *, latest, migrations)` takes the version and the migrations as arguments,
  so a test migrates a workspace through a migration of its own (0072).
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

Q13 (`approval_coverage`), Q14 (`model_version`), and Q15 (`runs_by_id`) are in `data_model.md` §8, their one
home.

Q7 and Q15 return `RunColumns` (`ema.types`), with no object per row: Q7 for export and `failed_runs` (points,
time, host, program, batch call, approval), Q15 for every run batch, through `read_batch`. Both read in chunks
of 30,000 rows, one statement each, so a writer in another connection waits at most one chunk's read.

```python
class Store:                                          # not frozen: holds the connection
    chunk_rows: int = 30_000                          # class attributes, so a test subclass makes them small (no
    busy_timeout_s: float = 60.0                      # monkeypatching, 0065; 0072)
    @classmethod
    def open(cls, path: str, *, create: bool = True) -> "Store": ...
        # path: the workspace's directory; create makes it and runs/, files/, results/; with create=False and
        # no ema.db, NotFound (0072)
        # migrates an older schema after copying ema.db; refuses a newer one (WorkspaceVersion); waits up to
        # BUSY_TIMEOUT_S = 60 s for another connection's lock (SQLite's busy timeout), so a read in one
        # connection delays a write in another instead of failing it; W4 retries past the timeout until it
        # commits, since its call has finished and its runs must be stored (C49); reads are chunked (below),
        # so the wait is one chunk's
    layout: Layout                                    # paths: db, lock, runs/, files/, results/ (layout.py's frozen
                                                      # dataclass; data_model.md §1)
    def run_lock(self) -> ContextManager[None]: ...   # WorkspaceBusy, naming the holder
    def result_directory(self, result_id: str, *,
                         complete: Callable[[str], bool] | None = None) -> ContextManager[str]: ...
        # a temporary directory, renamed into place before record_result commits (§6 there). If results/<id>
        # exists: with a row (Q5), the temporary directory is discarded and the stored result is the answer,
        # with no W5; with no row, it is replaced. If W5 then finds the id stored (two identical requests at
        # once), it writes nothing, and what is in place stays: its report and data cards are byte-identical.
        # With complete (a stored result's directory rebuilt), one in place that complete says is incomplete is
        # replaced too, and a complete one kept (0080). The directory in place is never deleted where it is: it
        # is moved aside under the write lock, which W5 holds while it looks for it (0072)
    # W1–W6 and Q1–Q15, with data_model.md's names and signatures; and, beside them:
    def current_keys(self, model_version_id: str,
                     point_hashes: Sequence[str]) -> dict[tuple[str, int], CurrentKey]: ...
        # Q1's key-only read, what resolve and price need (records.CurrentKey: run_id, attempt, status; a named
        # tuple, one per point); current_runs stays for whole runs (0072)
    def model_names(self) -> tuple[str, ...]: ...    # a read beside Q3, for list_models (0080)
    def close(self) -> None: ...
```

- **Record classes:** where `ema.types` has the class, the store returns it: `Run` (its model predictions folded
  in, for the `runs` and `predictions` tables), `DiagnosticResult` (for `results`), `MeasuredNoisy`,
  and `DesignIdentity` (`data_model.md` §3.4's JSON shape). `records.py` holds the store's own rows:
  `ModelVersion`, `Loading`, `Confirmation`, `Approval`, `ApprovedPoint`, `BatchCall`, `RunUsed` (W5's rows; Q7 and
  Q9 join it), `Coverage`, `CurrentKey` (0072). One class per concept; the workspace's `LoadingSummary` is what a user sees of a
  `Loading` (record 0056 updated `data_model.md` §10's table).
- **W6, `delete_result`,** has no workspace name in v2.0 (record 0056): no use case deletes a result, and U8's
  test deletes through the store (`data_model.md`).

## 6. Layer 3: output and services

### `ema.plotting` (3a)

```python
def new_figure(n_panels: int, *, stacked: bool = False) -> tuple[matplotlib.figure.Figure,
                                                                 Sequence[matplotlib.axes.Axes]]: ...
def axis_label(name: str, units: str) -> str: ...     # "name [units]", or "name" when dimensionless (S9); a
                                                      # spec's $ escaped, so mathtext never reads it (T10)
def strip(ax, x: np.ndarray, kinds: Sequence[FailureKind], log: bool, *,
          run_ids: np.ndarray | None = None) -> list[dict[str, Any]]: ...
    # runs not usable: one × each, below the axes, with the count in the label (shared.md, C12); returns the
    # card's entries, with their run ids (0073)
def save(fig, card: Mapping[str, Any], out_dir: str, name: str, caption: str) -> Figure: ...
    # the PNG and its data card: canonical JSON, indented 2, a final newline (S10); every point drawn from
    # a run has its run id (S9); a name of letters, digits, _ and -, refused otherwise (T10; 0073)
# the drawing helpers, so the six diagnostics draw one way (0073): axis (each axis and its card entry; log=None
# keeps a scale set), title, points, line, vline, hline, bin_means, histogram, intervals, spectrum, empty_panel,
# card_points, card_text
```

The Agg canvas on `matplotlib.figure.Figure`, never `pyplot`; every function runs under matplotlib's default
rcParams and then EMA's fixed ones, one dictionary in the module (`matplotlib.style.context(["default", _RC])`), so a
user's backend and rcParams are left alone and change no figure; `text.usetex` is off (T10). The styled calls hold
one lock, since `style.context` sets process-wide rcParams: two threads drawing at once give the single-threaded
bytes (S10, P4; §8, Threads; 0073).

### `ema.report` (3a)

```python
EXPLAIN_INTERVALS: str                       # shared.md's sentence; its one home, since the report writes it

def render(result: DiagnosticResult, spec: ModelSpec) -> str: ...
    # S1's sections in order, the title from result.title; the header (S2); numbers by fmt (S3);
    # EXPLAIN_INTERVALS once, and the line under each estimates table (S4, 0042); ids as 12 hex digits (0055);
    # result.extra is not printed (0041); a pure function of its inputs, so a report rebuilt from the store
    # is byte-identical (P1)
def to_pdf(report_path: str) -> str: ...              # pandoc with lualatex, the fonts matplotlib's DejaVu; PandocMissing, PdfFailed (0018, 0059)
    # in a temporary directory: every figure the report names checked first (PdfFailed); the reader
    # markdown-raw_tex-raw_html-raw_attribute-tex_math_dollars-smart-implicit_figures, with --sandbox (T10;
    # 0073); the copy pandoc reads gives a figure 48% of the width where a line holds several, 60% alone, and
    # keeps it unnumbered where the report puts it; the stored Markdown is unchanged (S10; 0081)
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
    # deleted, and KeyboardInterrupt re-raised, with every finished run stored (C49); after W4's COMMIT, the call
    # stays stored and keep is applied. Returns the runs made. A call is cut at the first key W4 wouldn't store
    # (its run made since the resolution); ValueError for a call its approval can't cover, or such a first key
    # (a bug in EMA: the workspace runs the resolution it approved, under the lock), NotFound for an unknown
    # approval, ModelChanged from check_files (0074). Model processes are started with subprocess, never a bare
    # fork, which would keep the run lock held (§5, the fork caveat; 0072)
def read_batch(design: Design, run_ids: np.ndarray, store: Store, *, new_approval: str | None) -> RunBatch: ...
    # the given run for each design row, in design order (C56; Q15): the ids the workspace builds (the
    # resolution's row_runs, each new row's RunKey.run_id filled in through row_keys); a row is new when its
    # run's approval is new_approval (E6). Never "the current run now", so another process's retry can't
    # slip in.
def replay_batch(provenance: Provenance, store: Store) -> RunBatch: ...
    # a replay's batch (U8, 0063): the provenance's run ids through Q15 with points=True, and a Design built
    # from its identity, those points and replicates, and its design_structure, with no generator; a row is
    # new when its run's approval is the provenance's approval_id
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
    # nothing rendered or recorded, since nothing was asked (T3); the workspace checks it before the lock.
    # Before asking, NotFound for a model version the store doesn't hold, and, on a first approval, check_files
    # (ModelChanged), so the question shows the version's own templates; ValueError for a price that isn't the
    # resolution's, no new runs, or a request or design that isn't asked_for's; nothing asked or recorded (0074).
    # Only True from approve is a yes; Ctrl-C at the question is recorded as a no and passes through (T3; 0074)
def ask_confirmation(*, store: Store, spec_path: str, spec_text: str, confirm: Approver | None) -> None: ...
    # the same for saving a model spec an MCP client drafted (W2, 0049): the absolute path, what the name
    # means now, and the full text (T6); raises ApprovalDeclined on a no
def ask(question: ApprovalRequest | ConfirmationRequest) -> bool: ...
    # the terminal approver, ema.ask: writes question.text and "Approve? [y/N] " ("Confirm? [y/N] ") to stderr,
    # never stdout (T9), reads one line: "y" or "yes" in any case is a yes; anything else, or end of input, a no
def fenced(text: str) -> str: ...
    # text EMA didn't write as a fenced block, its fence longer than any run of backticks in it, hidden characters
    # as codes (T7); public so the workspace fences a drafted spec and a stderr tail with it (0080)
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
    reader: Reader                             # reads a value into its canonical form, and describes it (0075)
    def parse(self, value: Any) -> Any: ...    # from Python, the CLI's text, or MCP's JSON; RequestError. Text is
        # read as JSON when it is JSON, else as a bare string, then by the reader; a reader whose reads_text is
        # True (DecimalText) gets text as written (0075)
    def json_schema(self) -> Mapping[str, Any]: ...   # the reader's, with the meaning and the default (C55)
    def info(self) -> DiagnosticParameterInfo: ...    # for describe_diagnostic (C55)

class Reader(Protocol):                        # 0075
    def read(self, value: Any, what: str) -> Any: ...      # the canonical value, or RequestError naming what
    def schema(self) -> Mapping[str, Any]: ...
# The readers canonicalize, so one design has one identity (0075): Integer(minimum) (3.0 and "3" as 3);
# DecimalText(lo, hi) (alpha as its shortest decimal text; "1/3" and padded text refused); Point (names to
# doubles: x, an anchor, a direction); GivenLines; Name(names), the one reader for a registry's name (a sampler, a
# basis): any well-formed name read, ^[A-Za-z][A-Za-z0-9_-]*$, an unregistered one left to the registry's "comes
# in a later version" when the design is built; its schema the pattern, with the registered names as examples,
# not an enum (0076, 0078, 0079). seed_parameter(meaning, changes_design) gives every diagnostic's seed row.

class Transform(Enum):                         # under y → a·y + b (C5)
    UNCHANGED = "unchanged"; SCALED = "times a"; AFFINE = "a·v + b"; SCALED_ONLY = "unchanged under a·y only"

class Diagnostic(Protocol):                    # its attributes declared as read-only properties, so class
                                               # attributes meet it (0075)
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

class DiagnosticBase: ...                      # the defaults a diagnostic may keep: observation_scope "Of the n
    # usable runs", transform from the shared observations' keys and a TRANSFORMS mapping, strips none,
    # example_request (0075)

@dataclass(frozen=True)
class AnalysisContext:
    request: Request
    spec: ModelSpec
    space: ModelParameterSpace
    interval_method: IntervalMethod | None     # from the registry by the diagnostic's name, so a fake
                                               # replaces it (C19)
    measured_noisy: tuple[MeasuredNoisy, ...]  # Q10's records, or a provenance's on a replay (C16, 0055)
    on_progress: Callable[[Progress], None] | None
    # and seed, prediction (its PredictionSpec), stream(tag) (spawned(seed, tag)), on_step(what) (the
    # bootstrap's progress, PM10) (0075)

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
    # through its JSON (C17), then figures from that copy. compute is always called, with no usable run too
    # (a diagnostic's own notes); evaluate refuses (ValueError, naming P6) estimates or extra when
    # estimates_allowed is False, and any observation with no usable run. The shared observations are one
    # table keyed "shared" (Minimum, Maximum, the spread), a diagnostic's own "shared" table's rows first. The
    # provenance is checked, not built: its request the context's, its spawn tags the diagnostic's (0075)
def register(d: Diagnostic) -> None: ...   # ValueError for a taken name, or a spawn tag below 2³² or taken (C8)
def get(name: str) -> Diagnostic: ...      # NotFound, naming the diagnostics there are
def names() -> tuple[str, ...]: ...
def unregister(name: str) -> None: ...      # tests only (0065)

# the helpers the workspace and the diagnostics share, written once (0075)
def make_request(diagnostic: Diagnostic, spec: ModelSpec,
                 space: Mapping[str, Any] | ModelParameterSpace | None = None, prediction: str | None = None,
                 params: Mapping[str, Any] | None = None) -> Request: ...
    # §7 step 2: the space parsed and validated, a missing or extra space refused, unknown parameters refused
    # naming the known ones, defaults filled in order, the only model prediction
def request_space(request: Request, spec: ModelSpec) -> ModelParameterSpace: ...
def identity(kind: str, space: ModelParameterSpace, params: Mapping[str, Any], spec: ModelSpec,
             model_version_id: str, *, seed: int, sampler: str | None = None) -> DesignIdentity: ...
    # every design identity is built here: TypeError for a value that isn't canonical JSON data, or a seed that
    # isn't an int; an unregistered sampler refused with G17's words
def describe(d: Diagnostic) -> DiagnosticSummary: ...
def estimate(key: str, label: str, value: float, interval: Interval) -> Estimate: ...
def interval_info(ctx: AnalysisContext, n_usable: int, *, distinct: str | None = None,
                  undefined: Mapping[str, int] | None = None) -> IntervalInfo: ...   # the method's settings,
                                                                                     # seed, distinct (0073)
def library_versions() -> dict[str, str]: ...    # ema, numpy, scipy, matplotlib
def make_provenance(batch: RunBatch, ctx: AnalysisContext, diagnostic: Diagnostic, model_version_id: str, *,
                    approval_id: str | None, versions: Mapping[str, str]) -> Provenance: ...
```

Importing `ema.diagnostics` imports every module of the package but `base` and the private ones, and each
diagnostic module ends with `register(...)`: adding a diagnostic is one module, with no other file to edit (0075).

`_lines.py` (0077) holds what coordinate lines and lines share: `LinesDiagnostic` (a `DiagnosticBase` with hooks
for what differs: a line's label and words, its figure, its card, lines' Length column and ends tables);
`analyze(y, usable, *, all_constant) -> LineAnalysis` (one line's cells, in their precedence; its spectrum);
`draw_spectrum(ax, analysis)`; `window(n)`; and the constants `LINE_RATE_FLOOR`, `LINE_RATE_WINDOW`,
`LINE_RATE_MIN_DEGREES`, `COORD_MIN_N`, `COORD_MIN_RUNS`, `SPECTRUM_YMIN` (its one home; the polynomial model
imports it, 0079), `RATE_SHIFT_TOL`. Lines are read from the batch's design structure, so a replay analyzes the
stored lines. `_fits.py` (0078) holds what the linear and polynomial models share: a fit's values, the bootstrap's
two estimators (the coefficients as drawn; the LOO error on distinct runs), each row's level, the per-level
table, the residual histogram's bins.

| Module | Diagnostic | Design | Numbers | Interval method |
|---|---|---|---|---|
| `point_run.py` | point run | `point` | observations: the value, the replicates' spread; measured noisy (W5) | none |
| `scatter.py` | scatter | `uniform` | mean, standard deviation, rank correlations, binned indices | bootstrap |
| `coordinate_lines.py` | coordinate lines | `coordinate_lines` | per line: range, Gram degrees above the floor, rate (observations, 0038) | none |
| `lines.py` | lines (random or given) | `random_lines` or `lines` | as coordinate lines, through `_lines.py` | none |
| `linear_model.py` | linear model | `convergent` | coefficients, LOO error; the in-sample relative residual and R² as observations, without intervals (0085); per-level observations | bootstrap |
| `polynomial_model.py` | polynomial model | `convergent` | Sobol indices, √E_k, LOO error; the in-sample relative residual and R² as observations, without intervals (0085); coefficients in `extra` (0041); no active subspace or shadows (0039) | bootstrap |

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
    # spec's file resolving outside the root (PathRefused; trust.md, T5; the MCP server's, 0057); a root
    # that is inside a workspace, or is one, or isn't an existing directory, is refused here too (PathRefused;
    # 0061, 0080). Under a root, the workspace's path and every path argument resolve against it, since an MCP
    # server's working directory is the client's choice; a path argument with a hidden character, naming a
    # credentials file below the root, or too long for the file system is refused too (T5, T7; 0080)

ResultRef = DiagnosticResult | str            # a result, or its id: any unique prefix of ≥ 4 hex digits (Q11)

class Workspace:                              # not frozen; a context manager; close() stops the children
    # Workspace(store, root) is built by open_workspace only (0080). It is bound to the thread that opened it, as
    # its SQLite connection is (§5, Connections): a call from another thread is EMAError (0080)
    path: str

    # models
    def load_model(self, path: str | os.PathLike) -> LoadingSummary: ...                     # W1; U6's message; 0054
    def list_models(self) -> list[ModelSummary]: ...
    def describe_model(self, name: str) -> ModelDescription: ...
        # the model version's spec with the current loading's settings, as runs use it (0081)
    def propose_model(self, spec: str | Mapping[str, Any], path: str | os.PathLike) -> Proposal: ...
        # validates and renders a drafted spec; saves nothing (U9). Refuses first what save_model would (a name
        # not ending in .json, a missing parent, another file at the path: PathRefused), so the agent learns it
        # before the user is asked; a file at the path is read with open_regular (0080)
    def save_model(self, spec: str | Mapping[str, Any], path: str | os.PathLike, *,
                   confirm: Approver | None) -> LoadingSummary: ...
        # validates as propose_model does (an invalid spec is refused, nothing asked); asks the confirmation
        # with the absolute path, what the name means now, and the full text (W2, T6): the path ends in .json,
        # its parent exists; a file at the path with another spec, or text that isn't one, is refused before
        # asking; one holding the same spec (its from_json(text).to_json() the drafted spec's rendered text) is
        # asked as "already saved, unchanged: load it?" with its own bytes, never rewritten, and loaded after
        # the yes, refused if it changed meanwhile (0080, 0081); otherwise writes the file, and loads it (W1).
        # One call per MCP tool.
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
        # on_progress is also run's cancellation hook: an exception it raises stops the evaluation between two
        # calls, every finished run kept and no result stored (C49), for a caller off the main thread, where
        # Ctrl-C can't reach a call (the MCP server's Stopped; 0080)

    # results
    def get_result(self, result: ResultRef) -> DiagnosticResult: ...                  # Q6
    def list_results(self, *, model: str | None = None, model_version: str | None = None,
                     diagnostic: str | None = None, prediction: str | None = None) -> list[ResultSummary]: ...
    def report(self, result: ResultRef, *, pdf: bool = False) -> Report: ...
        # rebuilds a result directory missing any of its files (the report, a PNG, a data card) from the store
        # (data_model.md §6), through Store.result_directory(complete=), never deleting it in place (0080); pdf
        # through pandoc (0018)
    def failed_runs(self, result: ResultRef) -> list[RunInfo]: ...
        # every run not usable for the result's model prediction: failed, or missing it, with its reason
        # and a failed run's stderr tail (U3; trust.md, Model output and the MCP client; 0061); the note's "lists each one" (shared.md)
    def run_dirs(self, id: str, *, point: Mapping[str, float] | None = None) -> list[RunInfo]: ...
        # a run id: that run; a result and a point: its runs there, one per replicate (0020, Q9)
    def reproduce(self, result: ResultRef | Provenance) -> Reproduction: ...          # U8, 0055: replays, no runs
    def export(self, result: ResultRef, directory: str | os.PathLike, *, pdf: bool = False) -> str: ...
        # E1–E7 (_export.py); with pdf, report/report.pdf too, made first, so a PDF that can't be made leaves the
        # export's directory unmade (0081)

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
  ema report 3f2a"), which the CLI prints and the MCP server puts in `text`; it is not stored (§3). For a
  repeated request (C50), whose stored result's counts are those of the evaluation that made it, `run`'s text
  says so first: "Diagnostic result 6f6b: the stored result of the same request; no new runs, nothing asked. As
  made: scatter on …; 200 runs: 200 new, …"; `get_result` and `list_results` keep the plain line (0081).
- **`ask`** is re-exported by `ema.workspace`, so the CLI, which imports only `ema.workspace` and `ema.types`
  (AR3), can pass the terminal approver; it is not counted (0080).

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
   result for it is returned, and nothing is written or asked (C50, I7), its shown text saying so (What is
   shown; 0081); otherwise, on to step 7.
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
   run's measured-noisy rows (W5, C51, I8); the provenance's `design_structure` is the batch design's levels and
   lines (0063). If another process stored a result with the same id meanwhile
   (two identical requests at once), the stored result is returned and nothing more is written
   (`Store.result_directory`, §5; I7; record 0056 adds this to `data_model.md` §6 and W5).
9. **Return** the `DiagnosticResult`.

`test_model` follows steps 1, 4, and 6 for one point (the nominal point, replicate 0): a one-row `Design`
with no identity, the test run's request (a `TestRunRequest`, `data_model.md` §3.4), and no design in its
approval (W3's `design` is NULL for the test run).

**`reproduce`** (`workspace/_reproduce.py`; U8, `data_model.md` §9 Replay, 0055) takes a result (stored, or
read from the `result` key of an export's `result.json` with `DiagnosticResult.from_json`) or a bare `Provenance`, and writes
nothing:

- the batch is the provenance's run ids, in its order (`replay_batch`, which reads Q15 with `points=True`, so a
  deleted result's runs are found, and builds the `Design`); its `Design` is built from the provenance's identity, the stored runs' points and
  replicates, and its `design_structure`, with no generator, so the replay recomputes what was computed, across
  generator versions too (0062, 0063); a row is new when its run's approval is the provenance's approval, so the
  header's counts are the original's;
- when the identity's generator and sampler versions are today's, the design is also rebuilt, as a check, and
  compared coordinate by coordinate: a linear-range coordinate within `GOLDEN_UNIT_TOL`, a log-range one within
  max(`GOLDEN_UNIT_TOL`, 32·2⁻⁵²·(1 + |ln lo| + |ln hi|)/(ln hi − ln lo)) in unit coordinates, held coordinates,
  replicates, levels, and lines' rows exactly; rows beyond go into `provenance_differences` ("design points
  differ at rows 3, 17"; or "design sizes differ", "design levels differ", "line 2's rows differ"); with
  another version, or no generator registered for the identity's kind, nothing is rebuilt, and
  `provenance_differences` names the versions; neither raises (0062, 0063). A generator's or sampler's version
  that differs is a version difference ("design generator uniform: 2 here, 1 there"); none registered is a
  sentence ("no design generator X here: the design was not rebuilt"); any exception of the lookup, the rebuild,
  or the comparison is "the design could not be rebuilt: …", `KeyboardInterrupt` passing through; rows that
  differ are named, the first 10 and a count (0080);
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
`ema_` columns), `result.json`, and a copy of the result's directory as `report/` (E1–E7), with `report.pdf` when
asked (0081).

## 8. Layer 5: the CLI and the MCP server

Presentation only (AR3): parse the input, call one workspace function, and show the `text` EMA rendered. Neither
formats a number (C54, C55; P1).

### `ema.cli`

13 commands of `scope.md`'s 15, in one module, `ema/cli.py` (0082). A global `--workspace DIR` (default
`ema_workspace`), accepted before or after the command (0082).

| Command | Calls |
|---|---|
| `ema model add PATH` | `load_model` |
| `ema model test NAME [--yes]` | `test_model` |
| `ema models [NAME]` | `list_models`, or `describe_model` |
| `ema diagnostics [NAME]` | `list_diagnostics`, or `describe_diagnostic` |
| `ema price MODEL DIAGNOSTIC [--space FILE] [--param k=v]… [--prediction P] [--retry-failed]` | `price` |
| `ema run MODEL DIAGNOSTIC [--space FILE] [--param k=v]… [--prediction P] [--retry-failed] [--yes]` | `run`; a progress line on stderr |
| `ema results [ID] [--model M] [--model-version V] [--diagnostic D] [--prediction P]` | `get_result`, or `list_results`; an ID with a filter is bad usage (0082) |
| `ema report ID [--pdf]` | `report` (0018); the Markdown on stdout exactly as the file holds it, then `Report: <path>` (and `PDF: <path>`) on stderr (0060, 0082) |
| `ema failed-runs ID` | `failed_runs` (U3) |
| `ema run-dirs ID [--point FILE]` | `run_dirs` (0020) |
| `ema reproduce ID` | `reproduce` (U8) |
| `ema export ID DIR [--pdf]` | `export` (E1; `--pdf`, 0081); prints the export's absolute directory (0082) |
| `ema mcp --root DIR` | starts the MCP server; `--root`, required and absolute (not `/`, nor inside a workspace), is the directory its path arguments may name (`trust.md`, T5, E7); a relative `--workspace` resolves against it |

- **`--space FILE`** is `designs.md`'s JSON form (U2); `--param k=v` is parsed by the diagnostic's
  `DiagnosticParameter` (a JSON value, or a bare string), as `run`'s keyword arguments are: the CLI passes the
  value as text and parses nothing, so the CLI, Python, and MCP requests get one reuse key (0082). A `--param`
  without `=`, with an empty name, given twice, or naming one of the request's own arguments (`model`,
  `diagnostic`, `space`, `prediction`, `retry_failed`, `approve`, `on_progress`, `self`; the message says where
  it goes) is bad usage. `--space FILE` and `--point FILE` are read as JSON objects, refusing a duplicate key and
  `NaN` or `Infinity`, and a point's values must be numbers; a file that can't be read, or isn't such an object,
  is bad usage, and one the workspace refuses its `RequestError` (0082).
- **Approval:** the price and the question on stderr, then `Approve? [y/N]`. `--yes` approves the price in
  advance: the approval is still priced, shown, and recorded with its question and answer (W3); the line reads
  `Approve? [y/N] y (--yes)`. With no terminal and no `--yes`, there is no answer, which is a no, recorded: the
  line reads `Approve? [y/N] no answer: no terminal, and no --yes` (0082).
- **Output:** EMA's texts on stdout, lists one item per line, with a blank line between items when any spans
  several lines; an empty list prints nothing on stdout, and a one-line note on stderr ("No models loaded.").
  The progress line on stderr is `Progress.text`, rewritten in place on a terminal, otherwise one line at each
  tenth of each phase (0082).
- **Exit codes:** 0 success; 1 an `EMAError` (a declined approval included) or an `OSError` (a workspace that
  can't be made or opened), printed "ema: <message>" on stderr; 2 bad usage, `ema` with no command, and `ema
  mcp`'s root refused at start (`PathRefused` from `open_workspace`; T5, 0061); 130 Ctrl-C, with "Stopped at
  <the last progress text>: every finished run is stored." on stderr, a text EMA wrote rather than a count the
  CLI made (P1; 0082). `ema reproduce` exits 0 whatever it finds: its text says whether the replay is
  identical.
- **`ema mcp`:** `--root` is required, absolute, and not `/` once links are resolved, checked before the lazy
  import (exit 2); without the `ema[mcp]` extra it says "ema mcp needs the ema[mcp] extra: …" and exits 2; then
  `ema.mcp.server.serve(root=, workspace=)`, a `PathRefused` from it exiting 2 (0082).
- **Not in the CLI:** `propose_model` and `save_model`, which serve an MCP client; on the command line the
  user writes the spec and runs `ema model add`.

### `ema.mcp`

Started by `ema mcp`, or `python -m ema.mcp --root DIR [--workspace DIR]` (`ema/mcp/__main__.py`, the same
root refusals (exit 2); 0081); needs the `ema[mcp]` extra, bounded `mcp>=2.2.0`, the SDK release whose API it
is written and tested against (`scope.md`; 0081). Each tool is one workspace call (0016). It speaks the
`initialize` handshake era only, where a server may ask (elicitation) while a tool call is open; a client that
probes the stateless era first falls back to it (0081). `serve(*, root, workspace="ema_workspace")` refuses a
relative root and `/` (`PathRefused`), beside `open_workspace`'s refusals (T5; 0081).

| Kind | Name | Calls |
|---|---|---|
| tool | `models(name?)` | `list_models`, or `describe_model` |
| tool | `diagnostics(name?)` | `list_diagnostics`, or `describe_diagnostic`: each parameter with its JSON schema, and `params_schema`, the whole `params` object's (C55; 0081) |
| tool | `propose_model(spec, path)` | `propose_model` |
| tool | `save_model(spec, path)` | `save_model` (it validates, then asks), its confirmation by elicitation (0049) |
| tool | `test_model(name)` | `test_model`, its approval by elicitation |
| tool | `price(model, diagnostic, space?, params?, prediction?, retry_failed?)` | `price` |
| tool | `run_diagnostic(model, diagnostic, space?, params?, prediction?, retry_failed?)` | `run`, its approval by elicitation, its progress as MCP progress notifications |
| tool | `results(id?, model?, model_version?, diagnostic?, prediction?)` | `get_result`, or `list_results`; `data` leaves out the run ids (an export holds them); an `id` with a filter is refused (0081) |
| tool | `failed_runs(id)` | `failed_runs` |
| tool | `export(id, directory, pdf?)` | `export`, only inside the directory named when the server started (E7, step 10); `pdf` adds the report's PDF (0081) |
| resource | `ema://results/{id}/report` | `report(id)`: byte-identical to the file (U9) |
| resource | `ema://results/{id}/figures/{name}.png` and `.json` | `report(id)`, then the figure's file and its data card in the result's directory |
| resource | `ema://diagnostics/{name}` | `describe_diagnostic` |

10 tools, `scope.md`'s cap (0016, 0053). Figures are resources, beside the report (record 0056).

- **The envelope:** every tool returns `{ok, data, text, see, error: {message, retryable}}`: `text` is EMA's
  rendering; `data` the returned type as strict JSON, with full ids and short ids; `see` the resources and
  tools that hold more, never advice on what to do (0017), such as "ema://results/3f2a…/report"; `error`
  from the `EMAError`, with its `retryable`. The envelope is the tool's structured content (with its output
  schema) and its one text block, its JSON; on an error `data` is null and `text` the message. `data` is a
  returned dataclass field by field without `text`, every double unchanged, and a non-finite number refused as
  EMA's failure, never written as null (P1, C55; 0081).
- **Threads:** the MCP SDK is asynchronous, and the workspace is not. The server keeps two `Workspace`s on the
  same directory, each on its own dedicated thread (a `concurrent.futures.ThreadPoolExecutor` of one worker,
  so each SQLite connection stays on one thread): one for the tools that may run or write (`save_model`,
  `test_model`, `run_diagnostic`, `export`), one for the rest and the resources, so reads and prices answer
  while a run of hours goes on (`data_model.md` §10: any number of readers). The `Approver` blocks its thread
  while the elicitation is asked on the event loop (`asyncio.run_coroutine_threadsafe`); progress is sent the
  same way. Standard library only: no new dependency beside `mcp` (`anyio`, which `server.py` imports, comes with
  `mcp`; `scope.md`).
- **Approvals and confirmations** are asked by elicitation, with the same text as the terminal's; a declined
  elicitation is a no (0016), and so is one unanswered after `ELICITATION_TIMEOUT_S` = 900 s (a named
  constant in `mcp/server.py`, chosen here), which frees
  the run lock. The form is one required boolean, `approve`, with `"default": true`, so Accept on the form
  showing the price is a yes; `approve` false, decline, cancel, a client error, a reply the SDK can't read, no
  answer in time, and a cancelled call are a no, recorded (W3; 0081).
- **Progress and cancellation:** progress notifications carry `Progress.text`, their value cumulative over the
  runs and analysis phases, at most one every `PROGRESS_INTERVAL_S` = 0.2 s but each phase's first and last. A
  call the client cancels, or one open when the client leaves or the server gets SIGTERM, is stopped through
  `run`'s `on_progress` hook, which raises `Stopped` between two runs, every finished run stored; a question it
  waits on is a no, and a queued call never starts. On a disconnect or SIGTERM, each workspace is closed on its
  own thread once its calls end (the run lock released, the model children stopped); SIGTERM then ends the
  process by the signal. A model call under way finishes, up to its timeout, and is stored (0081).
- **A client without elicitation** can't be asked, so `save_model`, `test_model`, and a run with new runs are
  refused before any question ("this client can't ask the user (it has no elicitation): …", with
  `CannotAsk`'s message; P3; 0081), and no
  approval is recorded, since none was asked (T3). Reads, prices, and repeated requests work.
- **`params`** is one JSON object, described by `diagnostics(name)` (C55); `space` is `designs.md`'s JSON form.
  An object argument sent as its JSON text is read as that object; anything else is refused naming the argument.
  `params` naming one of the tool's own arguments (`model`, `diagnostic`, `space`, `prediction`, `retry_failed`,
  `approve`, `on_progress`, `self`) is a `RequestError` saying where it goes (0081).
- **The tool descriptions and the server's instructions** are one reviewed file, `ema/mcp/tools.md` (0019).
  The instructions ask the client to quote EMA's text, give result ids, and point the user to the report,
  rather than restate numbers (P1); and, since EMA reports results without interpretation (P2), not to interpret
  unless the user asks, and then to say it is the client's own reading, not EMA's, kept apart from what it
  quotes (0081). The server refuses to start when a tool or argument it serves has no description there, or
  `tools.md` describes one it doesn't serve (C55, 0019; 0081).
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
| `Store` | `tests/contracts/store.py` | C46–C52, C56; I1–I12 | the `Store` class, its broken toys subclasses (0072) |
| the runner | `tests/contracts/runner.py` | its parts of C34, C37, C41, C46–C49, C56 | `ema.runner` over a store and the toy models (`tests/models`), millisecond models for C47–C49 (the cap counted at a call's start, an interrupt); its broken toys subclasses of its private loop (0074) |
| `Workspace` and CLI | `tests/contracts/workspace.py` | C53, C54 | the use cases U1–U9 and get started's examples (slow tier; 0060), and every CLI command against its workspace function |
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
exclude_type_checking_imports = true       # collect names ExecutedCall under TYPE_CHECKING only (0071)

[[tool.importlinter.contracts]]
name = "AR1 One-way layers"
type = "layers"
layers = [
    "ema.cli",
    "ema.mcp",
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
name = "AR3 The CLI calls only the workspace"
type = "forbidden"
allow_indirect_imports = true
source_modules = ["ema.cli"]
forbidden_modules = ["ema.numerics", "ema.designs", "ema.models", "ema.store", "ema.plotting",
                     "ema.report", "ema.runner", "ema.approval", "ema.diagnostics", "ema.reference_models",
                     "numpy", "scipy", "matplotlib"]

[[tool.importlinter.contracts]]
name = "AR3 The MCP server calls only the workspace"       # 0081
type = "forbidden"
allow_indirect_imports = true
source_modules = ["ema.mcp"]
forbidden_modules = ["ema.numerics", "ema.designs", "ema.models", "ema.store", "ema.plotting",
                     "ema.report", "ema.runner", "ema.approval", "ema.diagnostics", "ema.reference_models",
                     "numpy", "scipy", "matplotlib", "ema.cli"]

[[tool.importlinter.contracts]]
name = "AR4 Only the runner runs a model"
type = "forbidden"
allow_indirect_imports = true
# every module of ema.models but execute itself is a source (0071)
source_modules = ["ema.types", "ema.numerics", "ema.designs", "ema.models.spec", "ema.models.files",
                  "ema.models.collect", "ema.models.prepare", "ema.models.parsers", "ema.models.processes",
                  "ema.models.sandbox", "ema.models._worker", "ema.store", "ema.plotting", "ema.report",
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
  AR3's two contracts forbid `numpy`, `scipy`, and `matplotlib` as direct imports only, so an interface can
  compute no number itself (P1; 0081).
- **Type-checking imports** are left out (`exclude_type_checking_imports`): an import under `TYPE_CHECKING`
  never runs, so `collect`'s of `ExecutedCall` is not one, and a run-time import of `execute` breaks AR4 (0071).
- **External packages** are named at their top level only (`google`, not `google.genai`), as grimp keeps them.
- **Standard-library modules** (AR2, AR5): import-linter sees them as external packages (checked at step 12
  with import-linter 2.15, 0059), so no AST test checks these lists; the first build step's AR2 contract
  confirms it on EMA's own code.
- **`ema.experimental`:** none in v2.0 (0017). P2's contract (nothing in layers 0–3 imports it) is added here
  with the package.
- **One AST test** in the fast tier checks what import-linter can't express: AR7 (no module imports the root
  `ema`), that `ema.cli` imports `ema.mcp` only inside its `mcp` command (AR3, 0061), and that
  `ema/models/__init__.py` doesn't import `execute`, so AR4 can't be bypassed through the
  package's re-exports.
- **No vector-vector BLAS** (§1; P4; 0068): Ruff's banned-api rule (TID251) refuses, in `src/ema` (not
  `tests/`), `numpy.linalg.norm`, `numpy.dot`, `numpy.inner`, `numpy.vdot`, `numpy.vecdot`,
  `numpy.linalg.vecdot`, `numpy.tensordot`, `numpy.linalg.tensordot`, `numpy.linalg.multi_dot`, `numpy.einsum`,
  `numpy.matmul`, `numpy.linalg.matmul`, `operator.matmul`, `numpy.cov`, `numpy.corrcoef`,
  `scipy.stats.pearsonr`, and `scipy.stats.linregress`; a fast-tier AST test
  (`tests/unit/numerics/test_determinism.py`) refuses what Ruff can't see: `.dot(` calls, `__matmul__` and its
  kin, and `@` outside `_vector.matvec` (`MATMUL_ALLOWED`). Neither sees a library's internals: the diagnostic
  contract's C7 checks each whole compute for identical bytes at memory offsets.
- `uv run lint-imports` runs in the fast tier (CLAUDE.md's fast-tier command, 0059).

## 11. Size

Source lines per package against `scope.md`'s 11,000 (0084: raised from 8,300 by the owner, 2026-10-02), measured
on `demo` at the end of the demo build (step 17), after every step's review fixes: code lines, without docstrings,
comments, or blank lines, the same counter for every package. They replace 0064's estimates (8,200 against 8,300);
most of the difference is validation the reviews asked for, not features (0084).

| Package | Lines | Main parts |
|---|---|---|
| `ema.types` | 2,167 | the model spec's reader, each field named in its refusals, and `trust.md`'s checks (0069); the run and result types' strict reading, the store's columns, and the cross-checks (0070); `identity.py`; values as doubles, `DesignStructure`, `duration()`'s rule (0061–0063) |
| `ema.numerics` | 390 | the basis (ported), fits and PRESS, the bootstrap, the Gram spectrum; `_vector` (0068); the column-wise statistics (0076) |
| `ema.designs` | 586 | the `random` sampler, six generators; convergent's exact sizes (0067); `lines_through_anchor` (0073) |
| `ema.models` | 1,363 | the sandbox and worker (ported, without v1's limits and withheld variables), the environment and path checks, the three phases, parsers, `ModelProcesses`; Ctrl-C held while a process starts, exits seen without reaping, the reply checked again in EMA (0071) |
| `ema.store` | 1,235 | `data_model.md` §10; W5's checks, the result directory's swap, `current_keys` (0072) |
| `ema.plotting`, `ema.report` | 708 | the drawing helpers the diagnostics share (0073); escaping text EMA didn't write; the PDF |
| `ema.runner`, `ema.approval`, the root's `__init__` | about 488 | the questions' rendering (`trust.md`; 0074); the root's lazy re-exports (0080) |
| `ema.diagnostics` | 2,282 | base and precheck, with the readers and the request, identity, and provenance helpers (0075); the six; `_lines.py`, `_fits.py` |
| `ema.workspace` | 915 | the evaluation's order; export (E1–E7); reproduce (0062, 0063); the root's checks and the thread guard (0080) |
| `ema.cli`, `ema.mcp` | 823 | the CLI (0082); the server, its SIGTERM handling and reply relay (0081) |
| **Total** | **10,957** | 43 under the budget of 11,000 (0084) |

- **Reference models ship with `ema`,** in `ema/reference_models/` (each a model spec with its function or
  program), counted against their own 1,000 lines, not the 11,000 (82 lines of Python, 0084). The get-started
  guide and the use cases' "Done when" tests load them from an installed EMA; `ema.reference_models.path(id)`
  gives one's model spec (its `model.json`; 0060), and `space(id)` the space of its expected answers (its
  `space.json`; 0075).
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
| vector-vector BLAS (P4) | none in `ema`: `_vector`'s `dot`, `norm`, `matvec`; TID251 and an AST test | 0068 |
| AR3's contracts | one per interface; no `numpy`, `scipy`, `matplotlib`, or reference models in either | 0081, 0082 |
| the size budget | 11,000; §11's rows the measured counts | 0084 |

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
- **Guides (step 13):** done (`../guides/`, 0060): each guide walked through against §7; no new workspace
  function; §8's `ema report` and §11's `path(id)` changed.
