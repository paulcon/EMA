# Add a model

**Status:** outline. **Use cases:** U1, U2, U6. **Spec:** `../design/model_interface.md`.

> Two paths: a Python function, and a command-line program with an input deck.

## A Python function

1. Write the function; what it takes and returns. <…>
2. Describe its parameters and outputs: name, units, description, nominal value, scale. <…>
3. Register it, and see its version. <…>
4. Test it at the nominal point. <…>
5. What happens when it fails, and how to see why. <…>

## A command-line program

1. The input-deck template. <…>
2. The command, the run directory, and the files copied into it. <…>
3. Reading the outputs (parsers). <…>
4. What you approve, and why. <…>
5. Test it at the nominal point; time a few runs. <…>

## When a model changes

- What makes a new version, and what happens to stored runs. <…>
