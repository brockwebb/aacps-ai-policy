"""The Policy DM graph's extraction protocol for the kit's stage 10a (squiddy SQ-021 contract; DN-003).

`engine.extract.protocol` names this file; `squiddy.extract.extract_by_protocol` calls `plan` and `rows`, makes one
model call per unit on the kit's pool under the kit's spend job, and checkpoints every settled call (keyed by unit id,
prompt sha256, role and model; constitution section 15). This file makes no call and holds no state.

- THE UNITS. The parsed intermediate (`corpus/parsed/<id>.json`, the kit's parse) is cut into consecutive blocks of
  at most `domain.extract.unit_max_chars`, cut at a heading where it can be, so a section and its body travel together
  (fss-policy-kg Defect A: a definitions heading split from its body truncated 70 percent of its definitions).
- THE PROMPT. `domain.extract.prompt_file`, filled per unit; its sha256 is the unit's prompt hash.
- THE ROWS. Each answer parsed as `{"items": [...]}`; each item's `text` located VERBATIM in the parsed text
  (whitespace, quote and dash forms normalised, nothing else), and its span is a character range of `plain_text`.
  Obligation force must be one of four values (fss-policy-kg's closed vocabulary; the spec cannot declare an enum).
  References resolve to a cataloged id by `domain.extract.citation_aliases`, else to `ref:<slug>`.
  A row the protocol cannot ground is kept in the evidence file with its reason (`ungrounded`, `unparseable`,
  `task_failed`), never emitted.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

import yaml

FORCES = ("obligation", "prohibition", "permission", "recommendation")
ITEM_TYPES = ("obligation", "definition", "reference")
SKIP_KINDS = {"frontmatter", "page_header", "page_footer"}
_TRANSLATE = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-",
                            "—": "-", " ": " ", "‑": "-"})
_SLUG = re.compile(r"[^a-z0-9]+")


def slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return _SLUG.sub("_", s.lower()).strip("_")


def _xcfg(graph) -> dict:
    x = (graph.domain.get("extract") or {})
    for k in ("prompt_file", "prompt_version", "unit_max_chars", "citation_aliases"):
        if k not in x:
            raise SystemExit(f"FATAL: domain.extract.{k} is missing from the graph spec (DN-003 section 3)")
    return x


def _parsed(graph, doc_id: str) -> dict | None:
    path = graph.root / graph.engine["paths"].get("parsed_dir", "corpus/parsed") / f"{doc_id}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def cut_units(blocks: list[dict], max_chars: int) -> list[list[dict]]:
    """Consecutive text blocks, at most `max_chars` of text each (a single longer block is its own unit), cut before
    a heading once the unit holds half its budget."""
    units, cur, size = [], [], 0
    for b in blocks:
        if b.get("kind") in SKIP_KINDS or not (b.get("text") or "").strip():
            continue
        n = len(b["text"]) + 2
        heading = b.get("kind") in ("heading", "title", "section_header")
        if cur and (size + n > max_chars or (heading and size >= max_chars // 2)):
            units.append(cur)
            cur, size = [], 0
        cur.append(b)
        size += n
    if cur:
        units.append(cur)
    return units


def plan(graph, entry: dict) -> dict:
    x = _xcfg(graph)
    doc_id = entry["id"]
    parsed = _parsed(graph, doc_id)
    if parsed is None or not parsed.get("blocks"):
        return {"role": None, "units": [], "why": f"{doc_id}: no parsed text (metadata-only or not yet parsed)"}
    template = (graph.root / x["prompt_file"]).read_text(encoding="utf-8")
    role = (graph.engine.get("extract") or {}).get("roles", {}).get("extractor")
    if not role:
        raise SystemExit("FATAL: engine.extract.roles.extractor is not set")
    units = []
    for i, blocks in enumerate(cut_units(parsed["blocks"], int(x["unit_max_chars"]))):
        text = "\n\n".join(b["text"] for b in blocks)
        section = blocks[0].get("section_path") or ""
        prompt = (template.replace("{doc_title}", str(entry.get("title") or doc_id))
                  .replace("{doc_type}", str(entry.get("doc_type") or "document"))
                  .replace("{section_path}", section or "(document start)")
                  .replace("{unit_text}", text))
        units.append({"id": f"{doc_id}#u{i:03d}", "prompt": prompt,
                      "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                      "block_idx": [b["idx"] for b in blocks], "chars": len(text),
                      "oversize": len(text) > int(x["unit_max_chars"])})
    return {"role": role, "units": units,
            "doc": {"source_sha256": parsed.get("source_sha256"), "parser_version": parsed.get("parser_version"),
                    "plain_sha256": hashlib.sha256(parsed["plain_text"].encode("utf-8")).hexdigest()},
            "instrument": {"protocol": "aacps-dm-extract", "prompt_version": x["prompt_version"],
                           "prompt_file": x["prompt_file"], "role": role, "unit_max_chars": int(x["unit_max_chars"])}}


def _norm_with_map(s: str) -> tuple[str, list[int]]:
    """`s` with quotes and dashes unified and every whitespace run collapsed to one space, and for each character of
    the result the index in `s` it came from."""
    out, idx, prev_space = [], [], False
    for i, ch in enumerate(s.translate(_TRANSLATE)):
        if ch.isspace():
            if prev_space:
                continue
            out.append(" ")
            idx.append(i)
            prev_space = True
        else:
            out.append(ch)
            idx.append(i)
            prev_space = False
    return "".join(out), idx


def locate(needle: str, hay: str, lo: int = 0, hi: int | None = None) -> tuple[int, int, int] | None:
    """(start, end, matches) of `needle` in hay[lo:hi] under the normalisation, as indices of `hay`; None if absent."""
    hi = len(hay) if hi is None else hi
    region = hay[lo:hi]
    nh, idx = _norm_with_map(region)
    nn, _ = _norm_with_map(needle.strip())
    nn = nn.strip()
    if not nn:
        return None
    at = nh.find(nn)
    if at < 0:
        return None
    matches = nh.count(nn)
    start = lo + idx[at]
    end = lo + idx[at + len(nn) - 1] + 1
    return start, end, matches


def parse_answer(content: str) -> list[dict] | None:
    s = (content or "").strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s)
    try:
        obj = json.loads(s)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", s, re.S)
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    items = obj.get("items") if isinstance(obj, dict) else None
    return items if isinstance(items, list) else None


def load_aliases(graph) -> list[tuple[re.Pattern, str]]:
    path = (graph.root / _xcfg(graph)["citation_aliases"]).resolve()
    rules = yaml.safe_load(path.read_text(encoding="utf-8"))["rules"]
    return [(re.compile(r["pattern"], re.I), r["id"]) for r in rules]


def resolve_reference(text: str, instrument: str | None, aliases, cataloged: set[str]) -> tuple[str, str]:
    for probe in (text, instrument or ""):
        for rx, target in aliases:
            if rx.search(probe or ""):
                if target not in cataloged:
                    raise SystemExit(f"FATAL: citation alias names {target!r}, which the manifest does not hold")
                return target, "work"
    return f"ref:{slug(instrument or text)[:80]}", "external"


def rows(graph, entry: dict, plan: dict, results: list[dict]) -> list[dict]:
    from squiddy import manifest as mf
    doc_id = entry["id"]
    parsed = _parsed(graph, doc_id)
    plain = parsed["plain_text"]
    if hashlib.sha256(plain.encode("utf-8")).hexdigest() != plan["doc"]["plain_sha256"]:
        raise SystemExit(f"FATAL: {doc_id}: the parsed text changed between plan and rows")
    blocks = {b["idx"]: b for b in parsed["blocks"]}
    _s, _m, docs = mf.load_manifest(graph.manifest_path)
    cataloged = {d["id"] for d in docs}
    aliases = load_aliases(graph)
    inst = plan["instrument"]
    out = []
    for r in results:
        u = r["unit"]
        if r["status"] != "ok":
            out.append({"status": r["status"], "unit": u["id"], "error": r.get("error")})
            continue
        items = parse_answer(r["content"])
        if items is None:
            out.append({"status": "unparseable", "unit": u["id"], "error": (r["content"] or "")[:300]})
            continue
        ublocks = [blocks[i] for i in u["block_idx"]]
        lo = min(b["char_span"][0] for b in ublocks)
        hi = max(b["char_span"][1] for b in ublocks)
        extractor = {"provider": "claude_cli", "model_role": inst["role"], "model": r.get("resolved_model"),
                     "prompt_sha256": u["prompt_sha256"], "prompt_version": inst["prompt_version"]}
        for it in items:
            base = {"unit": u["id"], "extractor": extractor}
            if not isinstance(it, dict) or it.get("type") not in ITEM_TYPES or not isinstance(it.get("text"), str):
                out.append({**base, "status": "ungrounded", "why": "malformed_item", "item_raw": it})
                continue
            item, text = it["type"], it["text"]
            got = locate(text, plain, lo, hi)
            if got is None:
                out.append({**base, "status": "ungrounded", "why": "text_not_in_passage", "item": item,
                            "text_claimed": text[:500]})
                continue
            start, end, matches = got
            blk = next((b for b in ublocks if b["char_span"][0] <= start < b["char_span"][1]), ublocks[0])
            # the kit's GroundingSpan exactly (squiddy schema/core.yaml): the located text's digest so the slice is
            # verifiable, the whole text's so a re-parse that moves offsets is detectable. How many times the text
            # occurs in the unit is this protocol's own diagnostic, so it rides on the row, not in the span.
            row = {**base, "status": "grounded", "item": item, "text": plain[start:end],
                   "span": {"start": start, "end": end,
                            "sha256": hashlib.sha256(plain[start:end].encode("utf-8")).hexdigest(),
                            "parsed_sha256": plan["doc"]["plain_sha256"]},
                   "matches_in_unit": matches, "section_path": blk.get("section_path"), "page": blk.get("page")}
            if item == "obligation":
                if it.get("force") not in FORCES:
                    out.append({**base, "status": "ungrounded", "why": "force_outside_vocabulary", "item": item,
                                "force_claimed": it.get("force"), "text_claimed": text[:500]})
                    continue
                row.update(force=it["force"], binds=it.get("binds") or None,
                           responsible_party_stated=bool(it.get("responsible_party_stated")),
                           mechanism_stated=it.get("mechanism_stated") or None)
            elif item == "definition":
                term = (it.get("term") or "").strip()
                if not term:
                    out.append({**base, "status": "ungrounded", "why": "definition_without_term",
                                "text_claimed": text[:500]})
                    continue
                row["term"] = term
            else:
                target, kind = resolve_reference(plain[start:end], it.get("cited_instrument"), aliases, cataloged)
                row.update(target=target, target_kind=kind, cited_instrument=it.get("cited_instrument"))
            out.append(row)
    return out
