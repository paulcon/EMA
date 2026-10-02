"""The Markdown report of one diagnostic result (diagnostics/shared.md, The report; S1-S4; 0018, 0042, 0044, 0055).

``render(result, spec)`` is a pure function of the stored result and its model version's spec, so a report rebuilt
from the store is byte-identical (P1, S10). It reads no diagnostic: what a table, a note, or a figure says is in
the result, and the report lays it out (architecture.md §1). The conventions a diagnostic follows so its report
reads as its mock are record 0073's (docs/plans/08-figures-and-reports.md, The API the diagnostics call).

Every text field of the result and the spec is plain text, which the report escapes for Markdown (T10): EMA's own
symbols in a result are Unicode, and the report's own sentences are the only Markdown it writes unescaped.
"""

import re
from collections.abc import Mapping, Sequence
from fractions import Fraction
from typing import Any

from ema.designs import samplers
from ema.designs.lines import lines_through_anchor
from ema.types.design import DesignIdentity
from ema.types.errors import EMAError
from ema.types.identity import canonical_json, model_version_label
from ema.types.model import ModelSpec
from ema.types.results import DiagnosticResult, Estimate, EstimateTable, IntervalInfo, Observation
from ema.types.runs import FailureKind
from ema.types.space import ModelParameterSpace, Scale
from ema.types.text import fmt

#: The one explanation of variability intervals per report: the Estimates section's opening sentence (S4, 0042).
#: It is the only generated text that says "confidence interval" (the glossary's terminology test).
EXPLAIN_INTERVALS = (
    "Each variability interval shows how much its estimate changes when the runs behind it change, by the method "
    "named under its table; it is not a confidence interval, and carries no coverage probability."
)

#: Markdown's (and pandoc's) characters that act on text: each is backslash-escaped in text EMA didn't write (T10).
_SPECIAL = frozenset("\\`*_[]<>$|~^@#&")
#: A block marker at a line's start, after ``_escape`` (which escapes "*", "#", ">", "|", "~", "`"): a list item ("-",
#: "+", "1.", "a)", "(iv)"), a rule or setext underline ("---", "==="), or a definition (":") (record 0073 item 2).
_BLOCK = re.compile(r"^(\s*)(?:([-+:=])|(\(?[0-9A-Za-z]+)([.)])(?=\s|$))")
_ID_DIGITS = 12  # 0055
#: Request parameters that name one of a family, printed "level 2", as the mocks do; others "n = 200" (0073 item 6).
_NAMED = frozenset({"anchor", "basis", "degree", "level"})
#: A figure's file name: letters, digits, "_", "-", "." (not first, no ".."), so the image link can't break (T10).
_FILE = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*")


def _escape(text: str) -> str:
    """Escape text for Markdown, so it renders as written (T10; record 0073 item 2)."""
    return "".join("\\" + c if c in _SPECIAL else c for c in text)


def _one_line(text: str) -> str:
    """Join text's lines, whatever their line endings, with spaces (record 0073 item 2)."""
    return " ".join(text.splitlines())


def _cell(text: str) -> str:
    """Escape text for a table cell or inside a line: one line."""
    return _escape(_one_line(text))


def _line_start(text: str) -> str:
    """Escape text that starts a line, a block marker at its start included, so it is no list or rule (T10)."""
    escaped = _escape(text)
    found = _BLOCK.match(escaped)
    if found is None:
        return escaped
    if found.group(2):
        return f"{found.group(1)}\\{escaped[found.end(1) :]}"
    return f"{escaped[: found.start(4)]}\\{escaped[found.start(4) :]}"


def _paragraph(text: str) -> str:
    """Escape text that starts a paragraph (a table's title, a caption): one line, its start escaped."""
    return _line_start(_one_line(text).strip())


def _file(name: str) -> str:
    """Return a figure's file name, refused unless plain (``ema.plotting.save`` writes only such names)."""
    if not _FILE.fullmatch(name) or ".." in name:
        raise ValueError(f"a figure's file name is letters, digits, _, -, and ., not {name!r}")
    return name


def _number(x: float, units: str = "") -> str:
    """Write a number as S3 does: an integer in full, any other ``fmt``'s four digits; then its units."""
    text = str(x) if isinstance(x, int) and not isinstance(x, bool) else fmt(float(x))
    return f"{text} {_cell(units)}" if units else text


