# Purpose

**Status:** accepted. **Updated:** 2026-09-28.

## What EMA is for

Modern computer simulations involve complex models with many model parameters. Despite the complexity, the map from model parameters to model predictions may admit simplifying structures that can be exploited when studying model behavior across a range of conditions as in uncertainty quantification, design optimization, model calibration, and reduced-order modeling.

The exploratory model analysis methodology applies diagnostics to computational models to generate evidence of exploitable structures such as smoothness, regularity, and various concepts of low effective dimension. Diagnostics are derived from numerical methods; these methods may have guarantees on cost and/or accuracy under precise mathematical conditions on the problem or application. However, in practice, the user does not know whether these precise conditions are satisfied in a given problem. By reframing the methods as diagnostics, the exploratory model analysis methodology provides evidence for or against the structures assumed in mathematically rigorous cost and accuracy guarantees.

EMA is an application that implements the exploratory model analysis methodology. EMA interfaces with a computational model, applies diagnostics that involve sampling the model at many different model parameter values, and reports the results to support assessments of the presence of exploitable structure.

## Who uses it

An EMA user is a scientist or engineer who brings a computational model to be analyzed. The user is an expert in the computational model's scientific domain and the system the model represents. The user understands the use, meaning, and significance of both model parameters and model predictions. The user may have preconceived notions about which model parameters are important or how the model predictions change as the model parameters change. EMA makes the diagnostic results easy to read (labels, physical units, variability intervals, notes), and the results provide the user insight into the model behavior. The user may use EMA's reports to inform later parameter studies involving the computational model, such as which methods to use for efficient uncertainty quantification, design optimization, model calibration, and reduced-order modeling.

## What a user gets

The computational model may be a Python function or an external simulation code executed by command line and specified by an input deck; the external simulation code writes files containing the model predictions to the file system. EMA provides the user a guide to building an interface to the computational model; the interface drives diagnostics. The user chooses a diagnostic from an available set. Diagnostics are evaluated by running the model at many different model parameter values. A model run may take a long time on the user's computer, and the run may fail. EMA estimates the time to complete a diagnostic, asks before running the model, and manages failed runs.

Once a diagnostic completes, EMA produces a report with the diagnostic results. The report includes plots that show evidence of relationships between model parameters and model predictions. Reports include variability intervals for all estimates produced by diagnostics. Plots that show the estimates include the computed variability intervals. Interpreting the results in light of the domain science is left to the user.

EMA also keeps a database record of model runs, and the user can reuse model runs across diagnostics as well as export the runs for use in other tools. EMA records the data and metadata needed to reproduce the diagnostic and its results.

## What EMA is not

EMA is not any of the following:
- a model calibration tool,
- an uncertainty quantification (UQ) software package (though diagnostics derive from UQ methods),
- a workflow manager,
- a surrogate modeling tool (though diagnostics may use fitted surrogates).

EMA does not guarantee that any structure is present in any computational model; diagnostics are not guarantees. Diagnostic results depend on the model parameter ranges and diagnostic parameters the user chooses; changes in these values may change diagnostic results.

## Where the ideas come from

The ideas for EMA are broadly inspired by the philosophy behind John Tukey's exploratory data analysis. Most diagnostics are derived from numerical methods in uncertainty quantification, statistical learning, approximation theory, reduced-order modeling, and numerical analysis. The description of each diagnostic contains citations to relevant background literature.