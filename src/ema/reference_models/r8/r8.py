"""R8 (reference_models.md): R7 as a command-line program. Standard library only.

Usage: ``python3 r8.py x.in``. Reads the model parameters from the input deck (``name = value``, one per line) and
R7's constants from the shared file ``table.dat``, and writes ``y = <value>`` to ``out.txt``, the value written
exactly (``repr``).
"""

import sys


def read(path):
    values = {}
    with open(path, encoding="utf-8") as deck:
        for line in deck:
            if line.strip():
                name, value = line.replace("=", " ").split()
                values[name] = float(value)
    return values


def main(deck):
    x = read(deck)
    table = read("table.dat")
    kink, jump = table["kink"], table["jump"]
    a, b, c, e = x["a"], x["b"], x["c"], x["e"]
    y = max(0.0, a + e - kink) + (1.0 if b > jump else 0.0) + 1.0 / (1.0 + 4.0 * (c * c)) + 0.0 * x["f"] + 0.0 * x["g"]
    with open("out.txt", "w", encoding="utf-8") as out:
        out.write(f"y = {y!r}\n")


if __name__ == "__main__":
    main(sys.argv[1])
