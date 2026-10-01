# Add a model

**Status:** outline. **Use cases:** U1, U2, U6. **Spec:** `../design/model_interface.md`.

> Two paths: a Python function, and a command-line program with an input deck.

## A Python function

1. Write the function; what it takes and returns. <…>
2. Describe its model parameters and model predictions: name, units, description, nominal value, limits
   (scales belong to the model parameter space, 0024). <…>
3. Register it, and see its version. <…>
4. Test it at the nominal point. <…>
5. What happens when it fails, and how to see why. <…>

## A command-line program

1. The input-deck template. <…>
2. The command, the run directory, and the files copied into it. <…>
3. Reading the model predictions from the model output (output parsers). <…>
4. What you approve, and why. <…>
5. Test it at the nominal point; time a few runs. <…>

## The environment and files (`../design/trust.md`)

- What a model sees: the base variables, `pass_env` with an example (`LM_LICENSE_FILE`), and `env`; no secret
  in `env`, which is stored and shown; `DYLD_*` dropped by macOS for protected programs. <…>
- A wrapper script for a command of more than one line, or for a scheduler's or module system's many
  variables. <…>
- Units as plain text or Unicode (`W/m²`), not mathtext. <…>
- A file outside the model's directory: a link to it inside the directory. <…>

## When a model changes

- What makes a new version, and what happens to stored runs. <…>
