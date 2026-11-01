"""Read the Policy DM graph's served export (the kit's NetworkX node-link JSON) for the conflict pass and the anchor
queries. One loader, so both read the release and nothing else: a number in the anchor table regenerates from the
graph, never from an intermediate file.

The export is `graphs/aacps-policy-dm/exports/<artifact_stem>.json` (config `engine.export.artifact_stem`): nodes carry
`label`, `key` and their properties; links carry `type`, `source` and `target` as `<Label>::<key>`.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
GRAPH = REPO / "graphs/aacps-policy-dm"


def export_path(graph_root: Path = GRAPH) -> Path:
    cfg = yaml.safe_load((graph_root / "config.yaml").read_text())
    stem = cfg["engine"]["export"]["artifact_stem"]
    path = graph_root / cfg["engine"]["paths"]["exports_dir"] / f"{stem}.json"
    if not path.is_file():
        raise SystemExit(f"FATAL: no served export at {path}; cut a release first (squiddy extract / build)")
    return path


@dataclass
class PolicyGraph:
    nodes: dict[str, dict]                                     # node id (Label::key) -> node
    by_label: dict[str, list[dict]] = field(default_factory=lambda: defaultdict(list))
    out_edges: dict[str, list[dict]] = field(default_factory=lambda: defaultdict(list))
    in_edges: dict[str, list[dict]] = field(default_factory=lambda: defaultdict(list))
    meta: dict = field(default_factory=dict)

    def doc_of(self, statement_key: str, label: str) -> str | None:
        """The Work a statement is STATED_IN."""
        for e in self.out_edges.get(f"{label}::{statement_key}", []):
            if e["type"] == "StatedIn":
                return e["target"].split("::", 1)[1]
        return None

    def statements(self, label: str, doc: str | None = None) -> list[dict]:
        out = []
        for n in self.by_label.get(label, []):
            d = self.doc_of(n["key"], label)
            if doc is None or d == doc:
                out.append({**n, "doc": d})
        return out

    def work(self, key: str) -> dict | None:
        return self.nodes.get(f"Work::{key}")


def load(path: Path | None = None) -> PolicyGraph:
    path = path or export_path()
    raw = json.loads(path.read_text())
    g = PolicyGraph(nodes={n["id"]: n for n in raw["nodes"]}, meta={"path": str(path), **(raw.get("graph") or {})})
    for n in raw["nodes"]:
        g.by_label[n["label"]].append(n)
    for e in raw["links"]:
        g.out_edges[e["source"]].append(e)
        g.in_edges[e["target"]].append(e)
    return g
