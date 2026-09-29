# The decision workflow

**Written:** 2026-09-29. A short guide to how decisions are made and recorded in EMA v2. The rules themselves
are in `../decisions/README.md`, `../../STATUS.md`, `../../CLAUDE.md`, and decision record 0001; where this
guide and those files differ, those files win.

## The pieces

| Piece | Where | What it is | Who changes it |
|---|---|---|---|
| Open decision (OD-n) | a row in `STATUS.md`, "Open decisions" | a question still to answer, with options, a suggestion, and the steps it blocks | the owner or Claude, as questions come up |
| Decision record (NNNN) | `docs/decisions/NNNN-title.md` | what was decided, why, the alternatives, and what follows | Claude may draft it as `proposed`; only the owner sets `accepted` |
| Spec | `docs/design/*.md` | what to build | edited freely while `draft`; once `accepted`, changed only through a new decision record |

## A decision's life

```text
 question comes up          owner decides         owner accepts           later, if it changes
 ──────────────────► OD-n ──────────────► record ──────────────► record ──────────────────────► new record
   (row in STATUS.md)        (proposed)   (accepted)   supersedes it;
                                                        old one marked
                                                        "superseded by NNNN"
```

1. **Open.** A question gets an OD row in `STATUS.md`. Its "Blocks" column names the TODO steps that can't
   finish without it.
2. **Discuss and draft.** The owner decides, often in a conversation with Claude. Claude drafts the record
   from `../decisions/0000-template.md`, with status `proposed`, and adds it to the index in
   `../decisions/README.md`.
3. **Edit and accept.** The owner rewrites whatever isn't in their words, and sets the status to `accepted`.
4. **Apply, in one commit.** The commit holds:
   - the record;
   - the specs it changes;
   - the `STATUS.md` update: the OD row moves to "Decided", naming the record.
5. **Never edit an accepted record.** If the decision changes, a new record supersedes it, and the old one's
   status becomes `superseded by NNNN`.

The reason for the strictness: in v1, decisions lived in memory notes, plan files, and CLAUDE.md, and several
were argued again or rediscovered in later sessions (record 0001, "Context").

## How decisions gate the code

- Claude builds only from `accepted` specs. When a spec is silent or unclear, Claude asks rather than
  choosing.
- Before changing anything an accepted spec says, Claude checks `docs/decisions/`. If a new decision is
  needed, Claude drafts one as `proposed`, and waits for the owner to accept it.
- A TODO step is done when its specs are `accepted` and its OD rows are decided, with records.
- Going over a size budget in `docs/design/scope.md` is a decision too: it needs a record, not a drift.

## Open question about the workflow

When does an OD row move to "Decided"? `STATUS.md` and `../decisions/README.md` imply it moves in the commit
that applies the decision, but OD-1 was moved while its record, 0002, was still `proposed`. Two readings:

- **(a)** a row moves only when its record is `accepted`;
- **(b)** a row moves when the owner has decided, and the record's status catches up later.

Until this is settled (for example, in record 0001 before it is accepted), (a) is the safer reading.