def _plain(x: Any) -> Any:
    """JSON data from a stored, read-only parameter value."""
    if isinstance(x, Mapping):
        return {k: _plain(v) for k, v in x.items()}
    if isinstance(x, (tuple, list)):
        return [_plain(v) for v in x]
    return x


def _value(x: Any) -> str:
    """Write a request's or a design's parameter value: numbers by S3, text escaped, mappings and lists as JSON."""
    if isinstance(x, bool) or x is None:
        return canonical_json(x)
    if isinstance(x, (int, float)):
        return _number(x)
    if isinstance(x, str):
        return _cell(x)
    return _cell(canonical_json(_plain(x)))


def _version(spec: ModelSpec, model_version_id: str) -> str:
    """Write a model version as "name@" and 12 hex digits (0055), the name escaped; "@" inside a word is no citation."""
    name, _, digits = model_version_label(spec.name, model_version_id).rpartition("@")
    return f"{_cell(name)}@{digits}"


def _table(columns: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    head = "| " + " | ".join(_cell(c) for c in columns) + " |"
    rule = "|" + "---|" * len(columns)
    return "\n".join([head, rule, *("| " + " | ".join(row) + " |" for row in rows)])


def _label_cells(label: str) -> list[str]:
    """Return a row's leading cells: its label, split on tabs (record 0073 item 3)."""
    return [_cell(part) for part in label.split("\t")]


def _fit(columns: Sequence[str], rows: list[list[str]], what: str) -> None:
    for row in rows:
        if len(row) != len(columns):
            raise ValueError(f"{what}: a row of {len(row)} cells for {len(columns)} columns")


# The header (S2)


def _space_row(space: ModelParameterSpace, spec: ModelSpec) -> str:
    parts = []
    for p in spec.parameters:
        r = space.ranges.get(p.name)
        if r is not None:
            units = f" {_cell(p.units)}" if p.units else ""
            log = ", log" if r.scale is Scale.LOG else ""
            parts.append(f"{_cell(p.name)} [{fmt(r.lo)}, {fmt(r.hi)}]{units}{log}")
    return "; ".join(parts) or "none"


def _held_row(space: ModelParameterSpace, spec: ModelSpec) -> str:
    parts = []
    for p in spec.parameters:
        if p.name in space.ranges:
            continue
        given = p.name in space.held
        value = space.held[p.name] if given else p.nominal
        parts.append(f"{_cell(p.name)} = {_number(value, p.units)} ({'held value' if given else 'nominal'})")
    return "; ".join(parts) or "none"


def _point(values: Sequence[tuple[str, float, str]], given: Sequence[str]) -> str:
    """Write a point, 'a = 1, b = 0 (all nominal)': the values, and which were given (the point run's x, an anchor)."""
    text = ", ".join(f"{_cell(n)} = {_number(v, u)}" for n, v, u in values)
    names = [n for n, _, _ in values if n in given]
    if not names:
        return f"{text} (all nominal)"
    if len(names) == len(values):
        return f"{text} (all given)"
    return f"{text} ({', '.join(_cell(n) for n in names)} given; the others nominal)"


def _rate(rate: Fraction) -> str:
    return "½" if rate == Fraction(1, 2) else str(rate)


def _sampler(design: DesignIdentity, *, rate: bool) -> str:
    """'sampler random 1 (rate ½)': its name and version, and its rate when that version is still registered.

    The rate is the registered sampler's, so it is printed only when the registered version is the stored one (S10,
    P1): a later version's rate is not this design's.
    """
    text = f"sampler {_cell(str(design.sampler))} {_cell(str(design.sampler_version))}"
    if rate:
        try:
            sampler = samplers.get(str(design.sampler))
        except EMAError:
            return text
        if str(sampler.version) == str(design.sampler_version):
            text += f" (rate {_rate(sampler.rate)})"
    return text


def _coordinate_lines(design: DesignIdentity, spec: ModelSpec, space: ModelParameterSpace) -> str:
    """Write the anchor's values and the lines it is on (coordinate_lines.md, Parameters; G12)."""
    params = design.params
    n = int(params["n"])
    anchor = dict(params.get("anchor", {}))
    base = {p.name: float(anchor.get(p.name, space.held.get(p.name, p.nominal))) for p in spec.parameters}
    varied = space.varied(spec)
    values = [(p.name, base[p.name], p.units) for p in spec.parameters if p.name in varied]
    through = lines_through_anchor(design, spec)  # the generator's own rule (G12)
    if n % 2 == 0:
        on = "lines through the anchor: none (n is even)"
    elif len(through) == len(varied) > 1:
        on = f"all {len(varied)} lines share the anchor's run"
    else:
        on = f"lines through the anchor: {', '.join(_cell(v) for v in through) or 'none'}"
    return f"coordinate lines, n = {n}, anchor {_point(values, list(anchor))}; {on}"


def _replicates(design: DesignIdentity) -> str:
    """Write the point design's replicates: "replicates 0–4", or "replicate 0"."""
    repeats = int(design.params.get("repeats", 0))
    return f"replicates 0–{repeats}" if repeats else "replicate 0"


def _design_row(result: DiagnosticResult, spec: ModelSpec, space: ModelParameterSpace) -> str:
    design = result.provenance.design
    p = design.params
    kind = design.kind
    if kind == "uniform":
        return f"uniform, n = {_value(p['n'])}, {_sampler(design, rate=True)}, seed {design.seed}"
    if kind == "convergent":
        levels = result.provenance.design_structure.levels or ()
        sizes = ", ".join(str(n) for n in levels)
        return (
            f"convergent, n_min = {_value(p['n_min'])}, alpha = {_value(p['alpha'])}, level {_value(p['level'])}: "
            f"{sizes} points; {_sampler(design, rate=True)}, seed {design.seed}"
        )
    if kind == "point":
        repeats = int(p.get("repeats", 0))
        return f"point, repeats = {repeats} ({_replicates(design)})"
    if kind == "coordinate_lines":
        return _coordinate_lines(design, spec, space)
    if kind == "random_lines":
        return f"random lines, m = {_value(p['m'])}, n = {_value(p['n'])}, seed {design.seed}"
    if kind == "lines":
        return f"given lines, {len(p['lines'])} lines, n = {_value(p['n'])}"
    rest = ", ".join(f"{_cell(k)} = {_value(v)}" for k, v in sorted(p.items()))
    return f"{_cell(kind)}, {rest}, seed {design.seed}"


def _runs_row(result: DiagnosticResult) -> str:
    c = result.counts
    failed = sum(c.failed.values())
    kinds = ", ".join(f"{c.failed[k]} {k.value}" for k in FailureKind if c.failed[k])
    failed_text = f"{failed} failed ({kinds})" if failed else "0 failed"
    return (
        f"{c.runs}: {c.new} new, {c.reused} reused; {failed_text}; {c.missing} missing {_cell(result.prediction)}; "
        f"{c.usable} usable"
    )


def _header(result: DiagnosticResult, spec: ModelSpec) -> str:
    prediction = next(p for p in spec.predictions if p.name == result.prediction)
    shown = _cell(prediction.name)
    if prediction.description:
        shown += f": {_cell(prediction.description)}"
    if prediction.units:
        shown += f", {_cell(prediction.units)}"
    design = result.provenance.design
    space = ModelParameterSpace.parse(design.space)
    rows = [("Model version", _version(spec, result.model_version_id)), ("Model prediction", shown)]
    if result.provenance.request.space is None:  # the point run (0049): every model parameter held, no Held row
        x = result.provenance.request.params.get("x", {})
        values = [(p.name, space.held.get(p.name, p.nominal), p.units) for p in spec.parameters]
        rows.append(("Space", f"the point {_point(values, list(x))}; every model parameter held"))
    else:
        rows += [("Space", _space_row(space, spec)), ("Held", _held_row(space, spec))]
    rows.append(("Design", _design_row(result, spec, space)))
    rows += [(_cell(label), _cell(text)) for label, text in result.header_rows]
    rows.append(("Runs", _runs_row(result)))
    return "\n".join(["| | |", "|---|---|", *(f"| {label} | {text} |" for label, text in rows)])


# Estimates (S4; uncertainty.md, The bootstrap, step 6, and Rules)


def _interval_cell(e: Estimate, units: str) -> str:
    if e.interval is None:
        return "none"
    text = f"[{fmt(e.interval[0])}, {fmt(e.interval[1])}]"
    return f"{text} {_cell(units)}" if units else text


def _estimate_rows(table: EstimateTable) -> tuple[list[list[str]], list[str]]:
    """Return the table's rows, estimates with one label in one row, and the "none" reasons for the line under it."""
    groups: dict[str, list[Estimate]] = {}
    for e in table.estimates:
        groups.setdefault(e.label, []).append(e)
    rows, reasons = [], []
    for label, estimates in groups.items():
        cells = _label_cells(label)
        lead = len(cells)
        for j, e in enumerate(estimates):
            cells += [_number(e.value, table.units), _interval_cell(e, table.units)]
            if e.interval is None:
                heading = (
                    table.columns[lead + 2 * j] if len(estimates) > 1 and lead + 2 * j < len(table.columns) else ""
                )
                name = " ".join(label.split("\t")) + (f", {heading}" if heading else "")
                reasons.append(f"{_cell(name)}: none: {_cell(str(e.reason))}.")
        rows.append(cells)
    return rows, reasons


def _setting(key: str, value: Any) -> str:
    return f"{_cell(key)} = {_value(value)}"


def _method_line(info: IntervalInfo) -> str:
    """Write the line under a table: "Variability intervals: bootstrap over the 200 usable runs, ..., seed 1."."""
    s = dict(info.settings)
    parts = [f"Variability intervals: {_cell(info.method)} over the {info.n_usable} usable runs"]
    if "resamples" in s:
        parts.append(f"{_value(s.pop('resamples'))} resamples")
    if "distinct" in s:
        parts.append(f"{_cell(str(s.pop('distinct')))} recomputed on the distinct runs of each resample")
    if "percentiles" in s:
        lo, hi = s.pop("percentiles")
        parts.append(f"{fmt(float(lo))}th to {fmt(float(hi))}th percentiles")
    seed = s.pop("seed", None)
    s.pop("min_defined", None)
    parts += [_setting(k, v) for k, v in sorted(s.items())]
    if seed is not None:
        parts.append(f"seed {_value(seed)}")
    return ", ".join(parts) + "."


def _estimates_section(result: DiagnosticResult) -> list[str]:
    blocks = ["## Estimates", EXPLAIN_INTERVALS]
    for table in result.estimates:
        rows, reasons = _estimate_rows(table)
        _fit(table.columns, rows, f"estimates table {table.key}'s columns")
        blocks.append(_table(table.columns, rows))
        line = [_method_line(table.interval), *reasons]
        if table.interval.undefined:
            counts = ", ".join(f"{_cell(k)} {n}" for k, n in sorted(table.interval.undefined.items()))
            line.append(f"Undefined resamples, dropped: {counts}.")
        if table.title and table.title != table.columns[0]:
            line.insert(0, _paragraph(table.title))
        blocks.append(" ".join(line))
    return blocks


# Observations (0034)


def _observation_cell(o: Observation, title: str = "") -> str:
    """Write an observation: its value, then its units, but where its table's title names them.

    A title that says "in <units>." ("Coefficients in m³/yr.") gives the units once for the table, so each cell
    leaves them out (record 0078 item 2, Review round 1).
    """
    units = "" if o.units and f" in {o.units}." in f" {title}" else o.units
    if isinstance(o.value, str):
        return _cell(o.value) + (f" {_cell(units)}" if units else "")
    return _number(o.value, units)


def _observations_section(result: DiagnosticResult, spec: ModelSpec) -> list[str]:
    blocks = ["## Observations"]
    for table in result.observations:
        rows = [
            _label_cells(row[0].label) + [_observation_cell(o, table.title) for o in row] for row in table.rows if row
        ]
        _fit(table.columns, rows, f"observations table {table.key}'s columns")
        blocks.append(_table(table.columns, rows))
        if table.title and table.title != table.columns[0]:
            blocks.append(_paragraph(table.title))
    if result.measured_noisy is not None:
        label = _version(spec, result.model_version_id)
        blocks.append(
            f"The model prediction varies at this point, so {label} is recorded as measured noisy in "
            f"{_cell(result.prediction)}."
        )
    return blocks


# Figures and provenance


def _code(name: str) -> str:
    return f"`{name}`"


def _figures_section(result: DiagnosticResult) -> list[str]:
    blocks = ["## Figures"]
    groups: list[list[Any]] = []
    for f in result.figures:
        if groups and groups[-1][0].caption == f.caption:
            groups[-1].append(f)
        else:
            groups.append([f])
    for group in groups:
        blocks.append(" ".join(f"![{_cell(f.name)}]({_file(f.png)})" for f in group))
        cards = ", ".join(_code(_file(f.card)) for f in group)
        caption = f"{_paragraph(group[0].caption)} " if group[0].caption.strip() else ""
        blocks.append(f"{caption}Data card{'s' if len(group) > 1 else ''}: {cards}.")
    return blocks


def _provenance_section(result: DiagnosticResult, spec: ModelSpec) -> list[str]:
    p = result.provenance
    request = p.request
    params: Mapping[str, Any] = request.params
    parts = [_cell(request.diagnostic.replace("_", " "))]
    if request.space is not None:
        parts.append("space as above")
    for key in sorted(k for k in params if k != "seed" and params[k] is not None):  # None: not given (lines' m)
        if key == "sampler" and p.design.sampler is not None:
            parts.append(_sampler(p.design, rate=False))
        elif key in _NAMED:
            parts.append(f"{_cell(key)} {_value(params[key])}")
        else:
            parts.append(_setting(key, params[key]))
    if "seed" in params:
        parts.append(f"seed {_value(params['seed'])}")
    parts.append(f"prediction {_cell(request.prediction)}")
    new = result.counts.new
    approval = (
        f"{p.approval_id[:_ID_DIGITS]} ({new} new run{'' if new == 1 else 's'})"
        if p.approval_id is not None
        else "none (no new runs)"
    )
    label = _version(spec, result.model_version_id)
    runs = f"{result.counts.runs} ({_replicates(p.design)})" if p.design.kind == "point" else str(result.counts.runs)
    line = (
        f"EMA {_cell(p.ema)}; numpy {_cell(p.numpy)}, scipy {_cell(p.scipy)}, matplotlib {_cell(p.matplotlib)}; "
        f"model version {label}; request: {', '.join(parts)}; runs: {runs}; approvals: {approval}."
    )
    return ["## Provenance", line]


def _note(text: str) -> str:
    """Write a note as a list item, its later lines indented under it; blank lines dropped, so none is code (T10)."""
    lines = [line.rstrip() for line in text.splitlines() if line.strip()] or [""]
    return "- " + "\n  ".join(_line_start(line) for line in [lines[0].lstrip(), *lines[1:]])


def render(result: DiagnosticResult, spec: ModelSpec) -> str:
    """Render a diagnostic result's report, in Markdown (S1-S4; 0018, 0042, 0044, 0055; T10).

    The sections in order: the title, the header, Notes, Estimates (opening with ``EXPLAIN_INTERVALS``, a line
    under each table), Observations, Figures, and Provenance; an empty section is left out (0051). Every computed
    number is ``fmt`` of its stored double, integers in full; ids as 12 hex digits. ``result.extra`` is not printed
    (0041). A pure function of its inputs: a report rebuilt from the store is byte-identical (P1, S10).

    Parameters
    ----------
    result
        The stored diagnostic result.
    spec
        Its model version's spec (Q14): the names, descriptions, units, and nominal values.

    Returns
    -------
    str
        The report, ending in one newline.

    Raises
    ------
    ValueError
        For a spec without the result's model prediction, or a table whose rows don't fit its columns.
    """
    if result.prediction not in {p.name for p in spec.predictions}:
        raise ValueError(f"the spec {spec.name} has no model prediction {result.prediction}")
    title = f"# {_cell(result.title)}: {_cell(spec.name)}, {_cell(result.prediction)}"
    blocks = [title, _header(result, spec)]
    if result.notes:
        notes = [_note(n.text) for n in result.notes]
        blocks += ["## Notes", "\n".join(notes)]
    if result.estimates:
        blocks += _estimates_section(result)
    if result.observations or result.measured_noisy is not None:
        blocks += _observations_section(result, spec)
    if result.figures:
        blocks += _figures_section(result)
    blocks += _provenance_section(result, spec)
    return "\n\n".join(blocks) + "\n"
