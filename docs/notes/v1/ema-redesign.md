# EMA Redesign

Feeling like I lost control of the architecture. Want to make it simpler. And I want to work better with Claude Code. 

## Principles
Claude Code does well with structured design principles. 
- Numbers come from tools, not LLM calcs.
- Interpretations are experimental. 

## Guides
- Get started
- Link a model to EMA 
- Run a diagnostic 
- Define a diagnostic

## Workflow for a diagnostic

1. Choose a model.
2. Choose a diagnostic, and enter the parameters needed for that diagnostic.
   - Design parameters
3. Execute the model at each point of the design
4. Compute the values and intervals of the diagnostic.
5. Create a report with diagnostic results. 

## Scheduler

Run the model at the given design points. Return NaN if model fails. Any way to get an explanation for failures? 

If the model has a true parallel flag, then send all the inputs to the model at once. 

## Diagnostics

### TODO
- Taylor test
- Sparse fit
- Low-rank fit
- Ridge fit
- Lipschitz matrix
- SIR/SAVE (others?)
- Morris OAT

### Point run

| **User provides** | model, point (nominal), number of repeats (zero) |
| **Design** | given point |
| **Compute** | None |
| **Plots** | None |
| **Report** | output value, variation across repeats |

### Scatter plots

| **User provides** | model, ranges, n points, which inputs to scatter (all) |
| **Design** | uniform random |
| **Compute** | none |
| **Plots** | output versus each input (name, units), hist of output |
| **Report** | output mean, output ranges |

### Coordinate plots

| **User provides** | model, ranges, n points per line |
| **Design** | one line per input, n uniformly space points in range |
| **Compute** | Fourier transform |
| **Plots** | output versus each line with labels (name, units), Fourier transform |
| **Report** |  |

Range with no length means no plot.

### Random line plots

| **User provides** | model, ranges, m lines, n points per line |
| **Design** | one line per random anchor/direction, n uniformly spaced points |
| **Compute** | Fourier transform |
| **Plots** | output versus inputs for each anchor/direction, Fourier transform |
| **Report** |  |

### Linear model

| **User provides** | model, ranges, level |
| **Design** | uniform convergent |
| **Compute** | least squares, VI |
| **Plots** | 1d shadow, coefficients with VI, hist of residual |
| **Report** | residual norm |

n_min is d+1

### Polynomial model
Does this generalize quadratic and Sobol?

| **User provides** | model, ranges, degree |
| **Design** | convergent uniform |
| **Compute** | least-squares, AS, Sobol, VI |
| **Plots** | 1d shadow, 2d shadow, Sobol 1st and Total with VI, eigenvals with VI, activity scores with VI, 1st and 2nd eigenvecs with VI, Fourier decay |
| **Report** | additivity, low-d structure, residual |

n_min is (degree + dimension \chose degree)

## Designs

### Uniform design
Given: ranges, n

### Convergent design
Given: ranges, error factor alpha, level, n_min
Wraps uniform design

### Line design
Given: n points, anchor, direction, ranges

### Plane design
TODO

### Integration grids?
Do I need these? 
- QMC
- randomized QMC
- tensor grids
- sparse grids
- various weight functions for Gauss quad

## Databases
Tables for the database

### Designs: 
- id
- ranges
- type
- collection of run ids

### Runs: 
- id
- input
- output
- model
- time
- parallel flag

### Models: 
- id
- function name
- param list (param has name, description, unit, nominal)
- output of interest
- description
- parallel flag

### Diagnostics:
- id
- which diagnostic
- design
- model
- reference to reports

## Utilties
This would be a good place to list subproblems that arise in several places
- Vandermonde with Legendre basis
- Multi-index stuff

## Glossary

Use my nomenclature and connect to other nomenclature. Like "variation intervals" compared to _confidence intervals_ or _credible intervals_. This may help the chatbot.

## Chatbot

### Uses
- Set up a model
- Run a diagnostic
- Measure cost of runs

### Experimental
Review the diagnostics. Look at the plots. Provide an interpretation. Suggest the presence of structure. Provide caveats. Suggest next steps. Suggestions on how to exploit the structure.

## Objects

### ModelParameter:
- name
- units
- description
- scale (linear, log)
- nominal value
- constraint (like positivity)

### Model
- id
- Interface name
- List of ModelParameters
- Interface name
- Output name and units
- Model description
- Speed of evaluation
- Parallel flag

