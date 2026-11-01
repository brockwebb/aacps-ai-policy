"""scripts/conflict_pass.py: pairing, verdict validation, and constitution 15.8 (SIGKILL mid-loop, resume)."""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import conflict_pass as cp  # noqa: E402
import policy_graph as pg  # noqa: E402


def write_export(tmp: Path) -> Path:
    nodes = [{"id": "Work::draft", "label": "Work", "key": "draft"}, {"id": "Work::reg", "label": "Work", "key": "reg"}]
    links = []
    stmts = [("d1", "draft", "prohibition", "AI may only be used for approved instructional purposes."),
             ("d2", "draft", "obligation", "AACPS shall monitor tools for biased outcomes."),
             ("r1", "reg", "permission", "Staff may use approved instructional software purposes freely."),
             ("r2", "reg", "permission", "Teachers may monitor biased tools outcomes."),
             ("r3", "reg", "prohibition", "Vendors shall not monitor biased outcomes of tools."),
             ("r4", "reg", "obligation", "The board shall meet monthly.")]
    for key, doc, force, text in stmts:
        nodes.append({"id": f"Obligation::{key}", "label": "Obligation", "key": key, "force": force, "text": text})
        links.append({"type": "StatedIn", "source": f"Obligation::{key}", "target": f"Work::{doc}"})
    path = tmp / "export.json"
    path.write_text(json.dumps({"graph": {}, "nodes": nodes, "links": links}))
    return path


CFG = {"anchor_doc": "draft", "pairing": {"min_shared_terms": 2, "top_k": 5,
                                          "opposed": [["prohibition", "permission"], ["prohibition", "obligation"]]}}


def test_pairs_need_opposed_force_and_shared_terms():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        g = pg.load(write_export(Path(d)))
        got = {(p["a"]["key"], p["b"]["key"]) for p in cp.candidate_pairs(g, CFG)}
    # d1 (prohibition) x r1 (permission, shares approved/instructional/purposes): class A
    # d2 (obligation) x r3 (prohibition, shares monitor/biased/outcomes/tools): class B
    # d2 x r2 is obligation/permission: not opposed; r4 shares nothing
    assert got == {("d1", "r1"), ("d2", "r3")}


def test_parse_verdict_enforces_the_rubric_vocabulary():
    ok = cp.parse_verdict('{"verdict": "apparent_resolved", "resolution_basis": "hierarchy", "confidence": 0.7, '
                          '"rationale": "Federal law governs."}')
    assert ok["resolution_basis"] == "hierarchy"
    assert cp.parse_verdict('{"verdict": "apparent_resolved", "resolution_basis": null, "confidence": 0.7, '
                            '"rationale": "x"}') is None
    assert cp.parse_verdict('{"verdict": "no_conflict", "resolution_basis": "hierarchy", "confidence": 0.7, '
                            '"rationale": "x"}') is None
    assert cp.parse_verdict('{"verdict": "conflict", "resolution_basis": null, "confidence": 1, "rationale": "x"}') \
        is None
    assert cp.parse_verdict('{"verdict": "no_conflict", "resolution_basis": null, "confidence": "high", '
                            '"rationale": "x"}') is None


def test_sigkill_mid_loop_then_resume_calls_no_settled_pair_twice(tmp_path):
    """Constitution 15.8 on the real run loop: kill -9 after two calls, resume, and every pair is settled exactly once
    with the same verdict file an uninterrupted run writes."""
    export = write_export(tmp_path)
    # widen the fixture so there are more than two units: every draft x every opposed reg statement
    cfg = {**CFG, "graph_root": str(tmp_path), "rubric_file": str(tmp_path / "rubric.md"), "role": "adjudicator",
           "criteria_version": "t", "checkpoint": str(tmp_path / "verdicts.jsonl"),
           "progress_log": str(tmp_path / "progress.log"), "ranks": {"x": 1},
           "pairing": {**CFG["pairing"], "min_shared_terms": 0},
           "run": {"pilot_pairs": 1, "max_calls": 99, "max_billable_tokens": 10 ** 9, "progress_every_units": 1,
                   "timeout_seconds": 1, "max_turns": 1, "max_attempts": 2}}
    (tmp_path / "rubric.md").write_text("{text_a} || {text_b}")
    (tmp_path / "corpus").mkdir()
    (tmp_path / "corpus/manifest.yaml").write_text(yaml.safe_dump({"documents": [
        {"id": "draft", "doc_type": "x"}, {"id": "reg", "doc_type": "x"}]}))
    calls_log = tmp_path / "calls.log"
    driver = tmp_path / "driver.py"
    driver.write_text(textwrap.dedent(f"""
        import json, os, signal, sys
        sys.path.insert(0, {str(REPO / 'scripts')!r})
        import conflict_pass as cp, policy_graph as pg
        from pathlib import Path
        cfg = json.loads({json.dumps(json.dumps(cfg))})
        cp.REPO = Path("/")
        _load = pg.load
        cp.pg.load = lambda path=None: _load(Path({str(export)!r}))
        kill_after = int(sys.argv[1]); n = [0]
        class Inv:
            def __init__(s, c): s.content, s.usage, s.resolved_model = c, {{"input_tokens": 1, "output_tokens": 1}}, "m"
        class Client:
            model = "m"
            def invoke(self, prompt):
                with open({str(calls_log)!r}, "a") as fh: fh.write(prompt + "\\n")
                n[0] += 1
                if kill_after and n[0] > kill_after:
                    os.kill(os.getpid(), signal.SIGKILL)
                return Inv('{{"verdict": "no_conflict", "resolution_basis": null, "confidence": 0.9, "rationale": "r"}}')
        sys.exit(cp.run(cfg, client=Client()))
    """))
    first = subprocess.run([sys.executable, str(driver), "2"], capture_output=True, text=True)
    assert first.returncode == -9, first.stderr
    second = subprocess.run([sys.executable, str(driver), "0"], capture_output=True, text=True)
    assert second.returncode == 0, second.stderr
    prompts = calls_log.read_text().splitlines()
    rows = [json.loads(x) for x in (tmp_path / "verdicts.jsonl").read_text().splitlines()]
    settled = [r["pair_key"] for r in rows]
    assert len(settled) == len(set(settled)), "a settled pair was written twice"
    assert len(prompts) == len(settled) + 1, "only the unit in flight at the kill may be called again"
    assert len(settled) >= 3 and all(r["verdict"]["verdict"] == "no_conflict" for r in rows)


