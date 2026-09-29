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
| 0001 | Record decisions in decision records | proposed | 2026-09-28 |
| 0002 | Rebuild v2 in a new repository; keep v1 for reference | proposed | 2026-09-28 |
| 0003 | Call a model's variables model parameters, and what EMA analyzes model predictions | accepted | 2026-09-28 |
| 0004 | Call EMA's intervals variability intervals | accepted | 2026-09-28 |
| 0005 | Call the region a design samples the model parameter space, and make it part of the design | accepted | 2026-09-29 |
| 0006 | Make the diagnostic evaluation, with its report, the unit of work | accepted | 2026-09-29 |
