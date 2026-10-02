# 0074. Step 07's provisional choices: the runner and approval

**Date:** 2026-10-02. **Status:** proposed (provisional; record 0066). **Resolves:** none.

## Context

Build step 07 (`../plans/07-runner-and-approval.md`) builds `ema.runner` (`resolve`, `price`, `run_new`,
`read_batch`, `replay_batch`) and `ema.approval` (`ask_approval`, `ask_confirmation`, `ask`) on `demo-07-runner`,
without the owner's review (0066). The specs (`../design/architecture.md` §6 and §7, `../design/data_model.md` Q1,
Q2, Q13, Q15, W2–W4 and §10, `../design/trust.md`, `../design/use_cases.md` U1, U2, U9, `../design/contracts.md`)
and records 0010, 0015, 0049, 0054, 0056, 0057, 0071 (its deferrals of C34, C37, and C41 to this step), and 0072
(the store's signatures) leave some details open: what `run_new` does with a key its approval doesn't cover, how a
call is sized, the questions' exact text, and where the runner's contract checks live. v1's
`src/ema/agent/approval.py` was read for its rules (the approval covers everything that decides a run; the request
shows the command, the files, the environment); nothing was ported, as its rules now live by layer (0057).

## Decision

We will, provisionally:

**The runner**

1. **`run_new` refuses a call its approval can't cover with `ValueError`** (an error in EMA's code, as the store's
   preconditions are, 0070 item 4): an approval of another model version, one answered no, or a next key Q13 says
   isn't approved or already has its run. The workspace approves the resolution it runs, under the run lock, so a
   user never meets it; nothing of that call starts.
2. **A call is the next `batch_size` keys cut to the leading ones Q13 covers** (C37, C48): "never more than remain
   approved", counted when the call starts. A batch model's `batch_size` None is all the new keys in one call; a
   model that isn't a batch function has calls of one run. When no key of the next call is covered, that is the
   refusal (item 1).
3. **Before each call: Q13, then `check_files`** (M16, C34); then `prepare` → `execute` → `collect` → W4 → `keep`
   (record 0071's order). A batch model's every call is stored with its `BatchCall` (its whole time; 0071 item 19).
4. **Any exception before W4 returns, Ctrl-C included, deletes the call's directories**, found from its keys (each
   run directory, and the batch directory), so a `prepare` stopped halfway leaves none either (0028, M14, C41); the
   exception passes through, with every earlier call's runs stored (C49). A failure to delete is ignored, so the
   exception that stopped the call is the one raised.
5. **Progress:** "0/n runs" before the first call, then after each call's W4 and `keep` (PM10, U2's "40/96 runs");
   an exception from the callback passes through after the call's runs are stored (architecture.md §6, Progress).
6. **`run_new`'s loop is a private class, `ema.runner._Loop`,** with one method per step (`next_call`, `check`,
   `call`, `record`, `stopped`, `keep`), so the contract's broken toys are subclasses that change one step (no
   monkeypatching, 0065), as the store's broken toys are `Store` subclasses (0072 item 20). `run_new` is its only
   caller; no public name is added.
7. **`resolve`** keys a row by its point's exact bytes and its replicate, counts a repeated key once, and lists the
   new keys in the design's order of first appearance (P4); a failed current run is reused and counted in
   `reused_failed` once per key, or with `retry_failed` made a new key at the next attempt (0010, C47). It refuses
   a design of another model version, or of another width (`ValueError`). Its one store read is in `_current`, so
   the store's key-only read (record 0072's deferral; `Store.current_keys` on `demo-06-store`) replaces one call.
8. **`price`:** new and reused counted once per distinct key; the time is `new` × Q2's mean over every stored run of
   the model version, any status and attempt; "time unknown" when there is none (P3, U2).
9. **`read_batch` refuses a number of run ids that isn't the design's rows** (`ValueError`); a row is new when its
   run's approval is `new_approval` (E6). **`replay_batch`** builds its `Design` from the provenance's identity,
   the stored points and replicates (Q15 with `points=True`), and its design structure (0062, 0063).
10. **The run lock is the caller's:** `run_new` doesn't check that it is held (architecture.md §6 says the caller
    holds it; the workspace, step 14, takes it).

**Approval**

