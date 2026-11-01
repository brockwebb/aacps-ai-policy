"""docs/findings/anchor_queries.py: the derived `where`, the quote-length limit, and the dual-layer absence rule."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("anchor_queries", REPO / "docs/findings/anchor_queries.py")
aq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aq)

TEXT = ("Related Entries: AC, DL\n\nA. PURPOSE\n\nTo set rules.\n\nB. ISSUE\n\nAI is embedded in tools.\n\n"
        "C. POSITION\n\n1. AI shall support staff.\n\n2. AI may only be used for approved purposes.\n")
RULES = {"doc": {"section": r"(?m)^([A-F])\.\s+[A-Z][A-Z ]{3,}\s*$", "clause": r"(?m)^(\d+)\.\s"}}


class G:
    def __init__(self, stmts):
        self.stmts = stmts

    def statements(self, label, doc=None):
        return [s for s in self.stmts if s["label"] == label and doc in (None, s["doc"])]


@pytest.fixture(autouse=True)
def held(monkeypatch):
    monkeypatch.setattr(aq, "held_text", lambda doc: TEXT)


def test_derived_where_names_section_and_clause():
    at = lambda q: aq.derived_where("doc", aq.raw_offset("doc", q), RULES)
    assert at("Related Entries: AC") == "header"
    assert at("AI is embedded in tools.") == "B"
    assert at("AI shall support staff.") == "C.1"
    assert at("approved purposes.") == "C.2"
    assert aq.derived_where("other", 0, RULES) is None


def test_quote_over_the_limit_is_refused():
    with pytest.raises(aq.Fail):
        aq.resolve({"kind": "text", "doc": "doc", "quote": "AI may only be used for approved purposes."}, G([]), 5)


def test_absence_needs_both_layers_unless_text_layer_is_waived():
    g = G([{"label": "Obligation", "doc": "doc", "key": "k", "text": "AI shall support staff."}])
    with pytest.raises(aq.Fail):                      # the text layer has the word though the graph does not
        aq.resolve({"kind": "absent", "label": "Obligation", "doc": "doc", "pattern": "embedded"}, g, 14)
    r = aq.resolve({"kind": "absent", "label": "Obligation", "doc": "doc", "pattern": "embedded",
                    "text_layer": False}, g, 14)
    assert r["layer"] == "graph"
    with pytest.raises(aq.Fail):                      # and the graph layer alone still binds
        aq.resolve({"kind": "absent", "label": "Obligation", "doc": "doc", "pattern": "support",
                    "text_layer": False}, g, 14)
