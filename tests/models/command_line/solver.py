"""The toy program: reads its deck, writes out.json and w to stdout; ``mode`` picks its behaviour
(tests/support/models.py)."""

import json
import os
import sys

values = {}
with open(sys.argv[1]) as deck:
    for line in deck:
        name, _, value = line.partition("=")
        values[name.strip()] = value.strip()
a, b, mode = float(values["a"]), float(values["b"]), int(float(values["mode"]))
if os.environ.get("TOY_CALLS"):  # the runner's tests: each point the toy is called at (tests/support/runner.py)
    with open(os.environ["TOY_CALLS"], "a") as calls:
        calls.write(json.dumps([a, b, float(values["mode"])]) + "\n")
with open("mesh.dat") as mesh:
    scale = float(mesh.read().split()[0])
y = a + 2 * b + scale
if mode == 2:
    import signal

    os.kill(os.getpid(), signal.SIGKILL)
if mode == 3:
    import subprocess
    import time

    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    with open("pids.json", "w") as out:
        json.dump({"child": child.pid, "self": os.getpid()}, out)
    time.sleep(60)
if mode == 4:
    with open("inspect.json", "w") as out:
        json.dump(
            {
                "env": dict(os.environ),
                "stdin": sys.stdin.read(),
                "pid": os.getpid(),
                "argv": sys.argv,
                "deck": values,
                "cwd": os.getcwd(),
            },
            out,
        )
if mode == 5:
    with open("mesh.dat", "a") as mesh:
        mesh.write("1")
if mode == 7:
    sys.exit(0)
if mode == 8:
    print("err-line", file=sys.stderr)
with open("out.json", "w") as out:
    out.write('{"y": NaN}' if mode == 6 else json.dumps({"y": y}))
if mode != 9:
    print(f"w = {a - b!r}")
sys.exit(1 if mode == 1 else 0)
