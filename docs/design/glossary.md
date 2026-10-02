# Glossary

**Status:** accepted. **Updated:** 2026-10-01 (records 0022–0024, 0031, 0033, 0034, 0039, 0041–0043, 0049,
0050, 0055, 0057, 0061).

> One word per idea, in your nomenclature, linked to the standard terms so readers (and the agent) can
> connect them. The code, the docs, and the messages use these words. The Avoid column is advice for prose,
> applied in review; documents are not scanned (record 0008).
>
> A terminology test checks only public identifiers in `ema` (modules, classes, functions, arguments, fields,
> CLI commands and flags, data card keys) and the text EMA generates for users (report templates, golden
> reports, figure labels, CLI and error messages), for a short list of words that are always wrong there:
> - in identifiers: `qoi`, `box`, `DiagnosticRun`;
> - in generated text: "confidence interval", "CI", "credible interval", "error bar", "QoI", "box"; except
>   "confidence interval" in the one sentence each report with estimates opens its Estimates section with
>   (`EXPLAIN_INTERVALS`, `diagnostics/shared.md`; 0042).
>
> A word joins the list when a decision record decides against it.
>
> Spelling is American (labeled, color, analyze).

| Term | Meaning | Standard terms it relates to | Avoid |
|---|---|---|---|
| model | a program or function that maps model parameter values to model predictions | simulator, computational model, simulation code | user code, model code, model program (0057) |
| model version | a model's spec (except its location, `keep`, `batch_size`, and `timeout_s`) plus the contents of the files the spec names, identified by a hash (0029) | | |
| model spec | the user's description of a model: how EMA runs it, its model parameters and nominal values, its model predictions, and whether it's noisy; it holds no model parameter space (0005). The model spec (except its location, `keep`, `batch_size`, and `timeout_s`) and the contents of the files it names make a model version (0029, 0049) | model configuration, model definition | |
| model parameter | one of a model's variables whose value a design sets; a design that doesn't vary it holds it at its nominal value, or at a held value its model parameter space gives (0003, 0023, 0033) | input, input variable, factor | input, input parameter |
| nominal value | a model parameter's default or best-guess value | base point, reference point | |
| model parameter space | the set of model parameter values a design may sample; each design has exactly one (the point design's holds every model parameter at the point, 0049), and it belongs to the design, not the model (0005) | parameter space, input space, domain, design space, hyperrectangle, hyperellipsoid | box, input box, input space, domain, design space |
| model parameter ranges | one [low, high] per model parameter: one way to define a model parameter space, as the sides of a hyperrectangle or the axes of a hyperellipsoid (0005) | bounds | box |
| limits | the values of a model parameter outside which the model isn't defined, given in the model spec; a model parameter space must stay inside them (0024) | bounds, constraints, domain of definition | |
| scale | whether a design spreads a model parameter evenly in its value (linear) or its logarithm (log); part of the model parameter space (0024) | log scale, transformation | |
| unit coordinates | each varied model parameter mapped to [−1, 1], through its logarithm on a log scale (`designs.md`, 0047); "the unit cube" is [0, 1)^d, the sampler's (C28, 0049) | | |
| model prediction | a quantity EMA reads from a run and analyzes, with a name and units; a scalar in v2.0, and a model may have several; one that a run couldn't read is NaN, with its reason (0003, 0021, 0022) | quantity of interest (QoI), response, output | output (for a model prediction), QoI |
| range (of a model prediction) | max − min over the usable runs; every tolerance on a model prediction is relative to it (P6, 0049) | | |
| model output | anything a run produces: a Python function's return value, or the files, logs, and streams a command-line program writes; model predictions are read from it (0003) | simulation output, output files | |
| input deck | a command-line model's own input files, which EMA writes from a template with a point's model parameter values (0003) | input file | |
| output parser | what reads model predictions from a command-line model's model output (0003, 0027) | | |
| design | a set of points in one model parameter space at which to run the model, made by a design generator; short for experimental design | design of experiments, sample, experimental design | |
| design generator | what makes a design from a model parameter space (or, for the point design, a point) and its diagnostic parameters, with its size computed before it is built; v2.0 has point, uniform, convergent, and lines (given, coordinate, or random); a new kind of design is a new design generator (`designs.md`, 0033) | sampling scheme, design of experiments method | |
| sampler | what makes the points of a uniform or convergent design in the unit cube, with the rate at which an estimate's error is assumed to fall; part of the design's identity; v2.0 has `random` (0032, 0033) | random number generator, quasi-Monte Carlo sequence, low-discrepancy sequence | |
| nested | said of two designs when the smaller one's points are points of the larger, so the larger reuses the smaller's runs; `designs.md` says which designs are nested, and in what (0033) | nested designs, extensible sequence, sequential design | |
| point | one value for each model parameter, held ones included (0023); a design is a set of points, and a run is made at one point | design point, sample point, parameter vector | |
| run | one evaluation of a model version at one point, as one replicate (P7) | model evaluation, simulation, sample | |
| call | one execution of a model by EMA: a run, or a batch call of a Python function (0025, 0049) | | |
| test run | one run at the nominal point, made by `test_model` to check a model, priced and approved like any new run; a stored run like any other (U1, 0049) | | |
| run directory | the directory a run is prepared, executed, and collected in, at `<workspace>/runs/<run id>/`; it holds what the run saw and wrote (its input decks, its files, copied or linked, and its streams) and a record of the run, and is kept or deleted by the model spec's `keep` setting (0015, 0020, 0028, 0030) | working directory, scratch directory | workdir |
| noisy | said of a model whose model predictions can differ between runs of the same model version at the same point; a model is treated as noisy only when its spec says so or repeated runs have measured the variation, and is deterministic otherwise (P7). Noise is the model's own variation, not a variability interval, which is about the runs behind an estimate (0004) | stochastic, nondeterministic, stochastic simulator | |
| replicate | one of several runs of a noisy model version at the same point, numbered from 0; a deterministic model has only replicate 0, except the point run's repeats (P7, 0011) | replication, repeated run | |
| failed run | a run whose call raised, crashed, exited nonzero, couldn't start, or timed out (whatever it wrote), or for which EMA couldn't write its own file in the run or batch directory (0057), or that finished cleanly with none of its model predictions read; it is stored with its kind, its reason, and NaN model predictions, and reused like any stored run unless the user asks to retry (P6, 0010, 0043) | | |
| usable run | a run that is ok and read the model prediction a diagnostic evaluation analyzes; a failed run, or one missing that model prediction, is not usable (P6, 0022, 0049) | | |
| reference model | a model with known answers, used to test EMA's diagnostics and as an example for users; ids R1, R2, … (`reference_models.md`, 0009) | test function, benchmark problem | sample model |
| diagnostic | a formula or method that produces the diagnostic result for a given model and design, looking for one kind of structure (0006) | sensitivity analysis method, test | diagnostic test |
| diagnostic evaluation | one execution of a diagnostic for a particular model and design, which produces the numbers of the diagnostic result; the unit of work (0006) | | diagnostic run |
| request | what one diagnostic evaluation is asked for: the model prediction, the diagnostic, its parameters, the model parameter space, and the seed; with the model version, it decides the design (P4, 0006, 0046, 0049, 0061) | | |
| reuse key | what makes a request a repeat: its model version, the request, the runs its design resolves to, and EMA's and the libraries' versions; a request whose reuse key has a stored diagnostic result gets that result (C50, 0054, 0055) | cache key | |
| diagnostic parameter | a setting of a diagnostic that the user chooses, such as the number of points or the seed; not a model parameter (0003) | hyperparameter, option | parameter (alone, where it could mean a model parameter) |
| diagnostic result | what a diagnostic evaluation produces: estimates, observations, counts, notes, and figures, and the provenance recorded with them (P5, 0034); never interpretation (P2) | | |
| estimate | a number with its variability interval and the method that made the interval; the interval is "none", with the reason, when the method gives none for that diagnostic evaluation (`uncertainty.md`, 0041) | | |
| observation | a number whose spec gives it no variability interval (or a cell saying why there is none, such as "failed (timeout)" or "missing"), read or computed directly from a diagnostic evaluation's usable runs, such as a run's model prediction, or the minimum and maximum of the runs; it describes the runs, not the model over its model parameter space (0034) | observed value, sample statistic, summary statistic | |
| variability interval | how much an estimate changes when the runs behind it change (resampled, refined, or held out), reported with its method and settings; it carries no coverage probability (0004) | confidence interval, credible interval, bootstrap interval | confidence interval, CI, credible interval, error bar (except to explain the difference) |
| note | a caveat about the data: failed runs, too few runs, a constant model prediction, a noisy model (P6, P7) | | warning |
| figure | an image plus its data card | plot | |
| shadow plot | a figure of the model prediction against the model parameters, in unit coordinates, projected on the first one (1-D) or two (2-D) eigenvectors of the gradient's second-moment matrix of a fitted approximation; for a linear fit, on the direction of its slopes (0039) | sufficient summary plot | |
| data card | the JSON beside a figure recording what it shows | | |
| report | the Markdown a diagnostic evaluation produces: a header, the diagnostic result with its figures, and its provenance | | |
| user | the person who runs EMA, from Python, the CLI, or through an MCP client (0061) | | analyst |
| workspace | the directory holding the store | | |
| store | the database and files in a workspace that keep runs, diagnostic results with their provenance, and approvals (P1, P3, P5) | | |
| approval | the user's answer to new runs (a diagnostic evaluation's, or the test run's), given after EMA shows their price; only a yes lets them run, and a no is stored too; it covers everything that decides what those runs do (P3, 0049, 0061) | | |
| confirmation | the user's answer to saving a model spec an MCP client drafted, after EMA shows it in full; only a yes saves it (0016, 0061); not an approval, which is about runs (0049) | | |
| price | what new runs will cost, stated before any of them runs (a diagnostic evaluation's, or the test run's): how many runs are new, how many are reused, and the estimated time, or "unknown" (P3, 0049) | cost estimate | |
| budget | the most runs or seconds a request may use (later; not in v2.0, 0050) | | |
| provenance | the record of where a diagnostic result came from | | |
| experimental | the label for interpretation: any comparison of an estimate with a heuristic threshold, and anything that says what a number means or what to do next; never part of a diagnostic result or a report's main body, and kept in its own section (P2; none in v2.0, 0017) | interpretation | beta |
| heuristic threshold | a number chosen by judgment that an interpretation compares an estimate against; a named constant, documented in the spec that uses it (P2) | | |
