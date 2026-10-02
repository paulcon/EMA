"""The toy function as a batch: its behaviour is chosen by the column ``mode`` (tests/support/models.py)."""

import json
import os
import subprocess
import sys
import time

import numpy as np


def f(X):
    with open("mesh.dat") as file:
        scale = float(file.read().split()[0])
    mode = X[:, 2].astype(int)
    y = X[:, 0] + 2 * X[:, 1] + scale
    if (mode == 1).any():
        raise ZeroDivisionError("division by zero")
    if (mode == 2).any():
        os._exit(3)
    if (mode == 3).any():
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        with open("pids.json", "w") as out:
            json.dump({"child": child.pid, "self": os.getpid()}, out)
        time.sleep(60)
    if (mode == 4).any():
        with open("inspect.json", "w") as out:
            json.dump(
                {
                    "env": dict(os.environ),
                    "stdin": sys.stdin.read(),
                    "pid": os.getpid(),
                    "received": X.tolist(),
                    "cwd": os.getcwd(),
                    "sys_path": sys.path,
                },
                out,
            )
    if (mode == 5).any():
        with open("mesh.dat", "a") as mesh:
            mesh.write("1")
    if (mode == 7).any():
        return {}
    if (mode == 8).any():
        print("out-line")
        print("err-line", file=sys.stderr)
    if (mode == 10).any():
        return X[:, :2]
    return np.where(mode == 6, np.nan, y)
