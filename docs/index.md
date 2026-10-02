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

.. Step 08: figures and reports (a block of its own, to ease merging).

.. autosummary::
   :toctree: _autosummary

   ema.plotting.figures
   ema.report.render
   ema.report.pdf
```
