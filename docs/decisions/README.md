# Decision records

One file per significant decision: what was decided, why, and what follows from it. This is Michael Nygard's
format for Architecture Decision Records (https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).

- **Name:** `NNNN-short-title.md`, numbered in order and never reused. Copy `0000-template.md`.
- **Never edit an accepted record's decision.** If it changes, write a new record that supersedes it, and set
  the old one's status to `superseded by NNNN`.
- **One commit** holds the record, the specs it changes, and the `STATUS.md` update (the OD row moves to
  "Decided").
- **Amending part of a record.** When a record changes part of an accepted record's decision, the older
  record's status becomes `accepted; <part> amended by NNNN`, in the same commit (0052). The older record's text
  is not edited.
- **Plain errors in an accepted spec** (a typo, a wrong citation, a stale cross-reference, a number that
  contradicts its own source) are corrected in place, without a record, and listed in the commit message
  (0052).
- **Claude Code may draft a record** from a conversation, with status `proposed`. Only you set it to
  `accepted`.

Write one when a choice:
- is hard to reverse (the schema, the model interface, naming);
- would otherwise be argued again later (by you, a collaborator, or a new Claude session);
- trades one good thing for another (such as fewer false positives for more false negatives).

## Index

| Record | Title | Status | Date |
|---|---|---|---|
| 0001 | Record decisions in decision records | accepted | 2026-09-28 |
| 0002 | Rebuild v2 in a new repository; keep v1 for reference | accepted | 2026-09-28 |
| 0003 | Call a model's variables model parameters, and what EMA analyzes model predictions | accepted | 2026-09-28 |
| 0004 | Call EMA's intervals variability intervals | accepted | 2026-09-28 |
| 0005 | Call the region a design samples the model parameter space, and make it part of the design | accepted | 2026-09-29 |
| 0006 | Make the diagnostic evaluation, with its report, the unit of work | accepted | 2026-09-29 |
| 0007 | Choose the principles | accepted; P8 superseded by 0008 | 2026-09-29 |
| 0008 | Drop P8; check glossary words only in names and generated text | accepted; its generated-text list amended by 0042 | 2026-09-29 |
| 0009 | Call the models with known answers reference models | accepted | 2026-09-29 |
| 0010 | Reuse failed runs unless the user asks to retry them | accepted | 2026-09-29 |
| 0011 | Let the point run repeat a deterministic model, to measure its noise | accepted | 2026-09-29 |
| 0012 | Put six diagnostics in v2.0 | accepted | 2026-09-29 |
| 0013 | Leave quadrature and sparse grids for a later version | accepted | 2026-09-29 |
| 0014 | Support Python functions and command-line simulation codes in v2.0 | accepted | 2026-09-29 |
| 0015 | Run one model run at a time in v2.0, ready for parallel and remote runs later | accepted; its run-at-a-time wording amended by 0025; its platform question by 0029; its shared files by 0030 | 2026-09-29 |
| 0016 | Ship an MCP server in v2.0, with use case U9 | accepted; its live evals amended by 0050 (later) | 2026-09-29 |
| 0017 | Leave experimental interpretation out of v2.0 | accepted | 2026-09-29 |
| 0018 | Write reports in Markdown with TeX math, and make PDFs with pandoc when it is installed | accepted | 2026-09-29 |
| 0019 | Clarify that P1 covers what EMA produces, including its tool results | accepted | 2026-09-29 |
| 0020 | Keep each run's model output in its run directory, for inspection outside EMA | accepted; its keep values amended by 0028 | 2026-09-29 |
| 0021 | Analyze scalar model predictions of models not declared noisy in v2.0 | accepted | 2026-09-29 |
| 0022 | Let a model have several scalar model predictions, and analyze one per diagnostic evaluation | accepted; its data-model consequence and glossary row amended by 0043 | 2026-09-30 |
| 0023 | Hold a model parameter at its nominal value when a design's space leaves it out | accepted; its held values amended by 0033 | 2026-09-30 |
| 0024 | Put scales in the model parameter space, and a model parameter's limits in the model spec | accepted | 2026-09-30 |
| 0025 | Let a Python function take a batch of points in one call | accepted | 2026-09-30 |
| 0026 | Run every Python model in an isolated child process | accepted | 2026-09-30 |
| 0027 | Read model predictions with regex, JSON, and CSV output parsers | accepted | 2026-09-30 |
| 0028 | Collect every run from files, and keep the run directories of incomplete runs | accepted | 2026-09-30 |
| 0029 | Say what the model version covers, and check it before every call | accepted | 2026-09-30 |
| 0030 | Store large model files once, read-only, and link them into run directories | accepted | 2026-09-30 |
| 0031 | Add "run directory" to the glossary, and say in P3 which files the model version covers | accepted | 2026-09-30 |
| 0032 | Draw uniform points from numpy's PCG64, behind a sampler interface ready for others | accepted; its sampler interface amended by 0033 | 2026-09-30 |
| 0033 | Let a space hold a model parameter at a value, and add design words to the glossary | accepted | 2026-09-30 |
| 0034 | Report numbers without intervals as observations | accepted; its glossary row amended by 0042 | 2026-09-30 |
| 0035 | Call a model prediction constant only when every usable run gives the same value | accepted | 2026-09-30 |
| 0036 | Let a diagnostic result hold observations without estimates or a note | accepted | 2026-09-30 |
| 0037 | Show runs that aren't usable along each model parameter only; two-model-parameter plots later | accepted | 2026-09-30 |
| 0038 | Report each coordinate line's Gram spectrum, and its decay rate as an observation | accepted | 2026-09-30 |
| 0039 | Plot the polynomial model's fit against y; its shadows come with the active subspace | accepted | 2026-09-30 |
| 0040 | Bootstrap the fits and the scatter; no intervals for points and lines | accepted; the polynomial model's row amended by 0041 | 2026-09-30 |
| 0041 | Let an estimate's interval be "none", give the polynomial coefficients intervals, and keep spawn tags out of the report | accepted | 2026-09-30 |
| 0042 | Explain variability intervals once per report, and fix three step-6 slips | accepted | 2026-10-01 |
| 0043 | Fail a run that errs, times out, or exits nonzero, even when its model predictions can be read | accepted | 2026-10-01 |
| 0044 | Compare golden reports by their numbers to four digits; print ASCII minus signs and whole integers | accepted | 2026-10-01 |
| 0045 | Keep the quadratic contract model; give the point run's replicates and z their own fixture rules | accepted | 2026-10-01 |
| 0046 | Include the model version in a design's identity | accepted | 2026-10-01 |
| 0047 | State the unit-coordinate maps, the order of a line's points, and how alpha is read from a float | accepted | 2026-10-01 |
| 0048 | Loosen decay-rate tolerances to what rounding allows, and draw values below a spectrum's axis as open markers | accepted | 2026-10-01 |
| 0049 | Widen approval and price to every new run, give the point design a space, and add the review's glossary rows | accepted | 2026-10-01 |
| 0050 | Leave run budgets and live evals out of v2.0, give export its own spec, and list the later seams in scope | accepted | 2026-10-01 |
| 0051 | Settle the review's smaller rules: empty sections, rank, anchors, spawn streams, and four wordings | accepted | 2026-10-01 |
| 0052 | Give each rule one home, trim the specs' history, and write down the decision conventions | accepted | 2026-10-01 |
