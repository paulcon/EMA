# Glossary

**Status:** candidates listed. **Updated:** 2026-09-29.

> One word per idea, in your nomenclature, linked to the standard terms so readers (and the agent) can
> connect them. The code, the docs, and the messages use these words. Avoid the synonyms in the last column;
> a test can check for them, as v1's `test_terminology.py` did.
>
> Terms marked OD-n wait on that decision in `STATUS.md`.

| Term | Meaning | Standard terms it relates to | Avoid |
|---|---|---|---|
| model | a program or function that maps model parameter values to model predictions | simulator, computational model | code (for the model) |
| model version | a model's spec plus the contents of its files, identified by a hash | | |
| model parameter | one of a model's variables whose value a design sets (0003) | input, input variable, factor | input, input parameter |
| nominal value | a model parameter's default or best-guess value | base point, reference point | |
| model parameter space | the set of model parameter values a design may sample; each design has exactly one, and it belongs to the design, not the model (0005) | parameter space, input space, domain, design space, hyperrectangle, hyperellipsoid | box, input box, input space, domain, design space |
| model parameter ranges | one [low, high] per model parameter: one way to define a model parameter space, as the sides of a hyperrectangle or the axes of a hyperellipsoid (0005) | bounds | box |
| model prediction | a quantity EMA reads from a run and analyzes, with a name, units, and a shape (0003; OD-9) | quantity of interest (QoI), response, output | output (for a model prediction), QoI |
| model output | anything a run produces: a Python function's return value, or the files, logs, and streams a command-line program writes; model predictions are read from it (0003) | simulation output, output files | |
| design | a set of points in one model parameter space at which to run the model, made by a design generator; short for experimental design | design of experiments, sample, experimental design | |
| run | one evaluation of a model version at one point | model evaluation, simulation, sample | model call |
| noisy | said of a model whose model predictions can differ between runs of the same model version at the same point; a model is treated as noisy only when its spec says so or repeated runs have measured the variation, and is deterministic otherwise (P7). Noise is the model's own variation, not a variability interval, which is about the runs behind an estimate (0004) | stochastic, nondeterministic, stochastic simulator | |
| replicate | one of several runs of a noisy model version at the same point, numbered from 0; a deterministic model has only replicate 0 (P7) | replication, repeated run | |
| diagnostic | a formula or method that produces the diagnostic result for a given model and design, looking for one kind of structure (0006) | sensitivity analysis method, test | diagnostic test |
| diagnostic evaluation | one execution of a diagnostic for a particular model and design, which produces the numbers of the diagnostic result; the unit of work (0006) | | diagnostic run |
| diagnostic parameter | a setting of a diagnostic that the user chooses, such as the number of points or the seed; not a model parameter (0003) | hyperparameter, option | parameter (alone, where it could mean a model parameter) |
| diagnostic result | what a diagnostic evaluation produces: estimates with their variability intervals, counts, notes, figures | | |
| estimate | a number with its variability interval and the method that made the interval | | |
| variability interval | how much an estimate changes when the runs behind it change (resampled, refined, or held out), reported with its method and settings; it carries no coverage probability (0004) | confidence interval, credible interval, bootstrap interval | confidence interval, CI, credible interval, error bar (except to explain the difference) |
| note | a caveat about the data: failed runs, too few runs, a constant model prediction | | warning |
| figure | an image plus its data card | plot | |
| data card | the JSON beside a figure recording what it shows | | |
| report | the Markdown a diagnostic evaluation produces: header, the diagnostic result, figures, provenance | | |
| workspace | the directory holding the database and stored files | | |
| approval | the user's yes to a diagnostic evaluation's new runs, given after EMA shows their price; it covers everything that decides what those runs do (P3) | | |
| budget | the most runs or seconds a request may use | | |
| provenance | the record of where a diagnostic result came from | | |
| experimental | interpretation or advice, labelled apart from diagnostic results (OD-8) | | beta |
| <…> | <…> | <…> | <…> |
