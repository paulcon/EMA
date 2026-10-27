# 0089. Keep citations off the documentation site: cite ids in parentheses, and drop them when the site is built

**Date:** 2026-10-27. **Status:** accepted (2026-10-27, by the owner). **Resolves:** none.

## Context

- **The site is public** (0088, `https://paulcon.github.io/EMA/`), and holds the guides and the API reference,
  generated from the docstrings (0059 item 5). A review of the site found that its pages cite design documents
  and ids ("architecture.md §3", "data_model.md §3.2", "0044", "P4"), which read as jargon to a visitor.
- **Docstrings cite ids by rule** (CLAUDE.md, "Cite ids"; `CONTRIBUTING.md`), and keep them (0087 item 2): they
  are a contributor's trail from code to spec. Text users see cites none (0086 item 6, 0087 item 2;
  `tests/unit/test_record_ids.py`, whose `SPEC_ID` already takes a cited spec id to be a parenthesized list that
  holds one).
- **Counted on the site as built today** (2026-10-27): about 2,400 citations on 62 pages, the API reference and
  the guides together. About 60% sit in parentheses that hold only citations ("(0015)", "(designs.md, Shared
  rules; C20–C27)", "(§3.3)"), which a filter can remove without touching the sentence. The other ~870 are part
  of the sentence ("only W6 deletes", "records 0034, 0035, … Each line"), or share a parenthesis with words
  ("(RequestError; 0061, 0062)"); only rewording removes those.
- **Some look-alikes are data:** a reference model's id is its name (`ema.reference_models.path("R2")`, "a
  reference model (R2, Ishigami)"), and numbers such as `0.0001` or `10000000` aren't record ids.
- **Sphinx copies each page's source** to `_sources/` and links it ("Show source"), so a guide's raw Markdown,
  ids included, is on the site too.
- **The guides are outlines** (step 17 writes their full text), each opening with a paragraph of metadata
  (Status, Updated, Use cases, Specs, Tested).

## Decision

1. **The site cites nothing:** no record id, no spec id (P, U, M, G, S, V, C, Q, W, I, T, E, AR, OD, and the
   diagnostics' own, such as CL2), no spec file name, and no section mark, on any page. A reference model's id
   (R1–R11) is a name a user types, and stays. A guide that sends its reader to a spec links it on GitHub, in
   words ("the model interface spec"), not by file name.
2. **The repository keeps every citation, in parentheses.** Docstrings, comments, and the guides cite ids as now,
   but always as a parenthesized citation, never as a word in the sentence: "only W6 deletes" becomes "only
   deleting a diagnostic result removes rows (W6)". Inside a parenthesis, citations are separated from words by
   a semicolon ("(RequestError; 0061, 0062)"). CLAUDE.md's "Cite ids" rule and `CONTRIBUTING.md` say so.
3. **`docs/conf.py` drops the citations when the site is built,** and touches no source file:
   - in each docstring (`autodoc-process-docstring`, which autosummary's summaries also go through), and in each
     guide and `index.md` (`source-read`), code blocks' comments included: it drops each semicolon-separated part
     of a parenthesis that is a citation (it starts with an id, a spec file name, or `§`), then the parenthesis
     if nothing is left; a parenthesis may span lines;
   - in each guide, it replaces the opening metadata paragraph with its status alone ("**Status:** outline.");
   - it sets `html_copy_source` and `html_show_sourcelink` to false, so no page's source is published.
4. **The build checks it:** at `build-finished`, `docs/conf.py` scans every HTML page's text, code included, for a
   citation (item 1's ids, bare or in parentheses; `*.md`; `§`), and warns once per page with the text it found.
   `-W` makes a warning an error, so the docs command (CLAUDE.md) fails, and `docs.yml` publishes nothing. Data
   that looks like an id is listed by name, in an allowlist beside the pattern, each entry with its reason. The
   patterns are `tests/unit/test_record_ids.py`'s where they agree, so the two rules read alike.
5. **Build it as one step,** with its plan (`docs/plans/18-site-citations.md`) and branch
   (`build-18-site-citations`), before step 17: the filter and the check first, with their tests (the filter's
   cases, from the Context's examples, as known answers), then the rewording, module by module, until the docs
   command passes. Its stop condition: the docs command, the full tests, and lint pass; a fresh agent's review
   of the rendered site and of a sample of reworded docstrings finds nothing major; the owner reviews. Step 17
   writes the guides' full text under item 2's rule.

## Alternatives considered

- **Filter only** (no rewording): about 2–3 hours, but about a third of the citations stay, mid-sentence, with a
  note to explain them; the site is half cleaned.
- **A note and links only** (the review's suggestion): an hour, no source change, but every citation stays on
  the site.
- **Strip the ids from the source:** the simplest site, but contributors lose the trail from code to spec, and
  CLAUDE.md's rule and 0087 item 2 end.
- **A marked field for citations** (a last "Implements:" line in each docstring, dropped from the site): one
  place to look, but every docstring's citations move away from the sentences they support.
- **Drop the reference models' ids too:** they are the names `ema.reference_models.path` takes, so a guide
  without them couldn't say which model to load.
- **Keep the guides' metadata paragraph, or drop it whole:** the first is all citations; the second hides that a
  guide is an outline.

## Consequences

- **0088's status** becomes `accepted; item 1's content amended by 0089` (the site holds the guides and the API
  reference without their citations). 0087 item 2 is unchanged: docstrings keep their ids.
- **`../../CLAUDE.md`** ("Cite ids": in parentheses, so the site can drop them, 0089) and **`CONTRIBUTING.md`**
  (the same line).
- **Code:** docstrings and comments throughout `src/ema/` reworded in place, about the same number of lines; the
  source-line budget is measured at the step's end. `docs/conf.py` gains the filter and the check (it isn't in
  `ema`, so outside the budget). The guides reworded where an id is part of a sentence.
- **Tests:** the filter's known answers; the check runs in every docs build.
- **Effort:** about a day, with the review; no paid API. The site is redeployed by the owner after the merge.
- **What gets harder:** a new docstring must cite in parentheses, or the docs build fails; a new kind of id, or
  data that looks like one, means changing the pattern or the allowlist.
