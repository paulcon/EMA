# Notes for the EMA redesign. 

- Define an abstract base diagnostic along including an abstract DiagnosticResult.
- Define the data model for the database. This is like schema?
- Define the diagnostics. Look ahead to all diagnostics when considering the abstraction. Implement a few important diagnostics to start. 
- Define the architecture of the code. Including its interfaces. 
- Write some basic use cases. 
- Package structure
- Look up Python Hypothesis package
- Look up pytest
- Ask Claude to manage version hash
- What is the record format for traces and costs? How do I design that?
- Write a ROADMAP.md

## Package structure
- ema.core
- ema.diagnostics
- ema.report
- ema.models

## Data model
- Table for models
- Table for runs
- Table for diagnostics
- Table for designs
- Table for interpretations
- Table for reports

## Rules
- 

## Glossary
- diagnostic
- report
- model
- llm
- design
- run
- input
- output
- model parameter
- model type
  - input deck
  - python function
  - string (safety concerns)
- diagnostic interpretation
- diagnostic result
- seed
- rule
- budget

## Classes
- Diagnostic base
- Result base
- Model base
- Design base
- Run base
- Scheduler base
- Report base
- ModelParameter base
- ModelInterface base
- ModelQOI base
- 