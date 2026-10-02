"""The toy program (tests/models/README.md): reads its deck, writes out.json."""

import json
import sys

values = {}
with open(sys.argv[1]) as deck:
    for line in deck:
        name, _, value = line.partition("=")
        values[name.strip()] = value.strip()
with open("mesh.dat") as mesh:
    scale = float(mesh.read().split()[0])
with open("out.json", "w") as out:
    json.dump({"y": float(values["a"]) + 2 * float(values["b"]) + scale}, out)
