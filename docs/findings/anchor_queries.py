"""Regenerate docs/findings/2026-11-01_anchor_evidence.md from the graph (AP-02 Part D).

The verdicts and the evidence each one rests on are written in docs/findings/anchors.yaml. This script is what makes
them checkable: every piece of evidence is a query against the served export (scripts/policy_graph.py), and a query
that does not return what the YAML says is FATAL, so the table cannot drift from the graph.

Evidence kinds (anchors.yaml `evidence:` items):
- `statement`: an Obligation or Definition in `doc` whose text contains `quote` (at most `max_quote_words` words,
  verbatim). Resolves to the node: its key, section path and page.
- `absent`: no `label` statement in `doc` whose text (or, for a Definition, term) matches `pattern`, AND no match in
  the document's held text. fss-policy-kg's dual-layer rule: an absence claim needs negative evidence at both layers,
  the statement layer (the graph) and the text layer (the parsed text the graph was extracted from).
- `text`: a passage of the held text of `doc` containing `quote` (for a fact the extractor rightly did not make a
  statement of, such as a list of Legal References). Resolved against the parsed text, and named as text-layer.
- `cites` / `not_cites`: a Cites edge from `doc` to `target` exists / does not.

The `where` column: for a document under `derive_where` it is computed from the held text (`derived_where`), since
the kit's parsed section path for the draft is its running header (squiddy SQ-AP02g); otherwise the node's section
path, or a `text` item's own `where` label.

Plus one computed table: the draft's Obligations aligned clause by clause to the MSDE model policy's statements by
shared content words, and the model's Obligations with no counterpart in the draft.

    /Users/brock/GitHub/squiddy/.venv/bin/python docs/findings/anchor_queries.py [--check]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
import policy_graph as pg  # noqa: E402
from conflict_pass import terms  # noqa: E402  (one tokenizer for pairing and alignment)

SPEC = REPO / "docs/findings/anchors.yaml"
OUT = REPO / "docs/findings/2026-11-01_anchor_evidence.md"
PARSED = REPO / "graphs/aacps-policy-dm/corpus/parsed"


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("’", "'").replace("‘", "'").replace("“", '"')
                  .replace("”", '"').replace("–", "-").replace("—", "-")).strip()


def held_text(doc: str) -> str:
    p = PARSED / f"{doc}.json"
    if not p.is_file():
        raise SystemExit(f"FATAL: no parsed text for {doc} at {p}")
    return json.loads(p.read_text())["plain_text"]


def short(s: str, n: int) -> str:
    w = norm(s).split()
    return " ".join(w[:n]) + (" ..." if len(w) > n else "")


class Fail(Exception):
    pass


def raw_offset(doc: str, quote: str) -> int:
    """Where `quote` (matched as `norm` matches it) starts in the held text, un-normalized."""
    parts = []
    for w in norm(quote).split():
        parts.append("".join({"'": "['‘’]", '"': '["“”]', "-": "[-–—]"}.get(c, re.escape(c)) for c in w))
    m = re.search(r"\s+".join(parts), held_text(doc))
    if not m:
        raise Fail(f"cannot place {quote!r} in the held text of {doc}")
    return m.start()


def derived_where(doc: str, start: int, rules: dict) -> str | None:
    """The section a passage sits in, computed from the held text, for a document whose parsed section paths are
    unusable (the draft's are its running header, squiddy SQ-AP02g): the last `section` heading before `start` and the
    last `clause` number between that heading and `start`, e.g. `C.1`; `header` before the first heading."""
    r = rules.get(doc)
    if not r:
        return None
    text = held_text(doc)[:start]
    heads = list(re.finditer(r["section"], text))
    if not heads:
        return "header"
    h = heads[-1]
    clauses = list(re.finditer(r["clause"], text[h.end():]))
    return f"{h.group(1)}.{clauses[-1].group(1)}" if clauses else h.group(1)


def resolve(ev: dict, g: pg.PolicyGraph, maxw: int, rules: dict | None = None) -> dict:
    rules = rules or {}
    kind = ev["kind"]
    if kind in ("statement", "text"):
        q = norm(ev["quote"])
        if len(q.split()) > maxw:
            raise Fail(f"quote has {len(q.split())} words (> {maxw}): {q!r}")
    if kind == "statement":
        hits = [n for n in g.statements(ev["label"], ev["doc"]) if q in norm(n["text"])]
        if not hits:
            raise Fail(f"no {ev['label']} in {ev['doc']} contains {q!r}")
        n = hits[0]
        span = n.get("grounding_span") or {}
        sec = derived_where(ev["doc"], int(span["start"]), rules) \
            if ev["doc"] in rules else n.get("section_path")
        return {"layer": "graph", "doc": ev["doc"], "where": f"{sec or ''} p.{n.get('page')}".strip(),
                "quote": q, "node": f"{ev['label']}::{n['key']}",
                "detail": ", ".join(f"{k}={n.get(k)}" for k in ("force", "binds", "responsible_party_stated",
                                                                "mechanism_stated", "term") if k in n)}
    if kind == "text":
        if q not in norm(held_text(ev["doc"])):
            raise Fail(f"the held text of {ev['doc']} does not contain {q!r}")
        where = derived_where(ev["doc"], raw_offset(ev["doc"], q), rules) if ev["doc"] in rules else ev.get("where", "")
        return {"layer": "text", "doc": ev["doc"], "where": where, "quote": q, "node": "(text layer)",
                "detail": ev.get("note", "")}
    if kind == "absent":
        rx = re.compile(ev["pattern"], re.I)
        field = "term" if ev["label"] == "Definition" else "text"
        graph_hits = [n["key"] for n in g.statements(ev["label"], ev["doc"]) if rx.search(n.get(field) or "")]
        text_hits = rx.findall(held_text(ev["doc"])) if ev.get("text_layer", True) else []
        if graph_hits or text_hits:
            raise Fail(f"absence of /{ev['pattern']}/ in {ev['doc']} is contradicted: graph {graph_hits[:3]}, "
                       f"text {text_hits[:3]}")
        return {"layer": "graph+text" if ev.get("text_layer", True) else "graph", "doc": ev["doc"], "where": "",
                "quote": f"no match for /{ev['pattern']}/", "node": f"0 {ev['label']} nodes",
                "detail": ev.get("note", "")}
    if kind in ("cites", "not_cites"):
        edges = [e for e in g.out_edges.get(f"Work::{ev['doc']}", []) if e["type"] == "Cites"]
        found = any(e["target"].split("::", 1)[1] == ev["target"] for e in edges)
        if found != (kind == "cites"):
            raise Fail(f"{kind} {ev['doc']} -> {ev['target']} is not what the graph holds "
                       f"(its Cites: {sorted(e['target'] for e in edges)})")
        return {"layer": "graph", "doc": ev["doc"], "where": "", "quote": f"{'cites' if found else 'no Cites edge to'} "
                f"{ev['target']}", "node": "Cites", "detail": ev.get("note", "")}
    raise Fail(f"unknown evidence kind {kind!r}")


def alignment(g: pg.PolicyGraph, cfg: dict) -> tuple[list[dict], list[dict]]:
    draft, model = cfg["draft"], cfg["model"]
    d_obl = g.statements("Obligation", draft)
    m_obl = g.statements("Obligation", model)
    rows = []
    used = set()
    for d in sorted(d_obl, key=lambda n: (n.get("page") or 0, n["grounding_span"]["start"]
                                          if isinstance(n.get("grounding_span"), dict) else 0)):
        td = terms(d["text"])
        best, score = None, 0.0
        for m in m_obl:
            tm = terms(m["text"])
            j = len(td & tm) / len(td | tm) if td | tm else 0.0
            if j > score:
                best, score = m, j
        if best is not None and score >= cfg["min_jaccard"]:
            used.add(best["key"])
        rows.append({"draft": d, "model": best if score >= cfg["min_jaccard"] else None, "jaccard": round(score, 2)})
    dropped = [m for m in m_obl if m["key"] not in used]
    return rows, dropped


def render(spec: dict, g: pg.PolicyGraph) -> str:
    maxw = int(spec["max_quote_words"])
    L = ["# Anchor evidence: draft Policy DM against its corpus", "",
         f"**Generated by** `docs/findings/anchor_queries.py` from `docs/findings/anchors.yaml` over the served export "
         f"`{Path(g.meta['path']).relative_to(REPO)}` (ledger events {g.meta.get('ledger_events')}, last event "
         f"`{str(g.meta.get('ledger_last_event_id'))[:12]}`). Do not edit; edit the YAML and re-run. **Task:** AP-02 "
         f"Part D. Every quote is at most {maxw} words and is checked verbatim against a graph node (layer `graph`) or "
         f"the held text it was extracted from (layer `text`). An absence is checked at both layers.", "",
         "Verdicts are this session's reading of the evidence, not a legal opinion. The comment that uses them is "
         "written in Desktop under the operator's name.", "", "## Summary", "",
         "| id | anchor | verdict |", "|---|---|---|"]
    for a in spec["anchors"]:
        L.append(f"| {a['id']}{' (new)' if a.get('new') else ''} | {a['title']} | **{a['verdict']}** |")
    L.append("")
    for a in spec["anchors"]:
        L += [f"## {a['id']}{' (new)' if a.get('new') else ''}: {a['title']}", "",
              f"**Verdict: {a['verdict']}.** {norm(a['reading'])}", ""]
        if a.get("changes"):
            L += [f"**What the corpus changes:** {norm(a['changes'])}", ""]
        L += ["| # | layer | document | where | quote | node | detail |", "|---|---|---|---|---|---|---|"]
        for i, ev in enumerate(a["evidence"], 1):
            try:
                r = resolve(ev, g, maxw, spec.get("derive_where"))
            except Fail as exc:
                raise SystemExit(f"FATAL: anchor {a['id']} evidence {i}: {exc}")
            L.append(f"| {i} | {r['layer']} | `{r['doc']}` | {r['where']} | \"{r['quote']}\" | `{r['node']}` | "
                     f"{r['detail']} |")
        L.append("")
    al = spec["alignment"]
    rows, dropped = alignment(g, al)
    L += ["## The draft against the MSDE model policy, clause by clause", "",
          f"Each Obligation of `{al['draft']}` against the `{al['model']}` Obligation sharing the most content words "
          f"(Jaccard over the conflict pass's tokenizer; a match needs at least {al['min_jaccard']}, NO MEASURED "
          f"BASIS: chosen so a reworded clause still pairs and an unrelated one does not; read the quotes, not the "
          f"number). Quotes are the first {maxw} words.", "",
          "| draft (page) | draft force | model | model force | Jaccard |", "|---|---|---|---|---|"]
    for r in rows:
        d, m = r["draft"], r["model"]
        L.append(f"| \"{short(d['text'], maxw)}\" (p.{d.get('page')}) | {d.get('force')} | "
                 + (f"\"{short(m['text'], maxw)}\" | {m.get('force')} | {r['jaccard']} |" if m else
                    f"(no model clause at or above {al['min_jaccard']}) | | {r['jaccard']} |"))
    L += ["", f"**Model Obligations no draft Obligation was paired with** ({len(dropped)} of "
          f"{len(g.statements('Obligation', al['model']))}; each draft clause pairs with its single best match, so a "
          f"model clause the draft covers twice over, or folds into a broader sentence, can appear here; read them):", ""]
    for m in sorted(dropped, key=lambda n: (n.get("page") or 0, n["key"])):
        L.append(f"- p.{m.get('page')} ({m.get('force')}): \"{short(m['text'], maxw)}\" `Obligation::{m['key']}`")
    L += ["", "## Counts the table rests on", "",
          "| document | Obligations | Definitions | Cites (out) |", "|---|---|---|---|"]
    for doc in spec["count_docs"]:
        cites = sum(1 for e in g.out_edges.get(f"Work::{doc}", []) if e["type"] == "Cites")
        L.append(f"| `{doc}` | {len(g.statements('Obligation', doc))} | {len(g.statements('Definition', doc))} | {cites} |")
    conf = g.by_label.get("Conflict", [])
    L += ["", f"Conflict nodes in the graph: {len(conf)} (DN-003 section 4; `no_conflict` verdicts are rows in "
          f"`graphs/aacps-policy-dm/evidence/conflicts/verdicts.jsonl`, not nodes).", ""]
    for c in conf:
        sides = [e["target"] for e in g.out_edges.get(c["id"], []) if e["type"] == "ConflictsWith"]
        L.append(f"- `{c['key']}` {c.get('verdict')} ({c.get('resolution_basis')}, confidence {c.get('confidence')}): "
                 f"{norm(c.get('text'))} Sides: {', '.join(f'`{s}`' for s in sides)}")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="exit 1 if the committed table differs from a regeneration")
    args = ap.parse_args(argv)
    spec = yaml.safe_load(SPEC.read_text())
    text = render(spec, pg.load())
    if args.check:
        if not OUT.is_file() or OUT.read_text() != text:
            print(f"{OUT.relative_to(REPO)} is stale; re-run without --check", file=sys.stderr)
            return 1
        print("up to date")
        return 0
    OUT.write_text(text)
    print(f"wrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
