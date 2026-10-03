# Trust boundary

**Status:** accepted (TODO step 10; 0057). **Updated:** 2026-10-02 (0061: `remove_tree`, the root's check, "user"; 0069, 0071, 0073, 0074, 0080, 0081: credentials
files on every spec path, the group killed at a program's exit, T10's reader, Ctrl-C at the question, T6's same spec,
the function's signature at loading; review round 1 of applying 0066–0085); 2026-10-03 (0086 item 1). **Depends on:** P3; AR1–AR4, AR6; records 0010, 0016, 0018,
0019, 0020, 0022, 0025, 0026, 0028, 0029, 0030, 0049, 0050, 0053, 0054, 0056, 0086 (OD-7 and OD-11 are decided);
`model_interface.md` (M2, M9, M13–M15, M17, M20), `contracts.md` (C32, C33, C38, C39), `data_model.md` (W1, W2,
W3, Q12, the run lock), `architecture.md` (§3, §5–§8), `export.md` (E1, E4, E7), `use_cases.md` (U2, U6, U9),
`diagnostics/shared.md` (the notes), `scope.md`; C50, I4.

> What EMA trusts, what it doesn't, and the rules at each crossing. Written from TODO step 10, the
> consistency review's "Step 10 inputs", and the asks of `architecture.md`, `model_interface.md`, `export.md`,
> `data_model.md`, and `use_cases.md`, then checked by an independent review. v1's rules are in its
> `src/ema/agent/approval.py` and `core/models/_sandbox.py` (read, not copied: `scope.md` says rewrite the
> first and port the second after re-review).

## Who is trusted

| Party | Trusted? | What follows |
|---|---|---|
| **The user** | yes | They write model specs and models, and answer every approval and confirmation. EMA asks them before it runs anything new or saves a spec it didn't write itself (P3). |
| **The model** (the user's function, or a simulation code they chose) | as far as the user trusts it | It runs outside EMA's process, with stdin from `/dev/null`, a timeout, and only the environment below. It is **not sandboxed:** it runs as the user, so it can read and write their files and use the network, as it would from their shell. Code the user doesn't trust belongs in a container or a virtual machine, with EMA's command-line interface around it. |
| **An MCP client's agent** | no | It may be mistaken, or misled by text it read (a file, a model's output, a web page). It can read what the workspace holds, price, propose a model spec, and export; its path arguments are confined to the root named at `ema mcp` start, outside any workspace; it can't run a model or save a spec without the user's yes, and can't answer for the user (0016). |
| **The MCP client application** | to show each elicitation to the user | EMA can't tell who answered an elicitation. A client that answers by itself, or approves everything, is outside what EMA can check; EMA's own rules (what is asked, what is confined) hold either way. |

EMA has no secrets of its own: no module in `ema` uses an LLM SDK (AR6) or an API key, and EMA never reads
`.env`. What it guards is the user's environment and files, from accidents in a model and from an agent's
mistakes.

**What an agent's spec can do.** The agent writes no code file that EMA runs (0016), but a model spec it drafts
says what runs: its `command` may be `["sh", "-c", "…"]` (`model_interface.md`), and its `env` may set `PATH`.
The guard there is the user reading the spec: its full text in the confirmation, and the command, the
program's path, and the environment again in the model version's first approval. The checks below
(credentials files, credential-like names, hidden characters) cover what a spec names and how it is shown;
they don't read a command's arguments.

## What needs the user's yes

| Action | What is shown | Asked by | Recorded |
|---|---|---|---|
| **New runs** of a diagnostic evaluation (failed runs retried included, 0010) | the model version and the price (P3; no budgets, 0050). The first approval for a model version also shows what will run: the command and its program's resolved path, or a Python function's `function` (file and name) and the child's interpreter (0029), the input deck templates, the files, and the environment the spec sets (each `env` variable with its value, and each `pass_env` name with "set" or "not set", never its value) | Python: `approve=`. CLI: the question on stderr, then `Approve? [y/N]`; `--yes` answers yes in advance, still shown and recorded. MCP: an elicitation with the same text (0016) | `approvals`, `approval_points` (W3) |
| **The test run** (0049) | the same | the same | the same, with no design |
| **Saving a model spec an MCP client drafted** (a confirmation, 0049) | the absolute path it will be written to; what the model's name means now, when it is already loaded ("`heat` now means heat@b204… at /old/dir; saving makes it mean this spec", 0054); and the spec's full text, byte for byte as it will be written (or, for a file at the path already holding the same spec, as the file holds it; T6) | Python: `confirm=`. MCP: an elicitation. Not in the CLI, where the user writes the spec | `confirmations` (W2) |

- **Not asked:** loading a model spec (it runs nothing; the first approval shows what will run), prices,
  reads, reports and PDFs, export (it writes data only, into a new or empty directory, E1; through MCP, only
  inside the root and outside any workspace), and a repeated request, which makes no new runs (C50).
- **No answer is a no:** a declined or unanswered question (end of input; an elicitation unanswered after
  `ELICITATION_TIMEOUT_S`), and an exception raised by the approver. Nothing runs and nothing is saved.
  Ctrl-C at the question is recorded as a no, and then stops the call (T3: the user saw the question; 0074).
- **Nobody to ask:** `approve=None` or `confirm=None` (an MCP client without elicitation) refuses at once,
  asks nothing, and records nothing, since nothing was asked (`architecture.md` §7, §8).
- **The price shown is the price run:** the run lock is held from resolving the design again through the last
  new run, the wait for the answer included (`architecture.md` §7, step 6; `data_model.md` §10), so no other
  process's runs change what was approved; the approval covers only its points, once each (I4).
- **Dropped from the template:** "saving a file that becomes code" (0016; above, what an agent's spec can do).

## Running a model

One mechanism for every model, so no path runs a model any other way (AR4: only `ema.runner` imports the
execute phase):

- **A command-line model** runs without a shell, in its own process group, with the run directory as its
  working directory, stdin from `/dev/null`, and the environment below; a timeout, Ctrl-C, or the program's
  exit kills the group, so nothing it left running writes to its run directory after collect (M2, M20, C39;
  0071).
- **A Python function** runs in an isolated child, one per model version, in its own process group, started on
  EMA's own interpreter (`sys.executable`) with the environment below and stdin from `/dev/null`. The worker
  is started by its file's path; before it imports anything of `ema`'s or the model's, it replaces its
  `sys.path` with EMA's, each entry made absolute against EMA's working directory (a notebook's `''`
  included), the model's directory first, received over its own pipe (not through a variable, T2), so the
  function imports what EMA can without `PYTHONPATH`, and can't import EMA's modules by their bare names. A
  `PYTHONPATH` in `env` or `pass_env` doesn't change a function's imports, since its `sys.path` is replaced.
  Each call has the run directory (or batch directory) as its working directory, and a timeout. A timeout, a
  crash, or Ctrl-C kills the child's process group, so a solver the function started goes too, and the next call
  starts a new child (M9, 0026). `sandbox.py` and `_worker.py` are ported from v1 after re-review, without
  v1's memory and CPU limits and without its list of withheld variables.
- **What the child sends back** is JSON, and arrays in NumPy's format read with `allow_pickle=False`; never
  pickle (M9, C38).
- **A model's streams never reach EMA's own stdout,** which is the MCP server's protocol channel: a call's go
  to `stdout.txt` and `stderr.txt` in its directory; what the child writes outside a call (at import, or
  between calls) goes to EMA's stderr.
- **Model output is read from files inside the run directory only** (M13): an output parser's `file`, and
  `predictions.json`, are opened only when their resolved path lies inside the run directory; a link out of it
  makes the model prediction missing, with the reason "plate.out: outside the run directory" (0030).
- **EMA's own files in a run or batch directory** (`run.json`, and `predictions.json` after a call) are
  written without following links: a link or file the model left at that name is removed first, then the
  file is created exclusively; if that fails (the model made it again, or left a directory there), the
  run fails, kind `error`, with the reason "run.json: couldn't be written: …". EMA's own names (`point.json`, `run.json`, `predictions.json`,
  `stdout.txt`, `stderr.txt`) are refused at loading as a deck's `writes` or a listed file.
- **Run and batch directories are deleted without following links** (those `keep` doesn't keep, and a stopped
  run's): a link in them is removed, never its target, so a data directory a script linked there survives.
- **Loading never runs a model:** `load_spec` and `propose_model` read the function's file as text; the check
  for unlisted local imports (M17) parses it (`ast.parse`) and resolves module names to paths against the model's
  directory (0069 item 34), and the check that the function takes the model parameters by name reads its `def`
  from the same parse (`model_interface.md`, Names; 0081 item 29); neither imports it or a package it names, so
  nothing of the model runs in EMA's process, with EMA's full environment.
- **EMA never runs anything from a kept run directory,** and never changes one after its run (0020).
- **Shared copies** (`<workspace>/files/<sha256>/<name>`) are written read-only (0030, M15). This guards
  against accidents; a model that changes the permissions back can still write to its copy.

## The environment a model gets

A model's environment is built from three parts, the same for both kinds of model, and nothing else; EMA adds
no variable of its own (no run id, no replicate number: `model_interface.md`):

1. **The base:** these variables, when EMA's own environment has them: `PATH`, `HOME`, `USER`, `LOGNAME`,
   `SHELL`, `TMPDIR`, `TZ`, `LANG`, every `LC_*`, `LD_LIBRARY_PATH`, and `DYLD_LIBRARY_PATH`. A named
   constant, `BASE_ENV`, in `ema.models.sandbox`. (macOS drops `DYLD_*` variables when it starts a protected
   program such as `/bin/sh`; the add-a-model guide says so.)
2. **`pass_env`:** a list in the model spec of further variable names to pass from EMA's environment, with the
   values they have there (a license server, `LM_LICENSE_FILE`; a module system's variables). The names are
   part of the model version; the values are not, as a program found on `PATH` is not (0029). A name in
   `BASE_ENV` changes nothing.
3. **`env`:** the spec's literal variables (`OMP_NUM_THREADS`), part of the model version (0029). They take
   precedence over the base. A name in both `env` and `pass_env` is refused at loading.

A Python function's child gets its environment when it starts, so a variable a library reads when it loads
(`OMP_NUM_THREADS` for NumPy's threads) takes effect.

- **Why an allowlist:** EMA's environment is whatever the user's shell, or the MCP client that started
  `ema mcp`, put there, and it may hold API keys (from a `.env` file loaded by another tool, or a client's
  configuration). Passing only named variables keeps every other one from a model, whatever its name, with
  no need to read `.env` (M2). This is the scheme tox uses for test environments: a fixed base, `pass_env`,
  and `set_env`.
- **Credential-like names are refused** at loading, in `env` and `pass_env`, naming the variable: a name with a
  part, split at `_` and case-folded, in `CREDENTIAL_WORDS` (`key`, `apikey`, `token`, `secret`, `password`,
  `passwd`, `passphrase`, `credential`, `credentials`, `auth`): `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`,
  `AWS_SECRET_ACCESS_KEY`, `SSH_AUTH_SOCK`. This catches the common names, not every secret (`PGPASSWORD`,
  `DATABASE_URL` pass it): it stops an obvious mistake, and the user reads the rest. A model that needs a
  credential reads the tool's own credentials file, as it would outside EMA.
- **Values:** an `env` value is not checked. It is part of the model version, so it is stored, shown in
  approvals, exported with a result's spec, and returned to an MCP client; a guess at secret-shaped values
  would refuse ordinary paths and hosts, so the add-a-model guide says not to put a secret there. EMA never
  shows or stores a `pass_env` value itself; what the model writes to its streams is the model's output.
- **The program** is resolved against the model's own `PATH` (an `env` that sets `PATH` included), the same
  for `resolve_program`, the first approval, and `execute`. An empty or relative entry in a `PATH` would be
  resolved by `execute` against the run directory, and could run a program the model left there: in an
  `env` `PATH` it is refused at loading, naming it, with a reminder that values are literal (no `$PATH`, no
  `~`); from the base `PATH`, taken from EMA's environment (a trailing `:` in a shell's is common),
  `model_environment` drops it, so the model gets the spec's `env` exactly.
- **Names:** an `env` or `pass_env` name must be a variable name (`[A-Za-z_][A-Za-z0-9_]*`), or is refused at
  loading.

## Paths

- **Compared as files, never as strings** (T1): `ema.models.files.same_file` uses `os.path.samefile` when both
  exist. Otherwise it compares the paths resolved through their links and normalized (`os.path.normpath`, then
  Unicode NFC), case-folded only when the file system of the nearest existing parent is case-insensitive,
  which is found by probing it. P3 and C33 require it. "Inside a directory" means that the resolved path, or
  its nearest existing parent, is the directory or has it as an ancestor, compared as files.
- **Paths in a model spec** (the Python function's file, input deck templates and the names they are written
  to, `files`, and a parser's `file`) are relative to the model's directory (or, for `writes` and a parser's
  `file`, to the run directory), with no `..` part and no absolute path; any other is refused at loading,
  naming the field, and, for a path relative to the model's directory, saying what to do instead: a link in the model's directory to the file elsewhere
  (followed, below), or the spec moved up a directory. Only the command's program may be absolute, or found on `PATH` (`model_interface.md`).
  A file in the model's directory that is a link is followed: the user put it there.
- **Credentials files are refused** wherever a model spec or an MCP argument names a file: the spec's own
  path, the function's file, templates, `files`, a deck's `writes`, a parser's `file` (not the streams `stdout`
  and `stderr`; 0069 item 27), and the MCP tools' paths, the target of a link included. A
  credentials file is, as in v1's `is_secret`: `.env` and `.env.*` (not `.env.example`, `.env.sample`,
  `.env.template`); a name such as `.netrc`, `.pgpass`, `id_rsa`, or a shell start-up or history file; a name
  with `credential`, `credentials`, or `secret` as a word part (split at `.`, `_`, `-`); a suffix such as
  `.pem`, `.p12`, `.pfx`, `.ppk`; or a path through a directory such as `.ssh`, `.aws`, `.gnupg`,
  `.config/gcloud`, matched in the part of the path below the model's directory (a spec's paths) or the root
  (an MCP argument), and in the whole of a link's target that lies outside them. v1's `.key` suffix is left out, since LS-DYNA keyword decks use it. The lists are rewritten
  from v1's, with its tests (`scope.md`).
- **Hidden characters are refused:** a string in a model spec (mapping keys included) with a character in
  Unicode's categories Cc (control characters, tab excepted), Cf (format characters, such as bidirectional
  overrides and zero-width spaces; the joiners U+200C and U+200D excepted, which some scripts need), Cs (a
  lone surrogate, which would also break the hash), Zl, or Zp (line and paragraph separators) is refused at
  loading, naming the field, so no visible text in a command or an environment is hidden, overwritten, or
  reordered. (Some invisible characters remain legal in identifiers, such as a variation selector or U+3164;
  they are not refused.)
  Every string is one line: a command longer than one line belongs in a wrapper script. The same characters
  are refused in an MCP path argument (`PathRefused`), and `ema.approval` prints any such character in a
  question as its code (`\u202e`), but tab and line feed, so nothing in a question (a template's text, a
  resolved path) is hidden, and a template's lines still read as lines. Every string EMA didn't write (the spec's
  text, templates, the command, `env`, `function`, `files`, `pass_env` names, the program's resolved path,
  the save path, and the model's name and old path) is shown in a question in a code span (one line) or a
  fenced code block (several lines), its run of backticks longer than any in it, so a client that renders the
  question as Markdown shows it as typed (an HTML comment in it stays visible).
- **Duplicate keys are refused:** a spec with a key twice in one object is refused at loading, so the text
  the user reads is the spec EMA uses.

### The MCP server's root

- **`ema mcp --root DIR`** names the one directory the MCP tools' path arguments may name (E7). It is
  required and absolute: a client often starts a server in `/` or its own directory, so neither a default nor
  a relative path is safe. `ema mcp` without it, with a relative path, or with `/`, exits with a usage error
  (2) saying what to add to the client's configuration.
- **Confined:** every path argument of an MCP tool must lie inside the root (above: as files, after resolving
  links), and outside any workspace (no ancestor of the resolved path, up to `/`, holds `ema.db`):
  `propose_model`'s and `save_model`'s path, and `export`'s directory. Anything else, `..` that climbs out
  included, is refused before anything is read, asked, or written, naming the root (`PathRefused`).
  Workspaces are excluded so that no tool writes into a run directory or a result directory (0020). A root
  inside any workspace, or equal to one, is refused when `ema mcp` starts: `open_workspace(root=)` raises
  `PathRefused`, and `ema mcp` exits 2 (0061).
- **A drafted spec's files stay inside the root:** under a root, a file the spec names (the function's file,
  templates, `files`) whose resolved target lies outside the root is refused (`PathRefused`), so a link
  already in the root (a virtual environment's, a shared drive's) doesn't let `propose_model` or `save_model`
  read outside it.
