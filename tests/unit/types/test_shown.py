"""Every type with a ``text`` field prints as that text (architecture.md §3; AR3, P1; record 0070)."""

import dataclasses
import inspect

import ema.types


def test_every_type_with_text_prints_as_it():
    with_text = [
        obj
        for _, obj in inspect.getmembers(ema.types, inspect.isclass)
        if dataclasses.is_dataclass(obj) and "text" in {f.name for f in dataclasses.fields(obj)}
    ]
    names = {cls.__name__ for cls in with_text}
    assert {"Price", "Progress", "ApprovalRequest", "RunInfo", "Reproduction", "ResultSummary"} <= names
    plain = [cls.__name__ for cls in with_text if cls.__str__ is object.__str__]
    assert not plain, f"types with a text field that don't print as it: {plain}"


def test_report_and_result_print_as_their_text():
    assert ema.types.Report.__str__ is not object.__str__
    assert ema.types.DiagnosticResult.__str__ is not object.__str__
