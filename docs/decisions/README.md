# Decision records

One file per significant decision: what was decided, why, and what follows from it. This is Michael Nygard's
format for Architecture Decision Records (https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).

- **Name:** `NNNN-short-title.md`, numbered in order and never reused. Copy `0000-template.md`.
- **Never edit an accepted record's decision.** If it changes, write a new record that supersedes it, and set
  the old one's status to `superseded by NNNN`.
- **One commit** holds the record, the specs it changes, and the `STATUS.md` update (the OD row moves to
  "Decided").
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
| 0008 | Drop P8; check glossary words only in names and generated text | accepted | 2026-09-29 |
| 0009 | Call the models with known answers reference models | accepted | 2026-09-29 |
| 0010 | Reuse failed runs unless the user asks to retry them | accepted | 2026-09-29 |
| 0011 | Let the point run repeat a deterministic model, to measure its noise | accepted | 2026-09-29 |
| 0012 | Put six diagnostics in v2.0 | accepted | 2026-09-29 |
| 0013 | Leave quadrature and sparse grids for a later version | accepted | 2026-09-29 |
| 0014 | Support Python functions and command-line simulation codes in v2.0 | accepted | 2026-09-29 |
| 0015 | Run one model run at a time in v2.0, ready for parallel and remote runs later | accepted | 2026-09-29 |
| 0016 | Ship an MCP server in v2.0, with use case U9 | accepted | 2026-09-29 |
| 0017 | Leave experimental interpretation out of v2.0 | accepted | 2026-09-29 |
| 0018 | Write reports in Markdown with TeX math, and make PDFs with pandoc when it is installed | accepted | 2026-09-29 |
| 0019 | Clarify that P1 covers what EMA produces, including its tool results | accepted | 2026-09-29 |
| 0020 | Keep each run's model output in its run directory, for inspection outside EMA | proposed | 2026-09-29 |
| 0021 | Analyze scalar model predictions of models not declared noisy in v2.0 | accepted | 2026-09-29 |
