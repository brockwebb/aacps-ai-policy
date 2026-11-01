"""graphs/aacps-policy-dm/extract_protocol.py: units, verbatim grounding, the closed force vocabulary, references."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
GRAPH = REPO / "graphs/aacps-policy-dm"
spec = importlib.util.spec_from_file_location("extract_protocol", GRAPH / "extract_protocol.py")
xp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(xp)


def test_locate_normalises_whitespace_quotes_and_dashes_only():
    hay = "Intro.  AI shall\nsupport, and may not replace, the “professional” judgment – always."
    got = xp.locate('AI shall support, and may not replace, the "professional" judgment - always.', hay)
    assert got is not None
    start, end, n = got
    assert hay[start:end].startswith("AI shall") and hay[start:end].endswith("always.") and n == 1
    assert xp.locate("AI shall support and may not replace", hay) is None, "a dropped comma is not verbatim"
    assert xp.locate("AI must support", hay) is None


def test_locate_respects_the_unit_window():
    hay = "AI shall be vetted. " * 2
    assert xp.locate("AI shall be vetted.", hay, lo=20)[0] == 20


def test_parse_answer_accepts_fenced_json_and_rejects_prose():
    assert xp.parse_answer('```json\n{"items": []}\n```') == []
    assert xp.parse_answer('Here you go: {"items": [{"type": "definition"}]} thanks') == [{"type": "definition"}]
    assert xp.parse_answer("no json at all") is None
    assert xp.parse_answer('{"claims": []}') is None


def test_cut_units_cuts_at_a_heading_and_skips_frontmatter():
    blocks = [{"idx": 0, "kind": "frontmatter", "text": "doc_id: x"},
              {"idx": 1, "kind": "heading", "text": "A"}, {"idx": 2, "kind": "text", "text": "a" * 60},
              {"idx": 3, "kind": "heading", "text": "B"}, {"idx": 4, "kind": "text", "text": "b" * 10}]
    units = xp.cut_units(blocks, max_chars=100)
    assert [[b["idx"] for b in u] for u in units] == [[1, 2], [3, 4]]


def test_resolve_reference_by_alias_then_external():
    aliases = [(xp.re.compile(r["pattern"], xp.re.I), r["id"]) for r in
               yaml.safe_load((REPO / "corpus/admission/citation_aliases.yaml").read_text())["rules"]]
    cat = {r[1] for r in aliases}
    assert xp.resolve_reference("34 CFR Part 99", None, aliases, cat) == ("ferpa-34cfr99", "work")
    assert xp.resolve_reference("Family Educational Rights and Privacy Act", None, aliases, cat) == \
        ("ferpa-20usc1232g", "work")
    assert xp.resolve_reference("DI-RA", None, aliases, cat) == ("aacps-reg-di-ra", "work")
    assert xp.resolve_reference("DI", None, aliases, cat) == ("aacps-policy-di", "work")
    assert xp.resolve_reference("Maryland Public Information Act", "Maryland Public Information Act", aliases,
                                cat) == ("ref:maryland_public_information_act", "external")
    with pytest.raises(SystemExit):
        xp.resolve_reference("34 CFR Part 99", None, aliases, set())


def _graph(tmp_path, plain, blocks):
    (tmp_path / "corpus/parsed").mkdir(parents=True)
    (tmp_path / "corpus/parsed/doc.json").write_text(json.dumps({"plain_text": plain, "blocks": blocks,
                                                                  "source_sha256": "s", "parser_version": "p"}))
    (tmp_path / "corpus/manifest.yaml").write_text(yaml.safe_dump({"schema": {}, "documents": [
        {"id": "doc"}, {"id": "ferpa-34cfr99"}]}))
    (tmp_path / "prompt.md").write_text("{doc_title}|{doc_type}|{section_path}|{unit_text}")
    (tmp_path / "aliases.yaml").write_text(yaml.safe_dump({"rules": [{"pattern": r"34 CFR Part 99",
                                                                       "id": "ferpa-34cfr99"}]}))
    return SimpleNamespace(root=tmp_path, manifest_path=tmp_path / "corpus/manifest.yaml",
                           engine={"paths": {"parsed_dir": "corpus/parsed"},
                                   "extract": {"roles": {"extractor": "extractor"}}},
                           domain={"extract": {"prompt_file": "prompt.md", "prompt_version": "t",
                                               "unit_max_chars": 1000, "citation_aliases": "aliases.yaml"}})


def test_rows_ground_classify_and_refuse(tmp_path):
    plain = "C. POSITION\n\n2. AI may only be used for approved purposes.\n\nSee 34 CFR Part 99."
    blocks = [{"idx": 0, "kind": "heading", "text": "C. POSITION", "char_span": [0, 11], "page": 2,
               "section_path": "C"},
              {"idx": 1, "kind": "list_item", "text": "2. AI may only be used for approved purposes.",
               "char_span": [13, 58], "page": 2, "section_path": "C"},
              {"idx": 2, "kind": "text", "text": "See 34 CFR Part 99.", "char_span": [60, 79], "page": 2,
               "section_path": "C"}]
    g = _graph(tmp_path, plain, blocks)
    pl = xp.plan(g, {"id": "doc", "title": "T"})
    assert pl["role"] == "extractor" and len(pl["units"]) == 1
    answer = {"items": [
        {"type": "obligation", "text": "2. AI may only be used for approved purposes.", "force": "prohibition",
         "binds": None, "responsible_party_stated": False, "mechanism_stated": None},
        {"type": "obligation", "text": "AI may only be used for approved purposes.", "force": "duty"},
        {"type": "obligation", "text": "AI shall be banned.", "force": "prohibition"},
        {"type": "reference", "text": "34 CFR Part 99", "cited_instrument": "FERPA regulations"},
        {"type": "definition", "text": "C. POSITION"}]}
    results = [{"unit": {k: v for k, v in pl["units"][0].items() if k != "prompt"}, "status": "ok",
                "content": json.dumps(answer), "resolved_model": "m"},
               {"unit": {"id": "doc#u999"}, "status": "task_failed", "error": "boom"}]
    out = xp.rows(g, {"id": "doc"}, pl, results)
    by = [(r["status"], r.get("why")) for r in out]
    assert by == [("grounded", None), ("ungrounded", "force_outside_vocabulary"),
                  ("ungrounded", "text_not_in_passage"), ("grounded", None),
                  ("ungrounded", "definition_without_term"), ("task_failed", None)]
    ob, ref = out[0], out[3]
    assert plain[ob["span"]["start"]:ob["span"]["end"]] == ob["text"] and ob["page"] == 2
    assert ob["responsible_party_stated"] is False and ob["force"] == "prohibition"
    assert ref["target"] == "ferpa-34cfr99" and ref["target_kind"] == "work"
    assert ob["extractor"]["model"] == "m" and ob["extractor"]["prompt_sha256"] == pl["units"][0]["prompt_sha256"]


def test_no_parsed_text_plans_no_unit(tmp_path):
    g = _graph(tmp_path, "x", [])
    (tmp_path / "corpus/parsed/doc.json").unlink()
    assert xp.plan(g, {"id": "doc"})["role"] is None
