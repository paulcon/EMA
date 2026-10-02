"""``ema.plotting``: labels, the strip, open markers, and data cards (shared.md, Figures; S9, S10; C12; 0048, 0049;
T10; record 0073)."""

import json
import math
import zlib

import matplotlib
import numpy as np
import pytest
from matplotlib import cbook

from ema import plotting
from ema.types.identity import id_array, sha256_hex
from ema.types.results import Figure
from ema.types.runs import FailureKind

IDS = id_array([sha256_hex(f"run {i}") for i in range(6)])


def draw(out_dir, name="scatter_a"):
    """A scatter figure as the diagnostics will draw it: points, bin means, a strip, the axes, and the card."""
    fig, (ax,) = plotting.new_figure(1)
    x = np.array([0.1, 0.5, 0.9, 1.3])
    y = np.array([1.0, 2.0, 1.5, 3.0])
    plotting.points(ax, x, y)
    plotting.bin_means(ax, np.array([0.1, 0.9]), np.array([0.5, 1.3]), np.array([1.5, 2.25]))
    strip = plotting.strip(ax, np.array([0.2, 1.7]), [FailureKind.ERROR, FailureKind.TIMEOUT], False, run_ids=IDS[4:])
    plotting.title(ax, "a")
    panel = {
        "x": plotting.axis(ax, "x", "a", "m", extent=(0.0, 2.0)),
        "y": plotting.axis(ax, "y", "T_max", "K"),
        "points": plotting.card_points(IDS[:4], x=x, y=y),
        "not_usable": strip,
    }
    return plotting.save(fig, {"panels": [panel]}, str(out_dir), name, "T_max against a.")


def test_axis_label():
    """shared.md, Figures: `name [units]`, or `name` when dimensionless."""
    assert plotting.axis_label("T_max", "K") == "T_max [K]"
    assert plotting.axis_label("y", "") == "y"


def test_axis_label_escapes_dollars():
    """T10: a spec's units print literally, never as mathtext."""
    label = plotting.axis_label("x", r"$\input{/etc/hosts}$")
    assert label == r"x [\$\input{/etc/hosts}\$]"
    assert not cbook.is_math_text(label)


def test_save_writes_the_png_and_its_card(tmp_path):
    figure = draw(tmp_path)
    assert figure == Figure("scatter_a", "scatter_a.png", "scatter_a.json", "T_max against a.")
    png = (tmp_path / "scatter_a.png").read_bytes()
    assert png.startswith(b"\x89PNG")
    text = (tmp_path / "scatter_a.json").read_text(encoding="utf-8")
    card = json.loads(text)
    assert text == json.dumps(card, sort_keys=True, indent=2, ensure_ascii=False) + "\n"  # S10's form
    assert card["name"] == "scatter_a"
    panel = card["panels"][0]
    assert panel["x"] == {"label": "a [m]", "units": "m", "scale": "linear", "extent": [0.0, 2.0]}
    assert panel["y"]["label"] == "T_max [K]" and len(panel["y"]["extent"]) == 2
    assert [p["run_id"] for p in panel["points"]] == [sha256_hex(f"run {i}") for i in range(4)]
    assert panel["points"][1] == {"run_id": sha256_hex("run 1"), "x": 0.5, "y": 2.0}
    assert panel["not_usable"] == [
        {"run_id": sha256_hex("run 4"), "x": 0.2, "kind": "error"},
        {"run_id": sha256_hex("run 5"), "x": 1.7, "kind": "timeout"},
    ]


def test_cards_and_pngs_are_byte_identical_on_rerun(tmp_path):
    """S10: the data card byte-identical on rerun; the PNG too, on one machine, with no timestamp or Software."""
    draw(tmp_path / "one")
    draw(tmp_path / "two")
    for suffix in ("json", "png"):
        assert (tmp_path / "one" / f"scatter_a.{suffix}").read_bytes() == (
            tmp_path / "two" / f"scatter_a.{suffix}"
        ).read_bytes()
    png = (tmp_path / "one" / "scatter_a.png").read_bytes()
    assert b"Software" not in png and b"tIME" not in png


def test_a_card_must_be_strict_json(tmp_path):
    fig, _ = plotting.new_figure(1)
    with pytest.raises(ValueError, match="strict JSON"):
        plotting.save(fig, {"panels": [{"y": math.nan}]}, str(tmp_path), "bad", "")
    with pytest.raises(ValueError, match="name"):
        plotting.save(fig, {"name": "other"}, str(tmp_path), "bad", "")
    assert not (tmp_path / "bad.png").exists()