11. **The approval's text:** "New runs of the model version `name@0123456789ab`: scatter on `y`." (or "the test run
    at the nominal point"), then "Price: …" (P3, U2). On the model version's first approval (Q4: no yes yet, so a
    declined first approval's next question is first too), a blank line and "The model version's first approval:
    what each run starts.", then the command as a JSON list in a code span and "Program: …" (resolved, or "not
    found on the model's PATH"), each input deck's `writes` and template name with the template's text in a fenced
    block; or "Function: …" and "Interpreter: …" (0029); the files ("in each run directory", or "in each batch
    call's directory"), a shared one marked; the environment beyond EMA's base variables (each `env` variable as
    `NAME=value`, each `pass_env` name with "passed from EMA's environment, set" or "not set", never its value, T8),
    or "Environment: EMA's base variables only." `ApprovalRequest.text` holds no prompt: the terminal adds
    "Approve? [y/N]", an elicitation its buttons.
12. **Strings EMA didn't write** (the model's name in the label, a prediction's name, the command, paths, names,
    values, template text) are code spans or fenced blocks, each with a run of backticks longer than any in it
    (fences at least three), padded with a space when it starts or ends with a backtick; hidden characters (Cc but
    tab, Cf but the joiners, Cs, Zl, Zp) are printed as `\uXXXX` (`\UXXXXXXXX` above the BMP), a line feed kept
    only in a block (T7). An empty string is "(empty)".
13. **Only `True` from an approver is a yes;** anything else is a no, and an exception from it is a no, recorded,
    whose reason the `ApprovalDeclined` message gives ("declined: no runs made (the question failed: …)"). **Ctrl-C
    at the question is recorded as a no and passes through** (T3: every question asked is recorded).
14. **`ask_approval` checks** that the price is the resolution's (its new and reused-failed counts), that there are
    new runs (C50), and that `asked_for` matches the request (`TestRunRequest` exactly for the test run), all
    `ValueError`; `approve=None` raises `CannotAsk` first, rendering and recording nothing (T3).
15. **`ask_confirmation`** reads what the name means now from the spec text's `name` and Q3 ("`heat` now means
    `heat@b204…` at `/old/dir/model.json`; saving makes it mean this spec.", 0054); a file at the path with the same
    bytes asks "`…` is already saved, unchanged: load it?" (T6); then "The spec's full text:" and the text in a
    fenced block. It records W2 with the SHA-256 of the text's UTF-8 bytes, refuses a relative path
    (`ValueError`), and raises `ApprovalDeclined` ("declined: no model spec saved") on a no.
16. **`ask`** writes the question, a line feed, and "Approve? [y/N] " ("Confirm? [y/N] " for a confirmation) to
    stderr, never stdout (T9), and reads one line of stdin: "y" or "yes" in any case is a yes; anything else, end of
    input, or no stdin is a no. `ema.ask` is re-exported lazily from the root package.

**Tests**

17. **The runner's contract checks are a module of their own, `tests/contracts/runner.py`:** the runner's parts of
    C46 (`check_reuse`), C47 (`check_failed_reused`), C48 (`check_approval_cap`), C49 (`check_interrupt`), C56
    (`check_design_order`), and C34 (`check_refused_call`), C37 (`check_batch_sizes`), C41 (`check_keep_applied`),
    each with broken toys (contracts.md's negative controls: six-digit keys, retrying unasked, runs counted at
    finish, one transaction per evaluation, the stopped run stored as failed, files hashed once, the last batch
    filled past the approval, no `keep`, a stopped run's directory kept, another order), and the meta-test. The store
    contract's names (`check_reuse`, `check_approval_cap`, ...) are taken in `store.py` by its own checks of the
    same promises, and its implementation is the `Store` class, not the runner.
18. **The toys log each point they are called at** to `TOY_CALLS` when their spec's `env` sets it (the three toys in
    `tests/models`), so a check sees that a refused call never reached the model, even though its directory is
    deleted.
19. **Ctrl-C in the checks is pressed `INTERRUPT_S` (0.1 s) after a progress count,** from a timer started in the
    progress callback, so a loaded machine can't move it into an earlier call.
20. **Tiers:** the fast tier holds the checks over stored runs (C46, C47, C56, with their meta-test) and C48's and
    C49's checks over the Python toy, about 1 s; C34's, C37's, and C41's checks, the command-line variants, the
    meta-test of the checks that run a model, and a batch unit test are slow (about 5 s with `-n auto`).

## Review round 1

The independent review's findings, and the choices their fixes make (each implemented on `demo-07fix`):

