# Run a diagnostic and read its report

**Status:** outline. **Use cases:** U1–U5, U7, U8. **Specs:** `../design/diagnostics/`, `../design/uncertainty.md`.

1. Choose a diagnostic: the list, and each one's spec. <…>
2. Choose the model parameter space (ranges and scales) and the diagnostic parameters. <…>
3. Price it: new runs, stored runs reused, time, budget. <…>
4. Run it: what you're asked to approve. <…>
5. Read the report:
   - the header: model version, model parameter space, design, run counts, failed runs; <…>
   - each number and its interval, and what the interval means; <…>
   - the figures and their data cards; <…>
   - the notes. <…>
6. Find it again later, and export its runs; open `runs.csv` as data, not as a spreadsheet's formulas
   (`../design/trust.md`). <…>
