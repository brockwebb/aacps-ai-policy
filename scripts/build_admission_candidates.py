"""Build the squiddy catalog input for the Policy DM graph from this repository's candidate records (AP-02 Part C).

The hand-written candidate files (corpus/candidates/*.yaml) are the record of what was considered and how it was
acquired; they are written for people and disagree with each other and with the kit on shape (two are bare lists, field
names differ, sha256 sits inside prose, two dispositions are outside the kit's list). This script is the one place that
maps them onto the kit's catalog contract (`candidates:` with `id`, `kind`, `title`, plus `local_path`, `sha256`,
`cited_in`, `disposition`; squiddy cli.py cmd_catalog, intake.py, assess.py), and the place every candidate gets its
disposition. Inputs, never edited by it:

- corpus/candidates/aacps-policy-dm.yaml, aacps-policy-dm_related_entries.yaml, md-law-and-msde-guidance.yaml
- corpus/legal_refs.yaml and corpus/legal_refs_receipts.jsonl (AP-02 Part B)
- corpus/substrate.yaml and corpus/substrate/*.md (the converted texts)
- corpus/snapshots/aacps-policy-committee-page_2026-10-31.md
- corpus/admission/dispositions.yaml (the decisions this script applies: merges, supersessions, cited_in, and the
  disposition of every candidate that is not held)

Output: corpus/admission/candidates.yaml (generated; graph.yaml `intake:` reads it). Deterministic and offline.

    /Users/brock/GitHub/squiddy/.venv/bin/python scripts/build_admission_candidates.py [--check]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
GRAPH_ROOT = REPO / "graphs/aacps-policy-dm"
OUT = REPO / "corpus/admission/candidates.yaml"
DECISIONS = REPO / "corpus/admission/dispositions.yaml"
KIT_DISPOSITIONS = {"active", "metadata_only", "reference", "excluded:out_of_scope", "excluded:deferred",
                    "excluded:document_removed"}
SHA_IN_PROSE = re.compile(r"sha256 ([0-9a-f]{64})")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel_to_graph(path: Path) -> str:
    """local_path relative to the graph root (the kit resolves it there), so a worktree with corpus/ linked works."""
    return str(Path("../..") / path.relative_to(REPO))


def load_candidate_records() -> dict[str, dict]:
    recs: dict[str, dict] = {}
    for name in ("aacps-policy-dm.yaml", "aacps-policy-dm_related_entries.yaml", "md-law-and-msde-guidance.yaml"):
        raw = yaml.safe_load((REPO / "corpus/candidates" / name).read_text())
        items = raw["candidates"] if isinstance(raw, dict) else raw
        for c in items:
            if c["id"] in recs:
                raise SystemExit(f"FATAL: candidate id {c['id']} appears twice across corpus/candidates/")
            recs[c["id"]] = {**c, "_file": f"corpus/candidates/{name}"}
    return recs


def build() -> dict:
    dec = yaml.safe_load(DECISIONS.read_text())
    recs = load_candidate_records()
    legal = yaml.safe_load((REPO / "corpus/legal_refs.yaml").read_text())
    receipts: dict[str, dict] = {}
    for ln in (REPO / legal["receipts"]).read_text().splitlines():
        if ln.strip():
            r = json.loads(ln)
            receipts[r["id"]] = r            # the last receipt per id wins (a retry supersedes a failure)
    substrate = {u["id"]: u for u in yaml.safe_load((REPO / "corpus/substrate.yaml").read_text())["units"]}
    sub_cfg = yaml.safe_load((REPO / "corpus/substrate.yaml").read_text())
    sub_dir = REPO / sub_cfg["out_dir"]

    out: list[dict] = []
    merged: list[dict] = []
    per_id = dec["entries"]

    def held_fields(cid: str, acquired: Path, raw_sha: str | None) -> dict:
        """The file the kit parses: the substrate when one was converted, else the acquired file itself."""
        if cid in substrate:
            md = sub_dir / f"{cid}{sub_cfg['out_suffix']}"
            if not md.is_file():
                raise SystemExit(f"FATAL: {cid}: substrate {md} missing; run scripts/convert_substrate.py")
            return {"local_path": rel_to_graph(md), "sha256": sha256_file(md), "raw_sha256": raw_sha,
                    "raw_path": rel_to_graph(acquired), "substrate_converter": substrate[cid]["converter"]}
        return {"local_path": rel_to_graph(acquired), "sha256": sha256_file(acquired), "raw_sha256": raw_sha}

    # 1. the hand-written candidate records
    for cid, c in recs.items():
        d = per_id.get(cid)
        if d is None:
            raise SystemExit(f"FATAL: candidate {cid} ({c['_file']}) has no decision in {DECISIONS.name}; every "
                             f"candidate gets a disposition")
        if d.get("merge_into"):
            merged.append({"id": cid, "merged_into": d["merge_into"], "why": d["why"]})
            continue
        entry = {"id": cid, "kind": "work", "title": c["title"], "source_url": c.get("source_url"),
                 "publisher": c.get("publisher"), "doc_type": c.get("doc_type") or c.get("document_type"),
                 "access": c.get("access"), "licence_basis": c.get("licence_basis") or c.get("basis"),
                 "access_note": c.get("access_note"), "candidate_record": c["_file"],
                 "cited_in": d["cited_in"], "disposition": d["disposition"]}
        inbox = REPO / "corpus/inbox"
        acquired = next(iter(sorted(inbox.glob(f"{cid}.*"))), None)
        if cid in receipts and receipts[cid]["status"] == "ok":
            acquired = REPO / receipts[cid]["path"]
        if d.get("held_file"):
            acquired = REPO / d["held_file"]
        if d["disposition"] == "active":
            if acquired is None or not acquired.is_file():
                raise SystemExit(f"FATAL: {cid} is decided active and no held file exists")
            stated = SHA_IN_PROSE.search(c.get("access_note") or "")
            actual = sha256_file(acquired)
            if stated and stated.group(1) != actual:
                raise SystemExit(f"FATAL: {cid}: the receipt's sha256 {stated.group(1)} is not the held file's "
                                 f"{actual}; the file changed after acquisition")
            entry.update(held_fields(cid, acquired, actual))
            entry["acquisition"] = "operator_download" if c.get("access") == "browser" else "script_fetch"
            if cid in receipts:
                r = receipts[cid]
                entry.update(retrieved_at=r["retrieved_at"], fetch_url=r["url"], final_url=r.get("final_url"),
                             citation=r.get("citation"), acquisition="script_fetch", access="machine")
        else:
            entry["withheld_reason"] = d["withheld_reason"]
        for k in ("supersedes", "superseded_by", "note"):
            if d.get(k):
                entry[k] = d[k]
        out.append(entry)

    # 2. the Part B legal references with no hand-written record (fetched, or cataloged only)
    seen = {e["id"] for e in out} | {m["id"] for m in merged}
    for unit in legal["fetch"]:
        if unit["id"] in seen:
            continue
        r = receipts.get(unit["id"])
        if not r or r["status"] != "ok":
            raise SystemExit(f"FATAL: {unit['id']}: no ok receipt; run scripts/fetch_legal_refs.py")
        acquired = REPO / r["path"]
        if sha256_file(acquired) != r["sha256"]:
            raise SystemExit(f"FATAL: {unit['id']}: held file no longer matches its receipt")
        entry = {"id": unit["id"], "kind": "work", "title": unit["title"], "source_url": r.get("final_url") or r["url"],
                 "publisher": "Office of the Law Revision Counsel via GovInfo" if "govinfo" in r["url"]
                 else "eCFR (Office of the Federal Register)",
                 "doc_type": "federal statute" if "uscode" in r["url"] else "federal regulation",
                 "access": "machine", "licence_basis": "public-domain (US government work)",
                 "cited_in": f"draft Policy DM page 2, Legal References: {unit['draft_footer_name']}",
                 "disposition": "active", "acquisition": "script_fetch", "retrieved_at": r["retrieved_at"],
                 "fetch_url": r["url"], "final_url": r.get("final_url"), "citation": unit["citation"]}
        entry.update(held_fields(unit["id"], acquired, r["sha256"]))
        if unit.get("note"):
            entry["note"] = unit["note"]
        out.append(entry)
        seen.add(unit["id"])
    for ref in legal["catalog_only"]:
        out.append({"id": ref["id"], "kind": "work", "title": ref["title"], "source_url": ref["canonical_url"],
                    "doc_type": "federal statute" if ref["id"] != "comar-13a" else "state regulation",
                    "access": ref.get("access", "machine"), "access_note": ref.get("access_note"),
                    "licence_basis": "public-domain (US government work)" if ref["id"] != "comar-13a"
                    else "public-record", "citation": ref["citation"],
                    "cited_in": f"draft Policy DM page 2, Legal References: {ref['draft_footer_name']}",
                    "disposition": "reference",
                    "withheld_reason": ref.get("withheld_reason") or
                    "cataloged only: the draft cites it as general compliance and no DN-002 anchor needs a section "
                    "(AP-02 Part B)"})
        seen.add(ref["id"])

    # 3. documents no candidate file records (the snapshot)
    for extra in dec.get("extra") or []:
        path = REPO / extra["held_file"]
        entry = {k: v for k, v in extra.items() if k != "held_file"}
        entry.update(kind="work", disposition="active", acquisition="operator_download")
        entry.update(held_fields(extra["id"], path, sha256_file(path)))
        out.append(entry)

    for e in out:
        if e["disposition"] not in KIT_DISPOSITIONS:
            raise SystemExit(f"FATAL: {e['id']}: disposition {e['disposition']!r} is not in the graph's list")
        if not str(e.get("cited_in") or "").strip():
            raise SystemExit(f"FATAL: {e['id']}: empty cited_in; the assess criterion would decline it silently")
    ids = [e["id"] for e in out]
    if len(ids) != len(set(ids)):
        raise SystemExit("FATAL: duplicate ids in the output")
    for e in out:
        for target in e.get("supersedes") or []:
            if target not in ids:
                raise SystemExit(f"FATAL: {e['id']} supersedes {target}, which is not cataloged")
    clean = [{k: v for k, v in e.items() if v is not None} for e in out]
    return {"recorded_decision": dec["recorded_decision"], "candidates": clean, "merged": merged}


def render(doc: dict) -> str:
    head = ("# GENERATED by scripts/build_admission_candidates.py from corpus/candidates/, corpus/legal_refs*.\n"
            "# corpus/substrate/ and corpus/admission/dispositions.yaml. Do not edit; edit the inputs and re-run.\n")
    return head + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=120)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="exit 1 if the committed output differs from a rebuild")
    args = ap.parse_args(argv)
    text = render(build())
    if args.check:
        current = OUT.read_text() if OUT.is_file() else ""
        if current != text:
            print(f"{OUT.relative_to(REPO)} is stale: re-run without --check", file=sys.stderr)
            return 1
        print("up to date")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    doc = yaml.safe_load(text)
    from collections import Counter
    print(f"wrote {OUT.relative_to(REPO)}: {len(doc['candidates'])} entries "
          f"{dict(Counter(c['disposition'] for c in doc['candidates']))}; merged {len(doc['merged'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
