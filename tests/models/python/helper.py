"""A helper module the toy function imports, listed in the spec's files."""


def scale():
    with open("mesh.dat") as f:
        return float(f.read().split()[0])