def _inproc_cfg(tmp_path, **run):
    export = write_export(tmp_path)
    (tmp_path / "rubric.md").write_text("{text_a} || {text_b}")
    (tmp_path / "corpus").mkdir(exist_ok=True)
    (tmp_path / "corpus/manifest.yaml").write_text(yaml.safe_dump({"documents": [
        {"id": "draft", "doc_type": "x"}, {"id": "reg", "doc_type": "x"}]}))
    cfg = {**CFG, "graph_root": str(tmp_path), "rubric_file": str(tmp_path / "rubric.md"), "role": "adjudicator",
           "criteria_version": "t", "checkpoint": str(tmp_path / "verdicts.jsonl"),
           "progress_log": str(tmp_path / "progress.log"), "ranks": {"x": 1},
           "pairing": {**CFG["pairing"], "min_shared_terms": 0},
           "run": {"pilot_pairs": 1, "max_calls": 99, "max_billable_tokens": 10 ** 9, "progress_every_units": 1,
                   "timeout_seconds": 1, "max_turns": 1, "max_attempts": 2, **run}}
    return cfg, export


class _Inv:
    def __init__(self, c):
        self.content, self.usage, self.resolved_model = c, {"input_tokens": 1, "output_tokens": 1}, "m"


OK = '{"verdict": "no_conflict", "resolution_basis": null, "confidence": 0.9, "rationale": "r"}'


def _patch(monkeypatch, export):
    monkeypatch.setattr(cp, "REPO", Path("/"))
    load = pg.load
    monkeypatch.setattr(cp.pg, "load", lambda path=None: load(export))


def test_a_failed_call_is_retried_on_resume_up_to_max_attempts(tmp_path, monkeypatch):
    """Constitution 15.7: a failure is a row and is retried under a bounded policy, never left settled as a failure."""
    cfg, export = _inproc_cfg(tmp_path, pilot_pairs=99)     # no pilot gate here: every unit fails on purpose
    _patch(monkeypatch, export)
    calls = []

    class Flaky:
        model = "m"

        def invoke(self, prompt):
            calls.append(prompt)
            raise RuntimeError("transport")
    assert cp.run(cfg, client=Flaky()) != 0
    n_units = len(calls)

    class Good:
        model = "m"

        def invoke(self, prompt):
            calls.append(prompt)
            return _Inv(OK)
    assert cp.run(cfg, client=Good()) == 0
    assert len(calls) == 2 * n_units                     # every failed unit called again, once
    assert cp.run(cfg, client=Good()) == 0 and len(calls) == 2 * n_units   # and then settled
    # a unit that fails max_attempts times is left as failed, not called forever
    (tmp_path / "b").mkdir()
    cfg2, _ = _inproc_cfg(tmp_path / "b", pilot_pairs=99)
    calls.clear()
    for _ in range(3):
        cp.run(cfg2, client=Flaky())
    assert len(calls) == 2 * n_units


def test_a_spend_refusal_stops_the_pass_and_writes_no_row(tmp_path, monkeypatch):
    """Nothing was sent, so it is not a unit's failure: the pass stops naming the reason and the same command resumes."""
    from squiddy.spend import SpendRefused
    cfg, export = _inproc_cfg(tmp_path)
    _patch(monkeypatch, export)
    seen = []

    class Governed:
        model = "m"

        def invoke(self, prompt):
            seen.append(prompt)
            if len(seen) > 1:
                raise SpendRefused("call_cap", "pilot cap")
            return _Inv(OK)
    assert cp.run(cfg, client=Governed()) == cp.EXIT_HELD
    rows = [json.loads(x) for x in Path(cfg["checkpoint"]).read_text().splitlines()]
    assert len(rows) == 1 and rows[0]["status"] == "ok"


def test_a_pilot_that_settles_nothing_aborts_before_the_rest(tmp_path, monkeypatch):
    cfg, export = _inproc_cfg(tmp_path, pilot_pairs=2, max_attempts=1)
    _patch(monkeypatch, export)
    seen = []

    class Broken:
        model = "m"

        def invoke(self, prompt):
            seen.append(prompt)
            return _Inv("not json")
    assert cp.run(cfg, client=Broken()) == cp.EXIT_PILOT_FAILED
    assert len(seen) == 2


def test_the_token_ceiling_counts_cache_tokens(tmp_path, monkeypatch):
    """The AP-02 run counted input+output only: ~10K of ~373K tokens processed (cache creation and reads dominate)."""
    cfg, export = _inproc_cfg(tmp_path, pilot_pairs=99, max_billable_tokens=1000)
    _patch(monkeypatch, export)
    seen = []

    class Cached:
        model = "m"

        def invoke(self, prompt):
            seen.append(prompt)
            inv = _Inv(OK)
            inv.usage = {"input_tokens": 1, "output_tokens": 1, "cache_creation_input_tokens": 600,
                         "cache_read_input_tokens": 600}
            return inv
    assert cp.run(cfg, client=Cached()) == cp.EXIT_CEILING
    assert len(seen) == 1
