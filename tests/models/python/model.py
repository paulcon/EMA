"""The toy function: its behaviour is chosen by the model parameter ``mode`` (tests/support/models.py)."""

import json
import os
import subprocess
import sys
import time

from helper import scale

STARTED_WITH = os.environ.get("OMP_NUM_THREADS")
print("printed at import")


def f(a, b, mode):
    if os.environ.get("TOY_CALLS"):  # the runner's tests: each point the toy is called at (tests/support/runner.py)
        with open(os.environ["TOY_CALLS"], "a") as calls:
            calls.write(json.dumps([a, b, mode]) + "\n")
    mode = int(mode)
    y = a + 2 * b + scale()
    if mode == 1:
        return y / 0
    if mode == 2:
        os._exit(3)
    if mode == 3:
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
                    "received": {"a": a, "b": b, "mode": mode},
                    "started_with": STARTED_WITH,
                    "cwd": os.getcwd(),
                    "sys_path": sys.path,
                },
                out,
            )
    if mode == 5:
        with open("mesh.dat", "a") as mesh:
            mesh.write("1")
    if mode == 6:
        return {"y": float("nan"), "z": y + 1}
    if mode == 7:
        return {}
    if mode == 8:
        print("out-line")
        print("err-line", file=sys.stderr)
    if mode == 9:
        return {"y": y, "extra": 2.0}
    if mode == 10:
        return "abc"
    return {"y": y, "z": y + 1}
