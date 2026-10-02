# 0008. Drop P8; check glossary words only in names and generated text

**Date:** 2026-09-29. **Status:** accepted; its generated-text list amended by 0042 (one allowed sentence) and 0065 (four words). **Resolves:** none (TODO step 1). **Supersedes:** 0007 in part
(P8).

## Context

Record 0007 adopted P8, "The glossary's words": code, documents, reports, and messages use the glossary's
words and none in its Avoid column, checked by a terminology test that parses `../design/glossary.md` and
scans docs, report templates, golden reports, error messages, and code identifiers.

Checking the glossary against the accepted specs showed what a test over all prose would need:
- allowed exceptions in each row ("input deck", "input file", and "output parser", which 0003 allows; "model
  output", a glossary term that contains "output");
- a way to handle Avoid entries that apply only in context: "output" for a model prediction, "code" for the
  model, "parameter" alone, "box" and "domain" for the model parameter space;
- a way to tell a mention from a use: 0004 allows "confidence interval" to explain the difference, and P8's
  own Why line quotes the words it avoids;
- a list of exempt files: the glossary, the decision records, and `../notes/`.

Each can be solved, but the rules would grow, and the clean-ups they force would be about wording choices
that don't matter to the application.

What does matter is narrower:
- **Public names in code** (classes, fields, arguments, CLI commands and flags, data card keys) are hard to
  change once people use them. v1's words come back by default, through ported code and through Claude's
  habits.
- **Text EMA generates for users** (reports, figure labels, CLI and error messages) is what a user reads. A
  report that calls a variability interval a confidence interval misstates what it shows (0004).

Records 0003 and 0004 each list a terminology test among their consequences, without saying which text it
scans.

## Decision

We will drop P8 from the principles, and keep a narrow terminology test.

- **P8 is removed.** P1–P7 stand as in `../design/principles.md`. The id P8 is not reused.
- **The terminology test scans two things only:**
  - public identifiers in the `ema` package: module, class, function, argument, and field names; CLI
    commands and flags; data card keys;
  - text EMA generates for users: report templates, golden reports, figure labels, and CLI and error messages.
- **It checks a short list of words that are always wrong in those places.** The list starts with the words
  records have decided against and that have no legitimate use there:
  - in identifiers: `qoi`, `box`, `DiagnosticRun` (0003, 0005, 0006);
  - in generated text: "confidence interval", "CI", "credible interval", "error bar" (0004), "QoI" (0003),
    "box" (0005).

  "Input" and "output" are not on the list: they have legitimate uses ("input deck", "model output", "output
  parser") that only context tells apart. A word joins the list when a decision record decides against it.
- **Documents are not scanned.** In prose, the glossary's Avoid column is advice, applied in review. The
  glossary's header says so, and names the words the test checks.

## Alternatives considered

- **Keep P8 as accepted:** its test would need allowed exceptions, context rules, a mention-vs-use rule, and
  exempt files, which is more machinery than the benefit warrants, and it would fail on the draft specs until
  each is rewritten.
- **Keep P8, narrowed to names and generated text:** it would say what this record says, but a principle is
  heavier than a lint rule needs. Records 0003 and 0004 already commit to the test; this record gives it a
  scope.
- **Drop P8 and the test:** the lightest, but it contradicts the consequences of 0003 and 0004, and it loses
  the protection that matters most: public names, which are hard to change later, and the text users read.

## Consequences

- **`../design/principles.md`:** P8 is removed.
- **`../../CLAUDE.md`:** the P8 line goes. "Use its words in code, docs, and messages" stays, as guidance.
- **Record 0007:** its status becomes "accepted; P8 superseded by 0008". The rest of 0007 stands.
- **`../design/glossary.md`:** the header is rewritten: the Avoid column advises on prose, and the test checks
  only the list above, in names and generated text. Rows no longer need allowed exceptions or context rules
  for the test's sake.
- **Records 0003 and 0004:** their terminology test is this narrow test.
- **The terminology test** is written with the first build step that creates public names, and grows as
  modules and report templates are added.
- **The draft specs** (`architecture.md`, `data_model.md`, and others) keep v1's words until each is
  rewritten, as 0003, 0005, and 0006 say; no test fails on them.
- **Harder later:** drift in the documents' prose is caught only in review.
