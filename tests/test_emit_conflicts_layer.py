"""graphs/aacps-policy-dm/emit.py `conflicts` layer: a verdict other than no_conflict becomes a Conflict node and two
ConflictsWith edges, valid under the graph's generated schema; no_conflict and failed rows are not nodes; a side that is
not in the graph is FATAL. AP-02's real pass settled 48 of 48 pairs no_conflict, so this is the path's only exercise."""

from __future__ import annotations

import importlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parent.parent
GRAPH = REPO / "graphs/aacps-policy-dm"
spec = importlib.util.spec_from_file_location("aacps_emit", GRAPH / "emit.py")
emit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(emit)
sys.path.insert(0, str(GRAPH / "schema/generated"))
schema = importlib.import_module("aacps_policy_dm_pydantic")
CLASSES = {"Conflict": schema.Conflict, "ConflictsWith": schema.ConflictsWith}


def _row(pk, verdict, status="ok", a="obl:draft:1", b="obl:reg:2", basis=None):
    return {"pair_key": pk, "status": status, "a": {"id": a}, "b": {"id": b}, "role": "adjudicator",
            "criteria_version": "v", "prompt_sha256": "p", "resolved_model": "m", "run_id": "conflict_pass:v",
            "verdict": None if status != "ok" else {"verdict": verdict, "resolution_basis": basis,
                                                    "confidence": 0.8, "rationale": "why"}}


def _graph(tmp_path, rows):
    (tmp_path / "v.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return SimpleNamespace(root=tmp_path, domain={"conflicts": {"anchor_doc": "draft", "verdicts": "v.jsonl"}})


def test_only_a_conflict_verdict_becomes_nodes(tmp_path):
    g = _graph(tmp_path, [_row("k1", "genuine_conflict"), _row("k2", "no_conflict"), _row("k3", None, "failed"),
                          _row("k4", "apparent_resolved", basis="hierarchy")])
    ctx = {"in_graph": {"obl:draft:1", "obl:reg:2"}}
    out = emit.emit_layer({"id": "draft"}, None, g, CLASSES, "conflicts", ctx)
    nodes = [o for o in out if isinstance(o, schema.Conflict)]
    edges = [o for o in out if isinstance(o, schema.ConflictsWith)]
    assert sorted(n.id for n in nodes) == ["conflict:k1", "conflict:k4"]
    assert len(edges) == 4 and {e.object for e in edges} == {"obl:draft:1", "obl:reg:2"}
    assert {n.resolution_basis for n in nodes} == {None, "hierarchy"}
    assert emit.emit_layer({"id": "other"}, None, g, CLASSES, "conflicts", ctx) == []


def test_a_side_not_in_the_graph_is_fatal(tmp_path):
    g = _graph(tmp_path, [_row("k1", "genuine_conflict", b="obl:gone:9")])
    with pytest.raises(SystemExit):
        emit.emit_layer({"id": "draft"}, None, g, CLASSES, "conflicts", {"in_graph": {"obl:draft:1"}})
