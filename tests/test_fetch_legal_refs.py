"""scripts/fetch_legal_refs.py: receipts per unit, resume by skip, refusals and failures are rows (constitution 15)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("fetch_legal_refs", REPO / "scripts/fetch_legal_refs.py")
flr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flr)


def write_config(tmp: Path, units: list[dict]) -> Path:
    cfg = {
        "network": {"allowlist": ["www.ecfr.gov"], "user_agent": "test", "timeout_seconds": 1,
                    "inter_request_delay_seconds": 0, "retry_attempts": 2, "retry_backoff_seconds": 0},
        "inbox_dir": "inbox", "receipts": "receipts.jsonl", "fetch": units,
    }
    import yaml
    path = tmp / "cfg.yaml"
    path.write_text(yaml.safe_dump(cfg))
    return path


UNITS = [{"id": "a", "url": "https://www.ecfr.gov/a", "ext": "xml"},
         {"id": "b", "url": "https://www.ecfr.gov/b", "ext": "xml"}]


def fake_fetcher(calls: list):
    def fetch(unit, net):
        calls.append(unit["id"])
        return f"<doc>{unit['id']}</doc>".encode(), {"final_url": unit["url"], "http_status": 200,
                                                      "content_type": "application/xml", "last_modified": None}
    return fetch


def test_receipts_written_and_rerun_skips_every_completed_unit(tmp_path):
    cfg = write_config(tmp_path, UNITS)
    calls: list = []
    assert flr.run(cfg, repo=tmp_path, fetcher=fake_fetcher(calls)) == 0
    assert calls == ["a", "b"]
    rows = [json.loads(x) for x in (tmp_path / "receipts.jsonl").read_text().splitlines()]
    assert {r["id"] for r in rows} == {"a", "b"}
    for r in rows:
        assert r["status"] == "ok" and r["bytes"] > 0 and len(r["sha256"]) == 64
        assert (tmp_path / r["path"]).exists()
    calls.clear()
    assert flr.run(cfg, repo=tmp_path, fetcher=fake_fetcher(calls)) == 0
    assert calls == [], "a completed unit must never be fetched twice"


def test_a_tampered_file_is_fetched_again(tmp_path):
    cfg = write_config(tmp_path, UNITS)
    flr.run(cfg, repo=tmp_path, fetcher=fake_fetcher([]))
    (tmp_path / "inbox/a.xml").write_bytes(b"changed")
    calls: list = []
    flr.run(cfg, repo=tmp_path, fetcher=fake_fetcher(calls))
    assert calls == ["a"]


def test_changed_url_is_a_new_unit(tmp_path):
    cfg = write_config(tmp_path, UNITS)
    flr.run(cfg, repo=tmp_path, fetcher=fake_fetcher([]))
    cfg = write_config(tmp_path, [{**UNITS[0], "url": "https://www.ecfr.gov/a2"}, UNITS[1]])
    calls: list = []
    flr.run(cfg, repo=tmp_path, fetcher=fake_fetcher(calls))
    assert calls == ["a"]


def test_off_allowlist_host_is_a_failed_row_and_no_socket(tmp_path):
    cfg = write_config(tmp_path, [{"id": "x", "url": "https://dsd.maryland.gov/x", "ext": "html"}, UNITS[0]])
    rc = flr.run(cfg, repo=tmp_path)  # the real fetcher: refuses before any request
    assert rc == 1
    rows = [json.loads(x) for x in (tmp_path / "receipts.jsonl").read_text().splitlines()]
    bad = [r for r in rows if r["id"] == "x"][0]
    assert bad["status"] == "failed" and bad["error"].startswith("refused")
    assert not (tmp_path / "inbox/x.html").exists()


def test_transient_failure_is_a_row_and_does_not_stop_the_loop(tmp_path):
    cfg = write_config(tmp_path, UNITS)
    calls: list = []

    def flaky(unit, net):
        calls.append(unit["id"])
        if unit["id"] == "a":
            raise OSError("boom")
        return fake_fetcher([])(unit, net)

    assert flr.run(cfg, repo=tmp_path, fetcher=flaky) == 1
    assert calls == ["a", "a", "b"]  # two bounded attempts on a, then b
    rows = [json.loads(x) for x in (tmp_path / "receipts.jsonl").read_text().splitlines()]
    assert [r["status"] for r in rows] == ["failed", "ok"]


def test_sigkill_mid_loop_then_resume_equals_uninterrupted(tmp_path):
    """Constitution 15.8: SIGKILL mid-loop, restart, and the output equals an uninterrupted run's; no unit twice."""
    units = [{"id": f"u{i}", "url": f"https://www.ecfr.gov/{i}", "ext": "xml"} for i in range(4)]
    cfg = write_config(tmp_path, units)
    calls_log = tmp_path / "calls.log"
    driver = tmp_path / "driver.py"
    driver.write_text(textwrap.dedent(f"""
        import importlib.util, os, signal, sys
        from pathlib import Path
        spec = importlib.util.spec_from_file_location("f", {str(REPO / 'scripts/fetch_legal_refs.py')!r})
        f = importlib.util.module_from_spec(spec); spec.loader.exec_module(f)
        kill_after = int(sys.argv[1])
        n = [0]
        def fetch(unit, net):
            with open({str(calls_log)!r}, "a") as fh: fh.write(unit["id"] + "\\n")
            n[0] += 1
            if kill_after and n[0] > kill_after:
                os.kill(os.getpid(), signal.SIGKILL)
            return (unit["id"].encode(), {{"final_url": unit["url"], "http_status": 200,
                    "content_type": "application/xml", "last_modified": None}})
        sys.exit(f.run(Path({str(cfg)!r}), repo=Path({str(tmp_path)!r}), fetcher=fetch))
    """))
    first = subprocess.run([sys.executable, str(driver), "2"], capture_output=True)
    assert first.returncode == -9
    second = subprocess.run([sys.executable, str(driver), "0"], capture_output=True)
    assert second.returncode == 0, second.stderr
    calls = calls_log.read_text().split()
    completed_ok = [c for c in calls[:2]]
    assert calls.count("u0") == 1 and calls.count("u1") == 1, f"a completed unit was fetched twice: {calls}"
    assert set(calls) == {"u0", "u1", "u2", "u3"}
    for u in units:
        assert (tmp_path / f"inbox/{u['id']}.xml").read_bytes() == u["id"].encode()
    rows = [json.loads(x) for x in (tmp_path / "receipts.jsonl").read_text().splitlines()]
    assert sorted(r["id"] for r in rows if r["status"] == "ok") == ["u0", "u1", "u2", "u3"]
    assert completed_ok == ["u0", "u1"]


def test_the_shipped_config_loads_and_names_only_allowlisted_hosts():
    cfg = flr.load_config(REPO / "corpus/legal_refs.yaml")
    for unit in cfg["fetch"]:
        flr.check_host(unit["url"], cfg["network"]["allowlist"])
    with pytest.raises(flr.FetchRefused):
        flr.check_host("https://dsd.maryland.gov/", cfg["network"]["allowlist"])
