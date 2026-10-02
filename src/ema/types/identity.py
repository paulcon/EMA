"""Canonical encodings, hashes, and ids: every rule of data_model.md §3.4 in one place (architecture.md §3).

The model version's hash, the approval id, and the reuse key come with the steps that first use them (model
loading, the runner, the workspace).
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
    from collections.abc import Mapping

    from ema.types.requests import Request, TestRunRequest

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


#: How ids are held in arrays (record 0070): 32 raw bytes each. A ``V32`` element keeps trailing zero bytes,
#: which an ``S32`` element would drop.
ID_DTYPE = np.dtype("V32")


def id_array(ids: np.ndarray | Sequence[str] | Sequence[bytes]) -> np.ndarray:
    """Return ids as a new ``(n,)`` array of ``ID_DTYPE``, from any form ``batch_call_id`` takes.

    The one rule for ids given to a type (record 0070, review round 1): 64 hex digits each, 32-byte ``bytes``,
    an ``(n, 32)`` uint8 array, or an array of 32-byte fixed-width elements, ``ID_DTYPE`` included.

    Raises
    ------
    ValueError
        For anything that isn't an id.
    """
    raw = b"".join(bytes.fromhex(i) for i in _hex_ids(ids))
    return np.frombuffer(raw, dtype=ID_DTYPE).copy()


def _is_id(value: object) -> bool:
    """Tell whether ``value`` is an id's text: 64 lowercase hex digits (data_model.md §3.2)."""
    return isinstance(value, str) and _HEX_ID.fullmatch(value) is not None


def hex_ids(ids: np.ndarray | Sequence[str] | Sequence[bytes]) -> tuple[str, ...]:
    """Return ids as 64 hex digits each, from any form ``batch_call_id`` takes (an ``ID_DTYPE`` array included)."""
    return tuple(_hex_ids(ids))


_VERSION_KEYS = ("ema", "matplotlib", "numpy", "scipy")
_ASKED_FOR = ("diagnostic_evaluation", "test_run")


def approval_id(
    model_version_id: str,
    asked_for: str,
    request: "Request | TestRunRequest",
    new: int,
    reused: int,
    n_before: int,
) -> str:
    """Return an approval's id (data_model.md §3.4; 0062).

    The SHA-256 of the canonical JSON of ``{"model_version_id", "asked_for", "request", "new", "reused",
    "n_before"}``: the request in its canonical form, and the number of approvals stored before it in the
    workspace, so two identical questions asked twice get two ids.

    Parameters
    ----------
    model_version_id
        The model version priced.
    asked_for
        "diagnostic_evaluation" with a ``Request``, or "test_run" with a ``TestRunRequest``.
    request
        What the approval is for.
    new, reused, n_before
        Counts, each >= 0.

    Returns
    -------
    str
        64 hex digits.

    Raises
    ------
    ValueError
        For another ``asked_for``, one that doesn't match the request, or a negative count.
    """
    form = request.canonical()
    if asked_for not in _ASKED_FOR or (asked_for == "test_run") != ("test_run" in form):
        raise ValueError(f"an approval for {asked_for!r} doesn't match its request {type(request).__name__}")
    if min(new, reused, n_before) < 0:
        raise ValueError(f"an approval's counts are >= 0, not {new}, {reused}, {n_before}")
    key = {
        "model_version_id": model_version_id,
        "asked_for": asked_for,
        "request": form,
        "new": new,
        "reused": reused,
        "n_before": n_before,
    }
    return sha256_hex(canonical_json(key))


def reuse_key(
    model_version_id: str,
    request: "Request",
    run_ids: np.ndarray | Sequence[str],
    versions: "Mapping[str, str]",
) -> str:
    """Return a diagnostic result's reuse key; its SHA-256 is the result's id (data_model.md §3.4; C50, 0054).

    The canonical JSON of ``{"model_version_id", "request", "run_ids", "versions"}``: the canonical request, the
    ids of the runs the design resolves to, in design order, as hex text, and the versions of EMA, numpy, scipy,
    and matplotlib (0062).

    Parameters
    ----------
    model_version_id
        The model version analyzed.
    request
        The canonical request.
    run_ids
        One per design row, in design order, in any form ``batch_call_id`` takes.
    versions
        Exactly the keys "ema", "numpy", "scipy", and "matplotlib".

    Returns
    -------
    str
        The key's canonical JSON.

    Raises
    ------
    ValueError
        For other version keys, or anything in ``run_ids`` that isn't an id.
    """
    if tuple(sorted(versions)) != _VERSION_KEYS:
        raise ValueError(f"versions must name exactly {', '.join(_VERSION_KEYS)}, not {sorted(versions)}")
    key = {
        "model_version_id": model_version_id,
        "request": request.canonical(),
        "run_ids": _hex_ids(run_ids),
        "versions": dict(versions),
    }
    return canonical_json(key)
