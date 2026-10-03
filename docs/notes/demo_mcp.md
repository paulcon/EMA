# Demo: EMA through an MCP client

> A note for the demo (step 15; record 0081), not a spec. It sets up a demo directory, registers EMA's MCP server
> with Claude Code or Claude Desktop, and gives a five-minute script of prompts. Rehearsed on 2026-10-02 with the
> step's worktree in place of the repository: §1's shell commands as written, and the tool calls behind each of §3's
> prompts over a real stdio subprocess, answering every form yes. Not rehearsed: the `claude` and Claude Desktop
> steps (they change the client's configuration) and the `ema` CLI forms (step 16, merged in parallel). Checked
> again after review round 1 (record 0081, Review round 1) on a scratch copy of §1's layout: `ema mcp --root`
> answers `initialize` and lists 10 tools; a scripted client loads `ishigami/model.json` as is with `save_model`
> (the file unchanged), prices and runs a scatter, accepting each form with its default, and reads the report.

## 1. Before the demo (10 minutes, once)

The repository is `/Users/paulconstantine/PycharmProjects/EMA`, with step 15 (and the CLI, step 16) merged on the
branch it has checked out. Sync it once, so the server doesn't install anything while the client waits for it:

```bash
EMA=/Users/paulconstantine/PycharmProjects/EMA
cd "$EMA" && uv sync
```

### The demo directory (the server's root)

The root is the one directory the tools' path arguments may name (T5); the workspace, `ema_workspace`, is created
inside it on first start. Copy three reference models into it, and the beam model: a function and its model spec,
written by hand (a model spec is the user's to write; drafting one is for later):

```bash
DEMO=/Users/paulconstantine/ema_demo
mkdir -p "$DEMO/beam"
cp -R "$EMA/src/ema/reference_models/r2" "$DEMO/ishigami"     # the Ishigami function: x1, x2, x3 in [-pi, pi]
cp -R "$EMA/src/ema/reference_models/r3" "$DEMO/borehole"     # the borehole function: 8 parameters with units
cp -R "$EMA/src/ema/reference_models/r5" "$DEMO/r5"           # fails in known regions (failed runs)
cp "$EMA/docs/notes/demo/beam.py" "$EMA/docs/notes/demo/beam.json" "$DEMO/beam/"   # a cantilever's tip deflection
sed -i '' 's/"name": "r3"/"name": "borehole"/' "$DEMO/borehole/model.json"
rm -rf "${DEMO:?}"/*/__pycache__
```

Load the four model specs into the workspace (loading asks nothing and runs nothing). Through Python, now:

```bash
cd "$DEMO" && uv run --project "$EMA" python -c "
import ema
with ema.open_workspace('ema_workspace', root='$DEMO') as ws:
    for spec in ('ishigami/model.json', 'borehole/model.json', 'r5/model.json', 'beam/beam.json'):
        print(ws.load_model(spec))
"
```

or, with the CLI merged: `cd "$DEMO" && uv run --project "$EMA" ema model add ishigami/model.json` (and the other
three). The layout is then:

```text
/Users/paulconstantine/ema_demo/
├── beam/      beam.json  beam.py            # a cantilever beam: f(P, L, E), the tip deflection in mm
├── borehole/  model.json  borehole.py  space.json
├── ishigami/  model.json  ishigami.py  space.json
├── r5/        model.json  r5.py        space.json
├── ema_workspace/            # EMA's: ema.db, runs/, results/, files/
└── archive/                  # earlier workspaces and exports, moved here by reset_demo.sh
```

To start the demo again from nothing, delete `ema_workspace/` and `exports/`, and load the four specs again; or run
`docs/notes/demo/reset_demo.sh`, which moves the two to `archive/` with a timestamp (`--delete` deletes them), loads
the four specs, and refuses while a server or Python session has the workspace open.

### Check the server by hand

Either command starts the server over stdio; each prints one JSON line (the `initialize` answer) and exits when its
input ends:

```bash
INIT='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"t","version":"0"}}}'
echo "$INIT" | uv run --project "$EMA" python -m ema.mcp --root "$DEMO"
echo "$INIT" | uv run --project "$EMA" ema mcp --root "$DEMO"            # with the CLI merged
```

A refused root (relative, `/`, or inside a workspace) prints the reason on stderr and exits 2.

## 2. Register the server

### Claude Code

From the demo directory (the default scope, `local`, ties the server to this directory):

```bash
cd /Users/paulconstantine/ema_demo
claude mcp add ema -- uv run --project /Users/paulconstantine/PycharmProjects/EMA python -m ema.mcp --root /Users/paulconstantine/ema_demo
# or, with the CLI merged:
claude mcp add ema -- uv run --project /Users/paulconstantine/PycharmProjects/EMA ema mcp --root /Users/paulconstantine/ema_demo
claude mcp list          # ema: ... ✓ Connected
claude                   # then /mcp shows ema, with 10 tools
```

(`claude mcp remove ema` undoes it.) Claude Code asks permission before each MCP tool's first use; answer "Yes, and
don't ask again" for the read tools (`models`, `diagnostics`, `price`, `results`) to keep the demo moving. That
permission is the client's; EMA's own approval of new runs comes separately, as a form the user answers
(elicitation), with the price.

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (Settings → Developer → Edit Config), then
restart Claude Desktop. A GUI app doesn't see the shell's `PATH`, so `uv` is named by its full path:

```json
{
  "mcpServers": {
    "ema": {
      "command": "/Users/paulconstantine/.local/bin/uv",
      "args": ["run", "--project", "/Users/paulconstantine/PycharmProjects/EMA",
               "python", "-m", "ema.mcp", "--root", "/Users/paulconstantine/ema_demo"]
    }
  }
}
```

With the CLI merged, `"args"` may instead be `["run", "--project", "/Users/paulconstantine/PycharmProjects/EMA",
"ema", "mcp", "--root", "/Users/paulconstantine/ema_demo"]`.

## 3. The five-minute script

Say what EMA is while the first answer comes: EMA runs diagnostics on a computational model and reports figures,
numbers, and their intervals; every number comes from stored runs (P1), and nothing runs without the user's yes, with
its price (P3).

**The form.** Each yes EMA needs comes as a form from the client (an elicitation), not as a chat message: its text
is EMA's question (the model version, the price "N new runs, M reused, time …", and, on a model version's first
approval, what each run starts; for `save_model`, the absolute path and the spec's full text), and it has one field,
a checkbox **Approve**, already checked. **Accept** approves (record 0081 items 6 and 18); **Decline** or
**Cancel**, unchecking Approve before Accept, or no answer within 15 minutes is a no, and nothing runs. Every
answer is recorded with its question.

The prompts, in order (the tools each one calls are in brackets):

1. **"Which models does EMA have loaded?"** [`models`] Four: beam, borehole, ishigami, r5, each with its model
   version.
2. **"Describe the borehole model."** [`models(name)`] Its 8 model parameters with units, nominal values, and limits,
   and its model prediction, water flow in m³/yr.
3. **"What diagnostics does EMA have? Describe the point run and scatter, with their parameters."** [`diagnostics`,
   `diagnostics(name)`] Each parameter with its type, default, and meaning; `data.params_schema` is the JSON schema.
4. **"Run a point run of the borehole model at its nominal point."** [`run_diagnostic`] A form appears: the price
   ("5 new runs, 0 reused, time unknown") and, since it is this model version's first approval, what each run starts
   (the function, the interpreter, the files, the environment). Approve. "Diagnostic result f520: point_run on
   borehole@d17b114da037, y; 5 runs: 5 new, …"; its report holds the value and whether the repeated runs vary.
5. **"Price a scatter of the Ishigami model over x1, x2, and x3 in [-π, π], with n = 200 and seed 1."** [`price`]
   "200 new runs, 0 reused, time unknown" (no Ishigami run is stored yet to time it): asked of nobody, nothing run.
6. **"Run it."** [`run_diagnostic`] The form with the same price, and what each run starts; approve; progress shows
   "…/200 runs", then "bootstrap: … of 1000 resamples". The answer quotes EMA's line: "Diagnostic result 6f6b:
   scatter on ishigami@57ed926c2e1a, y; 200 runs: 200 new, 0 reused, 0 failed; report: ema report 6f6b".
7. **"Show me the report."** [the resource `ema://results/{id}/report`] The Markdown report, byte for byte the file
   in `ema_workspace/results/{id}/report.md`: per-parameter estimates with intervals, notes, figures.
8. **"Show me the scatter of y against x1."** [the resource `ema://results/{id}/figures/scatter_x1.png`] The figure;
   its numbers are in `scatter_x1.json`, the data card.
9. **"Run exactly the same scatter again."** [`run_diagnostic`] No form: the same request reuses the stored result,
   the same id, nothing run (C50). EMA's line says so first: "Diagnostic result 6f6b: the stored result of the
   same request; no new runs, nothing asked. As made: …; 200 runs: 200 new, …", the counts of the evaluation that
   made it.

If there is time:

10. **"Run a point run of the beam model, then a scatter of its deflection over P in [500, 1500], L in [1, 3], and
    E in [150, 250], with n = 100 and seed 1."** [`run_diagnostic`] Beam's first approval shows what each run starts
    (`beam.py:f`, the interpreter); the point run gives "deflection" at P = 1000 N, L = 2 m, E = 200 GPa (3.2 mm);
    the scatter's report shows the model parameters with their units (N, m, GPa) and the deflection in mm.
11. **"Run a scatter of r5's y over a and b in [-1, 1] with n = 100, then list the failed runs."**
    [`run_diagnostic`, `failed_runs`] "100 runs: 100 new, 0 reused, 16 failed"; each failed run with its kind and
    reason ("failed (timeout): timeout after 0.2 s", "failed (error): ValueError: no convergence at r5.py:13") and
    its stderr's last lines, quoted as the model's own output. (r5 has two model predictions: name one.)
12. **"Export the Ishigami scatter, with a PDF of its report, to exports/ishigami_scatter."** [`export`, with
    `pdf`] "Exported to …/exports/ishigami_scatter: runs.csv, result.json, report/ (with report.pdf)", inside the
    root only (a path outside it is refused, E7); the PDF takes a few seconds (pandoc and lualatex). Open it with
    `open exports/ishigami_scatter/report/report.pdf` (in Claude Code, ask it to, or type it with the `!` prefix).

**Viewing a report's Markdown with its figures:** the figures are PNGs beside `report.md`, linked by relative
paths. A plain editor shows the text only; use a Markdown preview: in PyCharm, the preview mode (the "Preview" or
"Editor and Preview" buttons at the top right of the editor); in VS Code, "Open Preview" (⇧⌘V); or make an HTML page
that holds its figures: `pandoc report.md -s --embed-resources -o report.html && open report.html`.

## 4. If something goes wrong

- **"this client can't ask the user (it has no elicitation)":** the client didn't declare elicitation, so EMA
  refuses new runs and saving, asking nothing. Plan B: make the same requests once in Python (or the CLI), answering
  the questions in the terminal; then the same prompts through MCP reuse the stored results and ask nothing (C50):

  ```bash
  cd "$DEMO" && uv run --project "$EMA" python -c "
  import math, ema
  pi = [-math.pi, math.pi]
  with ema.open_workspace('ema_workspace', root='$DEMO') as ws:
      print(ws.run('borehole', 'point_run', approve=ema.ask))
      print(ws.run('ishigami', 'scatter', {'x1': pi, 'x2': pi, 'x3': pi}, n=200, seed=1, approve=ema.ask))
  "
  ```

  The MCP request must then be the same: the space as `[-3.141592653589793, 3.141592653589793]`, n 200, seed 1.
- **The form never appears and the call ends in "declined":** a form unanswered for `ELICITATION_TIMEOUT_S` = 900 s
  is a no; so is a client that times the tool call out first. Claude Code's limits are environment variables:
  `MCP_TIMEOUT` (the server's start, in ms) and `MCP_TOOL_TIMEOUT` (a tool call, in ms), set before `claude`.
- **The server doesn't connect:** run the hand check in §1; its stderr says why (a root refused, a missing `uv sync`).
  `claude --debug` shows the server's stderr.
- **"another process is making runs" (`WorkspaceBusy`):** a Python session or a second client holds the run lock;
  close it.
