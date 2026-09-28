# Glossary

**Status:** candidates listed. **Updated:** <YYYY-MM-DD>.

> One word per idea, in your nomenclature, linked to the standard terms so readers (and the agent) can
> connect them. The code, the docs, and the messages use these words. Avoid the synonyms in the last column;
> a test can check for them, as v1's `test_terminology.py` did.
>
> Terms marked OD-n wait on that decision in `STATUS.md`.

| Term | Meaning | Standard terms it relates to | Avoid |
|---|---|---|---|
| model | a program or function that maps parameter values to outputs | simulator, computational model | code (for the model) |
| model version | a model's spec plus the contents of its files, identified by a hash | | |
| model parameter (OD-3) | one of a model's variables that a design sets | input, input variable, factor | input parameter |
| nominal value | a parameter's default or best-guess value | base point, reference point | |
| ranges / box (OD-3) | [low, high] for each parameter: the region a design samples | input space, parameter space, design space, domain | |
| output | a quantity a run returns | quantity of interest (QoI), response | |
| design | a set of points to run, made by a design generator | design of experiments, sample, experimental design | |
| run | one evaluation of a model version at one point | model evaluation, simulation, sample | model call |
| diagnostic | a design plus a computation plus figures and a report section, that looks for one kind of structure | sensitivity analysis method, test | diagnostic test |
| result | what a diagnostic computed: numbers with intervals, counts, notes, figures | | |
| estimate | a number with its interval and the method that made the interval | | |
| variation interval (OD-4) | <your definition> | confidence interval, credible interval, bootstrap interval | |
| note | a caveat about the data: failed runs, too few runs, a constant output | | warning |
| figure | an image plus its data card | plot | |
| data card | the JSON beside a figure recording what it shows | | |
| report | the Markdown a diagnostic produces: header, results, figures, provenance | | |
| workspace | the directory holding the database and stored files | | |
| approval | the user's yes to an action that runs or saves something | | |
| budget | the most runs or seconds a request may use | | |
| provenance | the record of where a result came from | | |
| experimental | interpretation or advice, labelled apart from results (OD-8) | | beta |
| <…> | <…> | <…> | <…> |
