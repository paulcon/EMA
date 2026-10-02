# EMA

EMA runs diagnostics on computational models to find exploitable structure, and reports the results with
figures, numbers, and their intervals.

## Guides

```{toctree}
:maxdepth: 1

guides/get_started
guides/add_a_model
guides/run_a_diagnostic
guides/add_a_diagnostic
```

## API reference

The public names of the modules that exist so far (`architecture.md`), one page per module.

```{eval-rst}
.. autosummary::
   :toctree: _autosummary

   ema.types.errors
   ema.types.text
   ema.types.streams
   ema.types.identity
   ema.types.model
   ema.types.space
   ema.types.design
   ema.types.runs
   ema.types.results
   ema.types.requests
   ema.types.summaries
   ema.numerics.basis
   ema.numerics.gram
   ema.numerics.fitting
   ema.numerics.sobol
   ema.numerics.stats
   ema.numerics.intervals
   ema.numerics.tolerance
   ema.designs.samplers
   ema.designs.generators
   ema.designs.point
   ema.designs.uniform
   ema.designs.convergent
   ema.designs.lines
   ema.models.spec
   ema.models.files

   ema.models.prepare
   ema.models.execute
   ema.models.collect
   ema.models.parsers
   ema.models.processes
   ema.models.sandbox
```

The store (step 06):

```{eval-rst}
.. autosummary::
   :toctree: _autosummary

   ema.store.store
   ema.store.records
   ema.store.layout
   ema.store.lock
   ema.store.migrations
.. Step 08: figures and reports (a block of its own, to ease merging).

.. autosummary::
   :toctree: _autosummary

   ema.plotting.figures
   ema.report.render
   ema.report.pdf

.. Step 09: the diagnostics' base, the point run, and the reference models (a block of its own, to ease merging).

.. autosummary::
   :toctree: _autosummary

   ema.diagnostics.base
   ema.diagnostics.point_run
   ema.reference_models

.. Step 10: scatter (a block of its own, to ease merging).

.. autosummary::
   :toctree: _autosummary

   ema.diagnostics.scatter
```

The runner and approval (step 07):

```{eval-rst}
.. autosummary::
   :toctree: _autosummary

   ema.runner
   ema.approval
```
