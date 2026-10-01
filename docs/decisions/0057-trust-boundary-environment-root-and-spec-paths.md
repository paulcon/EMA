# 0057. Give a model an allowlisted environment, confine the MCP server to a root, and check a spec's paths

**Date:** 2026-10-01. **Status:** accepted. **Resolves:** none (TODO step 10, the trust boundary).

## Context

- **Step 10's inputs** (`../notes/consistency_review_2026-10-01.md`, "Step 10 inputs"; `../design/architecture.md`,
  `../design/model_interface.md`, `../design/export.md`, and `../design/data_model.md`'s asks): one word for
  the code EMA isolates; the environment a model gets, and whether credential-like `env` values are refused;
  no `..` or absolute paths in a spec; the directory `ema mcp` confines path arguments to (E7, 0053), and its
  flag; the write path shown in `save_model`'s confirmation; where v1's approval rules go; the held principle
  "User code runs isolated, without EMA's secrets" (`../design/principles.md`, Candidates; 0026).
- **v1** gave a model its whole environment minus a list of withheld variables: the Anthropic keys, and every
  variable its chat loaded from `.env` (`_sandbox.py`, `WITHHELD_ENV`). v2 has no LLM SDK (AR6) and never reads
  `.env`, so it has no secrets of its own; but its environment is the analyst's shell's, or the one an MCP client
  starts `ema mcp` with, and either may hold API keys. A denylist misses a secret with an ordinary name
  (`DATABASE_URL` with a password), and M2's test ("lacks a variable set in `.env`") holds only for names on it.
- **Simulation codes need some variables:** `PATH`, `HOME`, the locale, library paths, and sometimes a license
  server (`LM_LICENSE_FILE`) or a module system's variables. The spec's `env` holds literal values, which are
  part of the model version (0029), so a machine-specific value written there makes a new model version per
  machine.
- **An MCP client's agent is not trusted** (it may be mistaken, or misled by text it read), but MCP clients
  often start a server in `/` or in their own directory, so a working-directory default confines nothing.
- **v1's critical bug A1** was a path compared as a string on a case-insensitive file system (P3).
- **A model spec's free text reaches LaTeX:** reports are Markdown with TeX math, made into PDFs by pandoc
  (0018), and pandoc passes `$…$` and raw TeX such as `\input{…}` through. An agent drafts specs (0016).
- **The layers** (AR1) let `ModelSpec.from_json` (layer 0) and `load_spec` (layer 2) check a spec, but not
  import `ema.approval` (layer 3b), where `architecture.md` §6 put v1's rules.

## Decision

We will:

1. **Give a model an allowlisted environment,** the same for both kinds of model: the variables in `BASE_ENV`
   that EMA's environment has (`PATH`, `HOME`, `USER`, `LOGNAME`, `SHELL`, `TMPDIR`, `TZ`, `LANG`, `LC_*`,
   `LD_LIBRARY_PATH`, `DYLD_LIBRARY_PATH`); the variables its spec names in a new field, `pass_env`, with their
   values in EMA's environment; and its spec's literal `env`, which takes precedence. `env` moves from the
   command-line interface to the spec, so a Python function's child gets both when it starts (a library reads
   `OMP_NUM_THREADS` when it loads). Nothing else, and no variable of EMA's own. `pass_env`'s names are part of
   the model version; their values are not, like a program found on `PATH` (0029), and EMA never shows or
   stores them itself (what the model writes to its streams is its output). A name in both `env` and
   `pass_env` is refused. The program is resolved against the model's own `PATH`; an empty or relative
   entry is refused in an `env` `PATH` (values are literal: no `$PATH`, no `~`) and dropped from the base
   `PATH`. A variable name must be `[A-Za-z_][A-Za-z0-9_]*`.
2. **Refuse credential-like variable names** in `env` and `pass_env` at loading: a name with a part (split at
   `_`, case-folded) in `CREDENTIAL_WORDS` (`key`, `apikey`, `token`, `secret`, `password`, `passwd`,
   `passphrase`, `credential`, `credentials`, `auth`). `env` values are not checked; the add-a-model guide says
   not to put a secret there.