- **The workspace** (`--workspace`) is EMA's own and needn't be inside the root; with `ema mcp`, a relative
  `--workspace`, and the default `ema_workspace`, resolve against the root rather than the working directory.
- **Resources and ids are looked up, never joined into a path:** `ema://results/{id}/figures/{name}.png` serves
  a figure only when `{name}` is one of that result's figures.
- **Where the check lives:** `open_workspace(path="ema_workspace", *, root=None)`; the MCP server opens its workspaces with
  the root, and each `Workspace` method that takes a path refuses one outside the root, or inside a
  workspace (`ema.mcp` may import only `ema.workspace` and `ema.types`, AR3).

### The path `save_model` writes

- The confirmation shows the **absolute path** the file will be written to: the path's parent resolved
  through its links, and its name; never the agent's string.
- The path must end in `.json`, its parent must exist, and both must lie inside the root and outside any
  workspace.
- **Written as shown:** the bytes written are the bytes shown, whose hash is recorded (W2), with an exclusive
  create, so a file that appears between the question and the write is never overwritten. If one does, the
  save is refused, naming the file; the yes stays recorded (T3), and nothing is loaded.
- **An existing file:** one holding the same spec (its text, read as a spec and written again, is the drafted
  spec's text: the same bytes, or hand-formatted) is loaded, never rewritten: `propose_model` shows the file's
  own text, the question says "already saved, unchanged: load it?" with those bytes, whose hash is recorded,
  nothing is written, and the file is loaded after the yes, refused if it changed after the question (0080 item
  29, 0081 item 17). A file holding another spec, or text that isn't one, is refused before asking, naming the
  file (`PathRefused`), and nothing is recorded.

## Text EMA didn't write, in reports and figures

Text that comes from a model spec (names; the model's description; each model parameter's and model
prediction's description and units) or from a model (a failed run's reason, or a missing model prediction's, which the notes print verbatim:
`diagnostics/shared.md`) is printed literally. The report backslash-escapes Markdown's special characters in
it, and pandoc's LaTeX writer then escapes TeX's; figure labels (`name [units]`) escape `$`, so matplotlib's
mathtext doesn't read it. No such text becomes math, a link, or TeX that pandoc or LaTeX acts on (0018).
Every text field of a result is plain text, escaped the same way, so EMA's own symbols in a result are Unicode
(ρ, Sᵢ, R²), and the report writes no math (0073). A line of such text that would start a block has its marker
escaped too (`-`, `+`, `:`, or `=` first, or the `.` or `)` of `1.`, `a)`, `(iv)` before a space), and a line
ending inside a table cell, a table's title, or a caption becomes a space. As a second guard, pandoc reads the
report with raw TeX, raw HTML, raw attributes, TeX math in dollars, smart punctuation, and implicit figures off
(`-f markdown-raw_tex-raw_html-raw_attribute-tex_math_dollars-smart-implicit_figures`), and runs with `--sandbox`,
so it reads only the report and its figures (0073; implicit figures, 0081 item 30). A description
`\input{~/.ssh/id_rsa}` renders as that text, and the PDF holds no file. Names are escaped too: an identifier
such as `_T_` would otherwise render as emphasis. A spec's units print literally in figure labels as well, so units
are written as plain text or Unicode (`W/m²`), not mathtext (`m$^2$`); EMA's own figure labels keep mathtext.

**In an export,** `runs.csv`'s text columns are not escaped for Markdown or for spreadsheets: `ema_reason`
holds the stored reason, and `ema_missing` is as E4 writes it; a spreadsheet may read a cell that starts with `=`, `+`, `-`, or `@` as a
formula, and the guides say to open `runs.csv` as data.

## Model output and the MCP client

A failed run's reason, a missing model prediction's reason, and a failed run's last 15 lines of stderr (`model_interface.md`, Failures) are the model's own
output, and `failed_runs` returns them to an MCP client as data. Nothing a client reads changes what EMA does
without the user: every run and save is asked, and every path argument is confined. The server's
instructions (`ema/mcp/tools.md`, 0019) say that reasons and stderr lines are quoted model output.

## Where the rules live

`architecture.md` §6 places v1's approval rules in `ema.approval`; the layers put most of them lower, where
the code that needs them can import them (AR1):

| Rule | Module |
|---|---|
| the spec's path shapes (string checks on `/`-separated parts, AR2), credentials-file names, credential-like variable names, hidden characters (`unicodedata`), duplicate keys, `pass_env` beside `env`, an `env` `PATH`'s empty or relative entries | `ema.types.model` (`ModelSpec.from_json`: checks that need no file); `CREDENTIAL_WORDS` and the credentials-file lists live there |
| paths as files (`same_file`), "inside a directory" (`is_within`), a named file whose link resolves to a credentials file | `ema.models.files`, used by `load_spec` and the workspace |
| the environment (`BASE_ENV`, `model_environment`), the child's process group and streams | `ema.models.sandbox`, used by `execute` and `resolve_program` |
| output read inside the run directory | `ema.models.parsers`, `ema.models.collect` |
| EMA's files in a run or batch directory written without following links | `ema.models.execute` (`predictions.json`), `ema.models.collect` (`run.json`) |
| run and batch directories deleted without following links | `ema.models.files` (`remove_tree`), used by `prepare` and `ema.runner` (0061) |
| loading never imports a model (M17 and the function's signature check, by `ast`) | `ema.models.load_spec` |
| asking, the first approval's and the confirmation's text (hidden characters as codes, code spans and fenced blocks), recording every answer | `ema.approval` |
| the MCP root, `save_model`'s write | `ema.workspace` (`open_workspace(..., root=)`), from `ema mcp --root`; `ema.models.save_spec` |
| escaping text EMA didn't write; pandoc's reader options | `ema.report`, `ema.plotting` (`axis_label`) |

**Size:** about 145 lines, by package: `ema.types` about 75 (the credentials lists, rewritten from v1's, about 50;
the name and character checks, about 25); `ema.models` about 35 (the environment, about 15; paths and links, about
20); `ema.workspace`, `ema.cli`, and `ema.approval` about 25 (the root, `--root`, the confirmation's text and its
same-bytes branch); `ema.report` and `ema.plotting` about 10. The ported sandbox and worker are
about 500 lines (v1's 534 less little); without v1's limits (about 50 lines) and its withheld variables (about
15), about 435, as `architecture.md` §11 counts them. Net about 80 more: about 7,940 of `scope.md`'s then 8,000;
after 0061–0063, about 8,200 of 8,300 (0064); the budget is 12,000 since 0086 item 1 (11,000 in 0084).

## Not in v2.0

| Item | Why not now | To add later |
|---|---|---|
| An OS sandbox for models (no network, files limited to the run directory) | models are the user's own code; the agent writes no code file (0016); the tools differ by platform (macOS's `sandbox-exec` is deprecated; Linux has bubblewrap and Landlock) and break MPI, license servers, and solvers that read from the user's tree | about 150–250 lines per platform, a setting, and its tests; the seam is `execute`, the only code that starts a model (AR4), whose input is plain data (`PreparedCall`) |
| Memory and CPU limits | 0026 | about 50 lines from v1's `_worker.py` (0026) |
| Patterns in `pass_env` (`SLURM_*`, `I_MPI_*`), as tox allows | exact names cover a license server and a few variables; a scheduler's or a module system's many variables are set by a wrapper script that loads them | about 15 lines: a trailing `*`, kept in the model version, its matches checked against `CREDENTIAL_WORDS` when the call starts, and the first approval listing the matched names |
| Hashing shared copies before each call | they are read-only; hashing doubles the per-call cost for large files (about 1 s per GB) | a few lines in `check_files` |

## Rules

| Id | Rule | Test |
|---|---|---|
| T1 | Paths are compared as files, never as strings: P3 and C33's rule, and every "inside a directory" check here. | C33's test; on a case-insensitive file system, `MODEL.JSON` is the same file as `model.json`; on a case-sensitive one, two names differing in case are two files; `ROOT/../x` is outside the root, and the root itself is inside it. |
| T2 | A model, of either kind, gets exactly the base variables EMA has, its spec's `pass_env`, and its spec's `env`; nothing from `.env`, and no variable EMA adds (M2, C32). | C32's test; for both kinds of model: a variable set in EMA's environment and in a `.env` beside the spec is absent; `PATH` and a `pass_env` name are present; an `env` value overrides the base; a name in both is refused at loading; an `env` `PATH` of `/opt/bin:$PATH` is refused, naming the entry. A Python child given the base only imports `ema`, NumPy, and a module reachable only through EMA's `sys.path`; `OMP_NUM_THREADS` in `env` is seen by NumPy. A base `PATH` ending in `:`: a program left in the run directory under the command's name is not run. A `PYTHONPATH` in `env` doesn't change a function's imports. |
| T3 | Every approval and confirmation asked is recorded with its question and answer, yes or no; none is recorded when nobody could be asked (W2, W3, Q12). | Yes, no, an exception in the approver, and `approve=None`: three records and none, in order. |
| T4 | Nothing runs, and no model spec is saved, without the user's yes; loading or proposing a spec runs nothing of the model's; through MCP the yes is an elicitation, and a client without elicitation is refused before anything is asked (P3, 0016). | U9's scripted client: declined and unanswered elicitations save nothing and run nothing; a client without elicitation gets the refusal, and the store is unchanged. A function file, and a package `__init__.py` it imports, that each write a marker when imported: `load_model` and `propose_model` leave no marker. |
| T5 | Every MCP path argument lies inside the root named at `ema mcp` start and outside any workspace, checked as files after resolving links, with no hidden character; a drafted spec's files resolve inside the root; `ema mcp` refuses to start without a root, with a relative one, with `/`, or with a root inside a workspace; resources are looked up by name (E7). | `save_model` and `export` with a path outside the root, one with `..` climbing out, a link inside pointing out, a path inside the server's workspace's `runs/` and inside another workspace under the root, and a name with U+202E: each refused, with nothing written or asked. A drafted spec whose `files` entry links outside the root: refused, the target not read. `ema mcp` with no `--root`, a relative one, `/`, and another workspace's `runs/` as root: exit 2. A figure resource named `../../x`: not found. |
| T6 | `save_model`'s confirmation shows the absolute path, what an already loaded name means now, and the full text; the file written has exactly the bytes shown; an existing file holding the same spec is loaded, never rewritten; one holding another spec, or other text, is refused before asking (0080, 0081). | The recorded hash equals the file's; a path through a link shows the resolved parent; a spec named like a loaded model says what the name means now; an existing file with another spec is refused, with no confirmation recorded; a file created between the yes and the write is refused and kept; the same spec, as the same bytes or hand-formatted, asks "load it?" with the file's text, writes nothing, and loads the file after the yes, and a file changed after the question is refused; a path not ending in `.json`, and one whose parent doesn't exist, are refused before asking. |
| T7 | Paths in a model spec are relative, with no `..` and no absolute path (but the command's program); a file a spec or an MCP argument names that is a credentials file is refused (v1's `is_secret`); a spec string with a hidden character (Cc but tab, Cf but the joiners, Cs, Zl, Zp), a duplicate key, and EMA's own file names as `writes` or `files`, are refused; a question prints such characters as codes (but tab and line feed), and every string EMA didn't write in a code span or a fenced block. | `files: ["../x"]`, `"/etc/hosts"`, `".env"`, `".ssh/id_rsa"`, `"db-credentials.json"`, and `"mesh.dat"` linked to `~/.ssh/id_rsa`: each refused at loading, naming the field; `.env.example`, `secretion.py`, and `deck.key` load. A command with `\u001b[2K`, a description with U+202E, a name with a lone surrogate, a description with a newline, and `"command"` twice: refused, naming the field. A model directory under `~/.docker/` loads. A template with U+202E: the first approval shows `\u202e`, and its lines as lines. A save path holding `<!-- x -->`, and a template holding a line of three backticks: each shown as typed. `files: ["run.json"]`: refused. `files: ["../mesh.h5"]`: the message names the link workaround. |
| T8 | A variable name that looks like a credential, or isn't a variable name, is refused in `env` and `pass_env`; EMA never shows or stores a `pass_env` value. | `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`, `SSH_AUTH_SOCK`, `A=B`, and `""` refused; `OMP_NUM_THREADS`, `LM_LICENSE_FILE` load; the first approval's stored question holds `LM_LICENSE_FILE` and "set", not its value. |
| T9 | Model output is read only from inside the run directory; a parser's file that links out of it is missing, with a reason (0030). EMA's own files in a run or batch directory are written, and those directories deleted, without following links. A model's streams never reach EMA's stdout. | `plate.out` a link to a file outside the run directory: the model prediction is missing, and the file outside is not read. A model that leaves `run.json` as a link to a file outside: that file is unchanged. A run directory not kept, holding a link to a data directory: the directory is deleted, the data kept. Under a scripted MCP client, a function that prints at import and in each call: the protocol stream stays valid. |
| T10 | Text EMA didn't write (spec text, names included, and failure reasons) prints literally in reports and figure labels; a block marker at a line's start is escaped too; pandoc reads the report as `markdown-raw_tex-raw_html-raw_attribute-tex_math_dollars-smart-implicit_figures`, with `--sandbox` (0073; 0081 item 30). | A description and a failure reason `$\input{/etc/hosts}$ *x* [a](b)`, and a model prediction named `_T_`, render as written in the report; a failure reason whose line starts `1. ` or `- ` renders as written; units `$\input{/etc/hosts}$` render as written in a figure's axis label; the PDF (when `to_pdf` doesn't raise `PandocMissing`, 0059) holds no line of `/etc/hosts`. |

M9 and C38 (no pickle; the child's process group, which the asks below add to M9) and M20 and C39 (no
shell) are the model interface's own rules, cited above and not repeated here.

## Decisions

| Item | Decision | Record |
|---|---|---|
| the word for what EMA isolates | "model" (the glossary's "a program or function"); no new row; "user code", "model code", and "model program" join the model row's Avoid column | 0057 |
| the held principle "User code runs isolated, without EMA's secrets" | answered by T1–T10, not a principle (as 0056 answered "One-way layers"): EMA has no secrets of its own, and P1–P7 protect what a user sees | 0057 |
| the model's environment | an allowlist for both kinds of model: `BASE_ENV`, the spec's `pass_env` (names; values not in the model version, never shown), and its `env`; credential-like names refused; variable names checked; values not checked; empty or relative `PATH` entries refused in `env`, dropped from the base | 0057 |
| the MCP root | `ema mcp --root DIR`, required and absolute, not inside a workspace; path arguments inside it and outside any workspace; a drafted spec's files inside it; `open_workspace(..., root=)` | 0057 |
| v1's approval rules | placed by layer (above), not all in `ema.approval` | 0057 |
| spec paths and strings | relative, no `..`, no absolute; credentials files refused; hidden characters and duplicate keys refused; one-line strings | 0057 |
| the first approval | also shows the environment the spec sets | 0057 |
| `save_model`'s confirmation | the absolute path, what the name means now, the full text; exclusive create | 0057 |
| a file at `save_model`'s path holding the same spec | loaded after a yes, never rewritten; T6 reads "the same spec", not "the same bytes" | 0080, 0081 |
| text EMA didn't write | printed literally, escaped, names included; pandoc reads no raw TeX; not escaped in `runs.csv` | 0057 |
| T10's reader | text in a result plain and escaped, block markers too; pandoc reads no math in dollars, no smart punctuation, no implicit figures, with `--sandbox` | 0073; 0081 |
| the Python child | its own process group; started by path, its `sys.path` replaced by EMA's (absolute) over its pipe; its streams kept off EMA's stdout | 0057 |
| run and batch directories | EMA's files written, and directories deleted, without following links; EMA's file names refused as `writes` or `files` | 0057 |
| loading | never imports a model file (M17 by `ast`), and the function's signature check (0081 item 29) | 0057; 0081 |
| questions | hidden characters printed as codes (but tab and line feed); every string EMA didn't write in a code span or a fenced block | 0057 |
| no OS sandbox, no limits, no `pass_env` patterns, no hashing of shared copies per call | not in v2.0 | 0026; 0057 |

## What this spec asks of other documents

Record 0057, applied 2026-10-01:

- **`model_interface.md`:**
  - The model spec: paths relative with no `..`, none absolute but the command's program; credentials files
    refused (`SpecError`, naming the field); EMA's own file names refused as `writes` or `files`; strings of
    one line, with no character in Cc (but tab), Cf (but the joiners), Cs, Zl, or Zp; duplicate keys refused
    (T7).
  - Python function, Isolated: "a scrubbed environment" becomes "the environment `trust.md` gives, with the
    spec's `env` and `pass_env`"; the child in its own process group, killed whole; started by path, its
    `sys.path` replaced by EMA's (absolute) over its pipe; loading never imports the function's file (M17
    by `ast`).
  - Command line, Environment ("the scrubbed environment (`trust.md`), plus the spec's `env` mapping"): moves
    to a section for both kinds of model, with `pass_env` beside `env`, names checked and credential-like
    names refused in both (T8), and empty or relative `PATH` entries refused in `env`, dropped from the base.
  - M9: a timeout, a crash, or Ctrl-C "kills its process group"; its test adds M20's: a function that starts
    a subprocess and sleeps; both are gone after the timeout and after Ctrl-C (C38 promises M9, so follows).
  - A run: EMA's files in a run or batch directory written, and directories deleted, without following
    links; Failures, `error`, adds "or EMA couldn't write its own file in the run or batch directory".
  - Versions, Not covered: the values of `pass_env` variables; the first approval shows the environment.
  - M2: "Model code gets…" becomes "A model gets…".
  - Its Trust ask done.
- **`principles.md`:** P3's Enforced by: the values of `pass_env` variables are not covered, beside programs
  outside the model's files; "Model files are compared as files (samefile, casefold)" becomes "(samefile;
  case-folded where the file system is)"; the held candidate "User code runs isolated, without EMA's secrets" removed,
  answered by T1–T10, and the Candidates note says so beside "One-way layers".
- **`glossary.md`:** the "model" row's Avoid column: "user code, model code, model program".
- **`scope.md`:** "Agent-written model code" (a bullet) becomes "Agent-written code"; the `_sandbox.py` row's "isolation
  of model code" becomes "isolation of models"; the `agent/approval.py` row's "v2's trust module keeps its
  rules" becomes "v2's trust rules (`trust.md`, placed by layer) keep its rules".
- **`architecture.md`:**
  - §2: `files.py` gains `is_within`; `sandbox.py` holds `BASE_ENV` and `model_environment`.
  - §3, `ema.types`'s imports: `unicodedata` added to its pure standard-library modules.
  - §3, `types/model.py`: `env` moves from `CommandLine` to `ModelSpec`, beside a new
    `pass_env: tuple[str, ...] = ()`; their rows in the spec's fields say both kinds of model, in the model
    version (`pass_env`'s names only); `from_json` also checks an `env` `PATH`'s entries (T2), T7 (path shapes, credentials-file names, hidden
    characters, duplicate keys, one-line strings) and T8.
  - §3, `types/requests.py`: `ApprovalRequest` gains `env: Mapping[str, str]` (the spec's `env`) and
    `pass_env: Mapping[str, bool]` (each name: set or not); `ApprovalRequest` also gains `function: str | None` (a Python function's, shown
    in place of the command); `ConfirmationRequest` gains `replaces: str | None`
    (what the name means now); `Proposal.path` is the absolute path the confirmation would show.
  - §3, `types/errors.py`: `PathRefused` (an MCP path argument outside the root, inside a workspace, with a
    hidden character, or naming a credentials file; a drafted spec's file resolving outside the root; not
    retryable). A spec naming a credentials file is a `SpecError`.
  - §5: `same_file`'s comment "samefile, casefold" becomes "samefile; case-folded where the file system is";
    `is_within` and the resolved-link check in `models/files.py`; `PreparedCall.env` is the whole
    environment the model gets (`model_environment`); `resolve_program` resolves against it; `save_spec`
    writes with an exclusive create; "the environment it passes is step 10's" becomes "`trust.md`'s"; the
    child in its own process group, its `sys.path` over its pipe, its streams off EMA's stdout; `run.json` and
    `predictions.json` written without following links.
  - §6: `ask_approval`'s first approval shows the environment, and a Python function's `function`; every
    question prints hidden characters as codes, and every string EMA didn't write in a code span or a fenced
    block; `ask_confirmation` shows the absolute path and
    what the name means now; "this module is where they go" becomes "`trust.md` places them by layer".
  - §7: `open_workspace(path="ema_workspace", *, root=None)`; path arguments outside the root or inside a workspace, and a
    drafted spec's files resolving outside the root, refused (T5); `save_model`'s comment: `.json`, an existing parent, a different file refused before asking, the
    same bytes asked as "load it?".
  - §8: `ema mcp --root DIR` (required and absolute; not `/`, nor inside a workspace); a relative `--workspace` resolves against the root; MCP path arguments
    confined; figure resources looked up by name; the server's instructions say reasons and stderr lines are
    quoted model output.
  - §11: about 80 lines more (7,940), by package (the rules on run directories, names, and questions add a
    few lines each, inside these estimates); §12: rows for these decisions; its Trust ask done.
- **`use_cases.md`:** U2: the first approval also shows the environment the spec sets (What EMA asks; Done
  when); U6: "shows the command, the input deck template, and the files again" adds the environment; U9: the
  scripted client starts `ema mcp --root`; the asks' Trust lines done.
- **`export.md`:** E7 and the MCP interface name `ema mcp --root`, and a directory outside any workspace;
  `runs.csv`'s text columns are not escaped, and the run-a-diagnostic guide says to open it as data; its Trust ask done.
- **`data_model.md`:** `confirmations.spec_path` is the absolute path shown (T6); Q4's "the first approval
  shows the command, templates, and files" adds the environment, and a Python function's `function`; its Trust ask done (T3; the
  run lock, above).
- **`diagnostics/shared.md`:** the notes' reasons print "verbatim" as escaped Markdown that renders verbatim
  (T10); Figures, Axes: "with mathtext for symbols" becomes "mathtext for EMA's own symbols; a spec's names
  and units print literally"; golden reports compare names as rendered.
- **Guides (step 13):** done (`../guides/`, 0060): the add-a-model guide: no secret in `env`; `pass_env` with an
  example; `DYLD_*` dropped on macOS; a wrapper script for a command of more than one line, or for a scheduler's
  or module system's many variables; units as plain text or Unicode; a link for a file outside the model's
  directory. The get-started guide: `ema mcp --root` in an MCP client's configuration. The run-a-diagnostic guide,
  with export: open `runs.csv` as data.
- **`contracts.md`:** C32's promise "M2 and T2", and its Generalizes adds T2.
- **Record 0029:** "accepted; its list of what is not covered amended by 0057 (`pass_env` values)".
- **`docs/decisions/README.md`:** the 0057 row; 0029's status.
- **`CLAUDE.md`:** "Model programs never receive it" becomes "Models never receive it".
- **`STATUS.md`, `TODO.md`:** step 10 done.
