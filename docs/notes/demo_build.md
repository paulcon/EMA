# Demo build log (2026-10-01 onward)

> The coordinating session's log of the autonomous build on the `demo` branch (record 0066): the waves, each
> step's record, and each review round's findings and fixes. A note, not a spec.

## Goal

A working demo of EMA through its MCP server (`ema mcp --root DIR`, U9) by the end of 2026-10-02: an MCP client
loads a reference model, is shown the price, approves, runs the diagnostics, and reads the report with its
figures.

## Waves

Steps are the roadmap's (`docs/notes/build_roadmap.md`), with T added (0066 item 2). Steps in one wave are built
at once, in worktrees on `demo-NN-<topic>`, and merged into `demo`.

| Wave | Steps | Records |
|---|---|---|
| 1 | 01 scaffolding and designs; 02's first task (BLAS determinism, measured beside it) | 0067; 02a in 0068 |
| 2 | 02 numerics; 03 model specs and loading; T the rest of `ema.types` | 0068; 0069; 0070 |
| 3 | 04 and 05 running a model (command line, then Python); 06 the store; 08 figures and reports | 0071; 0072; 0073 |
| 4 | 07 runner and approval; 09 diagnostics base, the point run, and the reference models | 0074; 0075 |
| 5 | 10 scatter; 11 coordinate lines and lines; 12 linear model; 13 polynomial model | 0076; 0077; 0078; 0079 |
| 6 | 14 the workspace | 0080 |
| 7 | 15 the MCP server; 16 the CLI | 0081; 0082 |
| 8 | 17 the demo, guides, and a last review | 0083 |

## Rounds

Each wave's review rounds: the findings (counted by severity), what was fixed, and what was left, with why.