3. **Show the environment in the first approval** for a model version, beside the command and the program's
   path (or a Python function's `function` and interpreter), the templates, and the files: each `env` variable with its value, and each `pass_env` name with "set" or
   "not set".
4. **Check a spec's paths and strings:** the function's file, templates, the names decks are written to,
   `files`, and a parser's `file` are relative, with no `..` part; only the command's program may be absolute.
   A credentials file (v1's `is_secret` lists, rewritten with their tests, matching `secret` and `credential`
   as word parts, and without the `.key` suffix) is refused wherever a spec or an MCP argument names one, the
   spec's own path and a link's target included; credentials directories are matched below the model's
   directory or the root, and in a link's target outside them. A string (mapping keys included) with a
   character in Unicode's categories Cc (tab excepted), Cf (the joiners U+200C and U+200D excepted), Cs, Zl, or
   Zp is refused, so every string is one line and no visible text in a command or an environment is hidden,
   overwritten, or reordered; a duplicate key is
   refused, so the text the analyst reads is the spec EMA uses; EMA's own file names (`run.json`, …) are
   refused as `writes` or `files`. A path outside the model's directory is refused with a message naming the
   workaround (a link in it). `ema.approval` prints any such character in a question as its code (but tab and
   line feed), and shows every string EMA didn't write in a code span or a fenced code block.
5. **Confine the MCP server's path arguments to a root:** `ema mcp --root DIR`, required and absolute, not
   `/`, and not inside a workspace. Every MCP path argument (`propose_model`'s and `save_model`'s path,
   `export`'s directory) must lie inside it and outside any workspace (no ancestor holds `ema.db`), with no
   hidden character, checked as files after resolving links (P3's rule), or is refused (`PathRefused`) before
   anything is read, asked, or written. A drafted spec's files must resolve inside the root. A relative
   `--workspace`, and the default, resolve against the root under `ema mcp`. Resources are looked up by name, never joined into a path. The check is
   `open_workspace(path="ema_workspace", *, root=None)`'s, since `ema.mcp` imports only `ema.workspace` and `ema.types` (AR3).
6. **Make `save_model`'s confirmation show** the absolute path (the parent resolved through its links, and the
   name), what the model's name means now when it is already loaded (0054), and the full text; require
   `.json` and an existing parent; write exactly the bytes shown with an exclusive create (a file that appears
   meanwhile is kept, and the save refused); ask "already saved, unchanged: load it?" for the same bytes; and
   refuse a different existing file before asking.
7. **Run the Python child in its own process group,** killed whole, started by its worker's path, which
   replaces its `sys.path` with EMA's, made absolute (received over its pipe), before any import; and keep
   every model's streams off EMA's stdout (the MCP protocol channel).
8. **Never run a model while loading:** `load_spec` and `propose_model` read the function's file as text,
   and M17's check parses it (`ast`) without importing it or a package it names.
9. **Write EMA's own files in a run or batch directory** (`run.json`, `predictions.json`) without following a
   link the model left there (the run fails, kind `error`, if EMA can't), and delete run and batch
   directories without following links.
10. **Print text EMA didn't write literally:** a spec's names, descriptions, and units, and failed runs' and missing
   model predictions' reasons, are backslash-escaped for Markdown in reports (pandoc's LaTeX writer escapes TeX's characters), with `$`
   escaped in figure labels; pandoc reads reports with raw TeX, raw HTML, and raw attributes off (math stays
   on for EMA's own TeX, so the escaping alone guards it). `runs.csv`'s text columns are not escaped for Markdown or
   spreadsheets; the guides say to open it as data, not as a spreadsheet's formulas. A spec's
   units in figure labels print literally too; EMA's own symbols keep mathtext. The MCP
   server's instructions say that reasons and stderr lines are quoted model output.
11. **Place v1's rules by layer:** the checks that need no file in `ModelSpec.from_json`; paths as files and
   links in `ema.models.files`; the environment and the child in `ema.models.sandbox`; asking and recording in
   `ema.approval`; the root in `ema.workspace`; escaping in `ema.report` and `ema.plotting`.
12. **Answer the held principle "User code runs isolated, without EMA's secrets" with the trust rules T1–T10,**
    not a principle, as 0056 answered "One-way layers": EMA has no secrets of its own, and P1–P7 protect what
    a user sees.
13. **Call what EMA isolates "the model"** (the glossary's "a program or function"), with no new row; "user
    code", "model code", and "model program" join the model row's Avoid column.

Not in v2.0: an OS sandbox for models, memory and CPU limits (0026), patterns in `pass_env`, and hashing shared
copies before each call (`../design/trust.md`, Not in v2.0, with the effort to add each).

## Alternatives considered

- **The environment:**
  - **Base and `env` only, `pass_env` later:** no new field, but a variable outside the base must be written
    literally into `env`, where a machine-specific value makes a new model version per machine, or set by a
    wrapper script. About 20 lines and a record to add later.
  - **Everything but credential-like names (v1's way):** nothing that works in the shell breaks, but a secret
    with an ordinary name gets through, and M2 holds only for names on the list.
- **Check `env` values for secret shapes** (`sk-`, `ghp_`, `AKIA`, a password in a URL): catches some pasted
  keys, but refuses ordinary paths and hosts by guesswork; the analyst sees every value in the first approval
  (and, for a drafted spec, the confirmation).
- **Show `pass_env` values in the first approval:** more informative, but the question is stored in full and
  sent to an MCP client, and a secret with an ordinary name (`PGPASSWORD`) passes the name check.
- **`env` and `pass_env` for command-line models only:** a function can set a variable in its own code, but
  not one a library reads when it loads, and a Python wrapper around a licensed solver would hard-code a
  machine's value in a tracked file.
- **Allow credential-like names in `pass_env`,** since their values aren't stored: a model reading cloud
  storage could use them, but a spec an agent drafted could hand a key to a command, and the tools' own
  credentials files serve the same need.
- **MCP path arguments anywhere inside the root, the workspace included:** simpler, but `export` and
  `save_model` could then write into kept run directories and result directories, which EMA never changes
  after they are written (0020).
- **MCP's own roots** (the directories a client declares, `roots/list`): no flag to configure, but the client
  application chooses them, and not every client supports them; a root the analyst names in the server's
  command is under their control.
- **One trust module in a low layer** (v1's lesson: "a module from day 1"): one file to read, but it would
  mix pure checks (layer 0), file and process checks (layer 2), and asking (layer 3b), and AR1 would force it
  to the lowest layer, with I/O there against AR2. The rules are one spec instead, with each placed where
  its caller can import it.
- **A default MCP root** (the working directory, or the home directory): one flag fewer, but a client that
  starts the server in `/` confines nothing.
- **The root checked in `ema.mcp`:** keeps `open_workspace` unchanged, but `ema.mcp` may not import the path
  functions (AR3), and the Python API couldn't use the same confinement.
- **Adopt the held principle as P8** ("A model runs isolated, with only the environment its spec names"): one
  more line in `CLAUDE.md`; the rules and tests are the same.
- **A glossary row for "user code":** the model is the only code EMA runs for the analyst (output parsers are
  EMA's, and the agent writes no code, 0016), so a second word would name the same thing.

## Consequences

- **`../design/trust.md`:** written from this record (T1–T10); its "What this spec asks of other documents"
  lists each passage below in detail.
- **`../design/model_interface.md`** (accepted): a spec's paths and strings; the Python child's environment
  (`env` and `pass_env`), process group, and start; the Command line's Environment bullet, for both kinds of
  model, with `pass_env`, the T8 refusal, and `PATH`'s entries; Versions, Not covered: `pass_env` values; the
  first approval shows the environment; M2's "Model code" becomes "A model"; Failures' `error` adds EMA failing to write
  its own file; M9 kills the child's process group,
  and its test adds a function's subprocess; M17 by `ast`; a run's files and deletions; its Trust ask done.
- **`../design/principles.md`** (accepted): P3's Enforced by adds `pass_env` values to what is not covered,
  and compares files "samefile; case-folded where the file system is"; the held candidate is removed,
  answered by T1–T10, as the Candidates note says.
- **`../design/glossary.md`** (accepted): the model row's Avoid column.
- **`../design/scope.md`** (accepted): "model code" in a bullet and a row; the `agent/approval.py` row's "trust module"
  becomes the trust rules placed by layer.
- **`../design/architecture.md`** (accepted): §2 (`files.py`, `sandbox.py`); §3 (`unicodedata` among
  `ema.types`'s imports; `env` and `pass_env` on `ModelSpec`, their field rows, `from_json`'s checks; `ApprovalRequest.env` and `.pass_env`,
  `ApprovalRequest.function`; `ConfirmationRequest.replaces`; `Proposal.path` absolute; `PathRefused`); §5 (`same_file`'s comment, `is_within`, `PreparedCall.env`,
  `resolve_program`, `save_spec`'s exclusive create, the child, EMA's files in a run directory); §6 (the first
  approval, with a Python function's `function`; the confirmation; hidden characters printed as codes, and
  strings EMA didn't write in code spans or fenced blocks; the rules placed by layer); §7 (`open_workspace`'s `root`; `save_model`'s comment); §8 (`ema mcp --root`; the workspace under it;
  confined arguments; figure resources by name; the instructions on quoted model output); §11 (about 7,940
  lines); §12 (decision rows); its Trust ask done.
- **`../design/use_cases.md`** (accepted): U2's and U6's first approvals also show the environment the spec
  sets; U9's scripted client starts `ema mcp --root`; the asks' Trust lines done.
- **`../design/export.md`** (accepted): E7 and the MCP interface name `ema mcp --root`, and a directory outside
  any workspace; `runs.csv`'s text columns not escaped, opened as data; its Trust ask done.
- **`../design/data_model.md`** (accepted): `confirmations.spec_path` is the absolute path shown; Q4's first
  approval shows the environment and a Python function's `function`; its Trust ask done.
- **`../design/diagnostics/shared.md`** (accepted): reasons print verbatim as escaped Markdown; axis labels
  keep mathtext for EMA's own symbols only.
- **Guides (step 13):** the add-a-model guide (`env`, `pass_env`, `DYLD_*`, wrapper scripts, plain-text
  units, links to files elsewhere), the get-started guide (`ema mcp --root`), and the run-a-diagnostic guide
  (`runs.csv` as data).
- **`../design/contracts.md`** (accepted): C32 promises M2 and T2.
- **Record 0029:** "accepted; its list of what is not covered amended by 0057".
- **`README.md` in `docs/decisions/`:** the 0057 row, and 0029's status.
- **`../../CLAUDE.md`:** "Model programs never receive it" becomes "Models never receive it".
- **Size:** about 80 more source lines (`../design/trust.md`, Where the rules live), leaving about 60 of the
  8,000.
- **Harder later:** a model that relied on a variable outside the base fails until its spec names it in
  `pass_env` or `env`; the add-a-model guide (step 13) says how, with an example.
- **`../../STATUS.md`, `../../TODO.md`:** step 10 done when `trust.md` and this record are accepted.
