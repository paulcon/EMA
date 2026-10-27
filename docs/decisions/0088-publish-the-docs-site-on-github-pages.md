# 0088. Publish the documentation site at paulcon.github.io/EMA, from a workflow started by hand

**Date:** 2026-10-27. **Status:** accepted (2026-10-27, by the owner). **Resolves:** none.

## Context

- **Record 0059 item 5** builds the Sphinx site "locally, not published": the guides and the API reference, with
  `design/`, `decisions/`, `notes/`, `plans/`, and `checks/` excluded. Its Context says the repository is
  private, and that GitHub Pages for a private repository needs a paid plan.
- **The repository is now public,** at `github.com/paulcon/EMA` (moved 2026-10-27, 49d91f5). GitHub Pages is
  free for a public repository, and so are its Actions minutes on the standard runners.
- **`paulcon.github.io` is the owner's homepage,** served from the root of `paulcon/paulcon.github.io`'s
  `master` branch (`index.html`, `constantine.bib`). A project site of `paulcon/EMA` is served at
  `paulcon.github.io/EMA/`, beside it, without touching that repository.
- **The site builds today** with `-W`, in about a minute: the four guides, each with status `outline`, and the API
  reference. The guides cite the design documents by relative path, as code, not as links (`docs/conf.py`), so
  nothing on the site links to a page that isn't there.
- **The checks run only when the owner starts them** (0059 item 7, `checks.yml`, `workflow_dispatch` only); a
  full run takes 30–35 minutes. A `workflow_dispatch` workflow can be started only once its file is on the
  default branch.

## Decision

1. **Publish the site at `https://paulcon.github.io/EMA/`,** with GitHub Pages on `paulcon/EMA`, its source set
   to GitHub Actions. What the site holds is unchanged from 0059 item 5: the guides and the API reference, with
   the same exclusions. The guides are published as they stand, outlines included, with their status lines.
2. **Deploy from a new workflow, `.github/workflows/docs.yml`, started by hand** (`workflow_dispatch` only), on
   Linux and Python 3.14:
   - one job, which runs only on `main` (`if: github.ref == 'refs/heads/main'`), so a branch is never published;
   - `uv sync --locked`, then the docs command (`uv run sphinx-build -W --keep-going docs docs/_build/html`), so
     a warning stops the publish;
   - `actions/configure-pages`, `actions/upload-pages-artifact` (`docs/_build/html`), and
     `actions/deploy-pages`, with `pages: write` and `id-token: write` only, the `github-pages` environment, and
     one deployment at a time (`concurrency: pages`, not cancelled in progress).

   The owner starts it after a merge to `main` that changes the guides or the docstrings
   (`gh workflow run docs.yml --ref main`). `checks.yml` is unchanged, and keeps the site as its run's artifact.
3. **One version is published:** the latest that the owner deployed from `main`. No site per release, and no
   previews of branches or pull requests. Adding one later: a folder per release tag, and a version switcher, in
   about half a day; the seam to keep is that the workflow uploads one directory, the Sphinx build's output.
4. **Point to the site** from `README.md` (Documentation), `pyproject.toml` (`[project.urls]`: `Documentation`
   and `Repository`), and `docs/conf.py`'s docstring ("published by `docs.yml`" in place of "not published").
   The local command stays the gate before a step is reported done (CLAUDE.md, `CONTRIBUTING.md`).
5. **Turn Pages on once, as staged steps for the owner** (each is a change to the remote), each with its stop
   condition:
   1. Merge and push to `main` the commit that applies this record. Stop when `docs.yml` is on `main` on GitHub.
   2. Turn on Pages with Actions as its source: `gh api -X POST repos/paulcon/EMA/pages -f build_type=workflow`.
      Stop when `gh api repos/paulcon/EMA/pages` shows `"build_type": "workflow"` and
      `"html_url": "https://paulcon.github.io/EMA/"`.
   3. Start the workflow: `gh workflow run docs.yml --ref main`, then `gh run watch`. Stop when the run passes and
      `https://paulcon.github.io/EMA/` shows the site, with `paulcon.github.io` itself unchanged.

## Alternatives considered

- **Keep the site local** (0059 item 5): nothing public to keep current, but the guides and the API reference are
  read only by those who clone and build.
- **The root of `paulcon.github.io`:** the shortest address, but it replaces the owner's homepage.
- **A folder of `paulcon/paulcon.github.io`** (`paulcon.github.io/ema/`): no Pages setting on `paulcon/EMA`, but
  every publish commits generated HTML to the homepage's repository, from a build in another repository.
- **A `gh-pages` branch, pushed from the owner's Mac** (ghp-import, or a worktree by hand): no workflow, but
  generated HTML in the repository's history, a `.nojekyll` file so `_static/` is served, and either a new tool
  or a manual procedure.
- **A deploy job in `checks.yml`:** only a commit that passes every check is published, but each publish waits
  30–35 minutes, and fixing a guide's typo needs a full run.
- **Deploy on every push to `main`:** never stale, but Actions run only when the owner starts them (0059 item 7).
- **Read the Docs:** versions and previews built in, but another service and account, and a configuration file
  of its own.

## Consequences

- **0059's status** becomes `accepted; item 5's "not published" amended by 0088`. Its text, the Context's
  "private" included, is not edited.
- **Files on acceptance:** `.github/workflows/docs.yml` (new); `docs/conf.py`'s docstring; `README.md`'s
  Documentation section (the site's link before the local command); `pyproject.toml`'s `[project.urls]`;
  `STATUS.md` (Done); this index's row and 0059's status. No spec in `docs/design/` changes, and no code in
  `src/`; the source-line budget is unchanged.
- **What is public grows from the repository to a site that search engines index:** the guides, outlines
  included, and every public name's docstring. Nothing new is exposed, since the repository is public, but the
  site is easier to find, and a stale deploy is read as current until the owner starts the workflow again.
- **Cost:** none in money (Pages and Actions minutes are free for a public repository); about 2 minutes a run.
- **Undoing it:** `gh api -X DELETE repos/paulcon/EMA/pages` takes the site down; `docs.yml` can stay or go.
