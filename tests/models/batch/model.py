"""The toy function as a batch (tests/models/README.md)."""


def f(X):
    with open("mesh.dat") as file:
        scale = float(file.read().split()[0])
    return X[:, 0] + 2 * X[:, 1] + scale