def test_card_points_converts_numpy_and_ids():
    points = plotting.card_points(IDS[:2], x=np.array([1, 2], dtype=np.int64), y=np.array([0.5, np.float32(0.25)]))
    assert points == [
        {"run_id": sha256_hex("run 0"), "x": 1, "y": 0.5},
        {"run_id": sha256_hex("run 1"), "x": 2, "y": 0.25},
    ]
    assert plotting.card_points(None, k=np.arange(2)) == [{"k": 0}, {"k": 1}]  # computed numbers: no run id (C12)
    with pytest.raises(ValueError):
        plotting.card_points(IDS[:2], x=np.arange(3))


def test_strip_draws_each_run_once_below_the_axes():
    """shared.md: one × per run not usable, below the axes, the count in the strip's label (C12)."""
    _, (ax,) = plotting.new_figure(1)
    kinds = [FailureKind.ERROR, FailureKind.ERROR, FailureKind.UNREAD]
    entries = plotting.strip(ax, np.array([0.1, 0.2, 0.3]), kinds, False)
    assert [e["kind"] for e in entries] == ["error", "error", "unread"] and "run_id" not in entries[0]
    marks = [line for line in ax.lines if line.get_marker() == "x"]
    assert len(marks) == 1 and len(marks[0].get_xdata()) == 3
    assert all(y < 0 for y in marks[0].get_ydata())  # in axes coordinates: below the axes
    assert any("3 not usable" in t.get_text() and "2 error" in t.get_text() for t in ax.texts)
    _, (ax2,) = plotting.new_figure(1)
    assert plotting.strip(ax2, np.array([]), [], True) == [] and not ax2.lines and ax2.get_xscale() == "log"


def test_spectrum_open_markers_on_the_bottom_edge():
    """0048: any value below the panel's lower limit, an exact zero or rounding, an open marker on the bottom edge."""
    _, (ax,) = plotting.new_figure(1)
    k = np.arange(1, 9)
    values = np.array([0.5, 0.0, 1e-3, 1e-20, 1e-5, 0.0, 1e-8, 1e-11])
    plotting.spectrum(ax, k, values, ymin=1e-17, floor=1e-10, fit=(0.0, 1.0, 7), window=6)
    filled = [line for line in ax.lines if line.get_marker() == "o" and line.get_markerfacecolor() != "none"]
    hollow = [line for line in ax.lines if line.get_marker() == "o" and line.get_markerfacecolor() == "none"]
    assert list(hollow[0].get_xdata()) == [2, 4, 6] and set(hollow[0].get_ydata()) == {1e-17}
    assert len(filled[0].get_xdata()) == 5
    assert ax.get_yscale() == "log" and ax.get_ylim()[0] == 1e-17


def test_intervals_and_empty_panel():
    _, (ax, ax2) = plotting.new_figure(2)
    plotting.intervals(
        ax, np.array([1.0, 2.0]), np.array([3.0, 0.0]), np.array([2.0, 0.0]), np.array([4.0, 1e-30]), ymin=1e-17
    )
    assert ax.get_yscale() == "log"
    plotting.empty_panel(ax2, "no spectrum: constant")
    assert [t.get_text() for t in ax2.texts] == ["no spectrum: constant"]


def test_new_figure_layouts():
    _, axes = plotting.new_figure(2, stacked=True)
    assert len(axes) == 2 and axes[0].get_position().y0 > axes[1].get_position().y0
    _, axes = plotting.new_figure(3)
    assert len(axes) == 3 and axes[0].get_position().x0 < axes[1].get_position().x0


def test_the_users_matplotlib_settings_are_left_alone(tmp_path):
    """Record 0073 item 8: EMA's style is applied in its own functions; the user's rcParams and backend stay."""
    before = dict(matplotlib.rcParams)
    backend = matplotlib.get_backend()
    draw(tmp_path)
    assert matplotlib.get_backend() == backend
    assert {k: v for k, v in matplotlib.rcParams.items() if before[k] != v} == {}


def test_png_has_no_text_chunks(tmp_path):
    draw(tmp_path)
    png = (tmp_path / "scatter_a.png").read_bytes()
    chunks, i = [], 8
    while i < len(png):
        n = int.from_bytes(png[i : i + 4], "big")
        chunks.append(png[i + 4 : i + 8])
        i += 12 + n
    assert not {b"tEXt", b"iTXt", b"zTXt", b"tIME"} & set(chunks)
    assert zlib  # the chunks are read by hand: no image library needed
