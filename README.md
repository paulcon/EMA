# EMA

EMA (Exploratory Model Analysis) runs diagnostics on computational models to find exploitable structure (which
model parameters matter, whether the model prediction is close to linear or to a low-degree polynomial, how it
varies along lines through the model parameter space), and reports the results with figures, numbers, and their
variability intervals.

A model is a Python function or a command-line simulation code, described by a model spec (a JSON file). Every
number EMA reports is computed from stored runs, every result records how it was made, and no run starts without
your yes to its price.

**Status:** pre-release (`2.0.0.dev1`). Stored formats and interfaces may still change.

## Requirements

- Python 3.13 or newer, and [uv](https://docs.astral.sh/uv/).
- Optional, for PDF reports: pandoc and a LaTeX with lualatex. Everything else works without them.

## Installation

The repository is private: installing needs read access (a GitHub login, or a token).

**As a tool**, to use EMA. This puts `ema` on your `PATH`, with the MCP server:

```bash
uv tool install "ema[mcp] @ git+https://github.com/paulcon/EMA"
ema --help
```

A Python model runs in EMA's own interpreter, so its imports must be installed there:
`uv tool install --with <package> …`.

**From a clone**, to develop EMA (`CONTRIBUTING.md`):

```bash
git clone https://github.com/paulcon/EMA.git && cd EMA
uv sync --extra mcp
uv run ema --help
```

From a clone, write `uv run --project /path/to/EMA ema` wherever this README writes `ema`.

### The MCP server

`ema mcp --root DIR` serves EMA's tools to an MCP client over stdio. `DIR` is the one directory the tools may
read or write; the workspace, `DIR/ema_workspace`, is made on first start. Register it with your client:

**Claude Code:**

```bash
claude mcp add ema -- ema mcp --root /path/to/study
claude mcp list                     # ema: … ✓ Connected
```

**Claude Desktop:** in Settings → Developer → Edit Config, add the server, then restart Claude Desktop. A desktop
app doesn't see your shell's `PATH`, so give `ema`'s full path (`which ema`):

```json
{
  "mcpServers": {
    "ema": {"command": "/Users/you/.local/bin/ema", "args": ["mcp", "--root", "/path/to/study"]}
  }
}
```

Each new run needs your yes: the client shows EMA's question, with the price, as a form (an elicitation), and
nothing runs until you approve it.

## Get started

The examples use a cantilever beam's tip deflection: a Python function, `beam.py`, and its model spec,
`beam.json`, both in `docs/notes/demo/`. Copy them into a study directory, and write the model parameter space
to sample:

```bash
mkdir -p study/beam && cd study
cp /path/to/EMA/docs/notes/demo/beam.py /path/to/EMA/docs/notes/demo/beam.json beam/
echo '{"P": [500, 1500], "L": [1, 3], "E": [190, 210]}' > beam/space.json
```

### With the CLI

Load the model, and list the models and the diagnostics:

```text
$ ema model add beam/beam.json
Loaded beam@48ad64499892: 3 model parameters (P, L, E), 1 model prediction (deflection)

$ ema models
beam@48ad64499892: 3 model parameters (P, L, E), 1 model prediction (deflection); spec /…/study/beam/beam.json

$ ema diagnostics
coordinate_lines: the model prediction along one line per varied model parameter through an anchor, and its spectrum
  …
point_run: the model prediction at one point, and its variation over repeated runs there
  …
scatter: the model prediction against each varied model parameter, over a uniform design: …
  space: model parameter space, required
  prediction: model prediction name, default the only one
  n: integer ≥ 1, default 200; the number of points.
  …
```

Run a scatter of 200 points. EMA shows the price and, on the model's first approval, what each run starts, and
waits for your yes:

```text
$ ema run beam scatter --space beam/space.json --param n=200
New runs of the model version `beam@48ad64499892`: scatter on `deflection`.
Price: 200 new runs, 0 reused, time unknown

The model version's first approval: what each run starts.
Function: `beam.py:f`
Interpreter: `/…/bin/python`
Files in each run directory: none.
Environment: EMA's base variables only.
Approve? [y/N] y
…
Diagnostic result 27b1: scatter on beam@48ad64499892, deflection; 200 runs: 200 new, 0 reused, 0 failed; report: ema report 27b1

$ ema report 27b1
# Scatter: beam, deflection
…
| Model parameter | Rank correlation ρ | Variability interval |
|---|---|---|
| P | 0.3028 | [0.1347, 0.4586] |
| L | 0.927 | [0.8929, 0.9475] |
| E | -0.08496 | [-0.2543, 0.09211] |
…
```

The workspace is `ema_workspace/` in the current directory (`--workspace DIR` for another); the report, its
figures, and every run are stored there. `ema --help` lists the other commands (`price`, `results`, `failed-runs`,
`reproduce`, `export`, …).

### With an MCP client

Start from the study directory above, with the server registered with `--root` set to it. Load the model once
from the CLI (`ema model add beam/beam.json`, run in the study directory), then ask the client:

- "Which models does EMA have loaded?"
- "What diagnostics does EMA have?"
- "Run a scatter of the beam model's deflection over P in [500, 1500], L in [1, 3], and E in [190, 210], with
  n = 200." A form shows the price and what each run starts; approve it.
- "Show me the report."

The answers quote EMA's own text: the same lines as the CLI, and the report as stored.

## Documentation

- `docs/guides/`: get started (in Python), add a model, run a diagnostic, add a diagnostic. Outlines for now.
- `docs/design/`: the specs. Start with `purpose.md` and `glossary.md`; `model_interface.md` says how to write
  a model spec, and `diagnostics/` describes each diagnostic and its report.
- The guides and the API reference, as a site: https://paulcon.github.io/EMA/. To build it locally:
  `uv run sphinx-build docs docs/_build/html`, then open `docs/_build/html/index.html`.
- `STATUS.md`: where the project stands.

## Contributing

How the project is organized (specs, decision records, plans, ids) and how a change gets in: `CONTRIBUTING.md`.

## License

MIT (`LICENSE`).
