"""Canonical encodings, hashes, and ids: every rule of data_model.md §3.4 in one place (architecture.md §3).

The model version's hash came with model loading (step 03); the approval id and the reuse key come with the steps
that first use them (the runner, the workspace).
"""

import hashlib
import json
import re
import struct
from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from ema.types.model import ModelSpec

_HEX_ID = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class TrackedFile:
    """A file a model version covers: its path, its contents' hash, and whether it is shared (0030, 0031).

    Attributes
    ----------
    path : str
        Relative to the model spec's directory, with "/".
    sha256 : str
        The SHA-256 of its contents, as 64 hex digits.
    shared : bool
        Stored once, read-only, and linked into every run directory.
    """

    path: str
    sha256: str
    shared: bool


def canonical_json(x: object) -> str:
    """Encode as canonical JSON (data_model.md §3.4): sorted keys, compact, non-ASCII kept, no NaN.

    A double is written by its ``repr``, the shortest decimal that reads back exactly, so every double
    round-trips, -0.0 and subnormals included (C17); integers stay integers.

    Parameters
    ----------
    x
        JSON data: dicts with string keys, lists or tuples, strings, numbers, bools, and None.

    Returns
    -------
    str
        The canonical text.

    Raises
    ------
    ValueError
        For NaN or infinity, which can't be written (a missing value is ``null``).

    Examples
    --------
    >>> canonical_json({"b": [1.5, None], "a": "≈"})
    '{"a":"≈","b":[1.5,null]}'
    """
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256_hex(data: bytes | str) -> str:
    """Return the SHA-256 of bytes, or of text's UTF-8, as 64 hex digits."""
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


def point_hash(point: Sequence[float] | np.ndarray) -> str:
    """Hash a point: the SHA-256 of its doubles as little-endian IEEE float64 bytes, 8·d bytes (§3.4).

    The point is complete, in the model spec's order of model parameters. Exact bits: -0.0 and 0.0 are
    different points (P3).

    Parameters
    ----------
    point
        The point's d values.

    Returns
    -------
    str
        64 hex digits.
    """
    return hashlib.sha256(np.ascontiguousarray(point, dtype="<f8").tobytes()).hexdigest()


def run_id(model_version_id: str, point_hash: str, replicate: int, attempt: int) -> str:
    """Return a run's id (data_model.md §3.4, 0061 item 6).

    The SHA-256 of the model version id and the point hash as hex text (UTF-8), then the replicate and the
    attempt, each an 8-byte little-endian integer.

    Parameters
    ----------
    model_version_id, point_hash
        64 hex digits each.
    replicate, attempt
        Integers >= 0.

    Returns
    -------
    str
        64 hex digits.

    Raises
    ------
    ValueError
        For a negative replicate or attempt.
    """
    if replicate < 0 or attempt < 0:
        raise ValueError(f"a replicate and an attempt are >= 0, not {replicate} and {attempt}")
    data = (model_version_id + point_hash).encode("utf-8") + struct.pack("<qq", replicate, attempt)
    return hashlib.sha256(data).hexdigest()


def _hex_ids(run_ids: np.ndarray | Sequence[str] | Sequence[bytes]) -> list[str]:
    if isinstance(run_ids, np.ndarray):
        if run_ids.dtype == np.uint8 and run_ids.ndim == 2 and run_ids.shape[1] == 32:
            return [row.tobytes().hex() for row in run_ids]
        if run_ids.dtype.kind in "SV" and run_ids.dtype.itemsize == 32:
            raw = np.ascontiguousarray(run_ids).tobytes()
            return [raw[i : i + 32].hex() for i in range(0, len(raw), 32)]
        run_ids = run_ids.tolist()
    ids: list[str] = []
    for i in run_ids:
        text = i.hex() if isinstance(i, bytes) and len(i) == 32 else i
        if not isinstance(text, str) or not _HEX_ID.fullmatch(text):
            raise ValueError(f"not a run id: {i!r}")
        ids.append(text)
    return ids


def batch_call_id(run_ids: np.ndarray | Sequence[str] | Sequence[bytes]) -> str:
    """Return a batch call's id (data_model.md §3.4).

    The SHA-256 of its runs' ids as hex text (UTF-8), in call order, with no separator.

    Parameters
    ----------
    run_ids
        The runs' ids, as 64-hex-digit strings, 32-byte ``bytes``, an ``(n, 32)`` uint8 array, or an array of
        32-byte fixed-width bytes; each is taken as its hex form, so all hash the same.

    Returns
    -------
    str
        64 hex digits.

    Raises
    ------
    ValueError
        For anything that isn't a run id.
    """
    return sha256_hex("".join(_hex_ids(run_ids)))


def decimal_fraction(x: float | str) -> Fraction:
    """Read alpha as the decimal it is written as (0047).

    ``Fraction(repr(x))`` for a float, the text itself for a string, so 0.7072 is 7072/10000, not the nearest
    double.

    Parameters
    ----------
    x
        A finite float, or a decimal number's text.

    Returns
    -------
    fractions.Fraction
        The exact decimal.

    Raises
    ------
    ValueError, TypeError
        For NaN, infinity, a bool, or text that isn't a number.

    Examples
    --------
    >>> decimal_fraction(0.7072), decimal_fraction("0.9")
    (Fraction(442, 625), Fraction(9, 10))
    """
    if isinstance(x, bool) or not isinstance(x, (float, int, str)):
        raise TypeError(f"not a decimal number: {x!r}")
    return Fraction(x if isinstance(x, str) else repr(x))


def model_version_label(name: str, model_version_id: str) -> str:
    """Show a model version as always: "name@" and the id's first 12 hex digits (model_interface.md).

    Examples
    --------
    >>> model_version_label("heat", "b204a1" + "0" * 58)
    'heat@b204a1000000'
    """
    return f"{name}@{model_version_id[:12]}"


def version_hash(spec: "ModelSpec", files: Sequence[TrackedFile]) -> str:
    """Return a model version's id (data_model.md §3.4; M3, 0029).

    The SHA-256 of the canonical JSON of ``{"spec": …, "files": […]}``: the spec as ``versioned_json`` writes it
    (every field, each default filled in, without its location, ``keep``, ``batch_size``, and ``timeout_s``), and
    each tracked file as ``[relative path, sha256 of its contents, shared]``, sorted by path. The digests are
    given: reading and hashing the files is ``ema.models``'s (architecture.md §1).

    Parameters
    ----------
    spec
        The model spec.
    files
        Its tracked files: the Python function's file, the input deck templates, and the listed files.

    Returns
    -------
    str
        64 hex digits.
    """
    tracked = [[f.path, f.sha256, f.shared] for f in sorted(files, key=lambda f: f.path)]
    return sha256_hex(canonical_json({"spec": json.loads(spec.versioned_json()), "files": tracked}))