21. **A call is also cut at the first key W4 wouldn't store** (M1; P3, I2, I4, M14): Q13 counts only this
    approval's runs, so a stale resolution's key run since under another approval passed it, ran again, had its
    stored run's directory wiped by `prepare`, and was then refused by W4. `next_call` reads the call's keys'
    current runs (`Store.current_keys`) and cuts the call at the first key that isn't runnable: no current run and
    attempt 0, or a failed current run and attempt one more. A first key not runnable is the refusal (`ValueError`,
    item 1). The check `check_run_once` (C46, C48) and its broken toy `AsksQ13Only` (Q13 only) test it, with a unit
    test of a stale retry.
22. **An exception after W4's COMMIT leaves the call stored** (M2; I5, M14, C49): item 4's deletion applies only
    when the call isn't stored, which the loop's `stored` step asks of the store (`get_run` of the call's first key,
    whose id no earlier run has, by item 21; `NotFound` is not stored). A check that is itself interrupted counts
    as stored: keeping a stopped call's directory is safer than deleting a stored run's. In the stored case `keep`
    is applied, an exception from it ignored, and the exception that stopped the call passes through.
23. **Progress "0/n runs" is reported once the first call has passed Q13 and `check_files`**, just before it starts,
    so a refusal of the first call reports nothing (item 5).
24. **`resolve` reads `Store.current_keys`** (record 0072's key-only read; the deferral below is closed) and builds
    each new `RunKey` from the point hash it already computed (`run_id` of it), hashing each point once. At 10⁵
    distinct points over an empty store, the best of four runs took 1.08 s, against 1.51 s before (this machine,
    load average about 28).
25. **`ask_approval` checks, before rendering or asking:** that a design is given exactly for a diagnostic
    evaluation (W3's rule, 0049), and that the store holds the model version (`NotFound`, Q14); on a first approval,
    `check_files(model)` (M16), so the question shows the model version's own templates (`ModelChanged`). Nothing
    is asked or recorded when one fails. The price check of item 14 also compares `reused` (distinct stored runs).
26. **Text EMA didn't write, beyond item 12:** the reason an approver's exception gives in `ApprovalDeclined` is a
    code span (hidden characters as codes, T7); in a path shown in a question (the program or interpreter, a
    template, an input deck, a file, a spec path) a backslash is doubled, so a typed `\u202e` can't pass for a
    hidden character's code.

## Deferrals

- None left: `Store.current_keys` is used by `resolve` and `run_new` (item 24), and `tests/contracts/store.py`'s
  docstring points to `tests/contracts/runner.py` (review round 1).

## Spec edits on acceptance

- `architecture.md` §9: the store contract's row gains "the runner's parts in `tests/contracts/runner.py`" (item
  17), or a row of its own for the runner.
- `architecture.md` §6: `run_new` raises `ValueError` for a call its approval can't cover, or a key run since the
  resolution (items 1, 21), and `NotFound` for an unknown approval; `ask_approval` raises `NotFound` for an unknown
  model version and, on a first approval, `ModelChanged` (item 25); the question's text holds no prompt (item 11).
- `trust.md`, What needs a yes: Ctrl-C at the question is recorded as a no (item 13).

## Alternatives considered

- **A refusal as an `EMAError` (`ApprovalDeclined`):** a user-facing class for a state only a bug in EMA reaches;
  the workspace never runs a resolution it didn't approve.
- **Running the covered keys of a call and refusing the rest at W4:** the model would run outside its approval
  before the refusal (C48's negative control).
- **A public `Loop` class:** a name beyond architecture.md §6's; the private class keeps the public names exact.
- **Detecting a refused call by its directory:** the runner deletes the directory of any call that ends before W4,
  so a call that ran and was then refused looks like one that never ran; the toys' call log tells them apart.
- **Recording nothing on Ctrl-C at the question:** T3 says every question asked is recorded; the user saw it.

## Consequences

- **Size:** `ema.runner` is 189 code lines (without docstrings, comments, and blanks; 394 physical), `ema.approval`
  211 (354): 400 against `architecture.md` §11's 418 (the roadmap's 440); 364 before review round 1.
- **Tests:** the fast tier gains about 1 s (the whole fast tier measured 27.6 s to 30.5 s on this machine under
  other builds' load, against 27.9 s before; the coordinator should measure the merged tier against 30 s).
- **For step 14:** `_evaluate.py` resolves, takes the lock, resolves again, prices, calls `ask_approval`, then
  `run_new` and `read_batch` with the ids it builds from the resolution (`tests/support/runner.py`'s `row_run_ids`
  shows how); `test_model` does the same with a one-row design with no identity and a `TestRunRequest`.
