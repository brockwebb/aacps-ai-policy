"""The conflict pass (DN-003 section 4): force-opposed pairs with a draft Obligation on one side, adjudicated under
fss-policy-kg's rubric, one checkpointed model call per pair. Its verdict file is what the graph's `conflicts` layer
reads (`squiddy layer --graph graphs/aacps-policy-dm --id aacps-policy-dm-draft --layer conflicts`).

Constitution section 15, as implemented here:
- unit: one candidate pair; key = sha256(statement a, statement b, prompt sha256, role, model);
- checkpoint: `checkpoint` in config/conflict_pass.yaml, one JSON line per settled call, flushed and fsynced;
- resume: re-run the same command; a settled key is never called again;
- progress: every `progress_every_units` units and at the end, to stdout and `progress_log`;
- pilot: the first `pilot_pairs` units, then the measured tokens and seconds per unit and the projection are printed
  before the rest run;
- ceilings: `max_calls` and `max_billable_tokens`; crossing one stops new calls and exits 3 naming it;
- failures are rows (`status: failed`), and a partial run is reportable (`--report`).

    /Users/brock/GitHub/squiddy/.venv/bin/python scripts/conflict_pass.py --plan     # pairs only, no call
    /Users/brock/GitHub/squiddy/.venv/bin/python scripts/conflict_pass.py            # pilot, projection, the rest
    /Users/brock/GitHub/squiddy/.venv/bin/python scripts/conflict_pass.py --report   # what the checkpoint holds
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import policy_graph as pg  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
STOP = set("""a an the and or of to in on for by with as at from be is are was were been being shall may must
should will would can could not no nor any all each every such this that these those it its their them they which who
whom whose than then so if unless only also other others including include includes use used using under within into
upon per via ai aacps""".split())
VERDICTS = ("no_conflict", "apparent_resolved", "genuine_conflict")
BASES = ("specificity", "temporality", "hierarchy", "exception_clause")


def terms(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z][a-z\-]{2,}", (text or "").lower()) if w not in STOP}


def candidate_pairs(g: pg.PolicyGraph, cfg: dict) -> list[dict]:
    anchor = cfg["anchor_doc"]
    opp = {tuple(sorted(p)) for p in cfg["pairing"]["opposed"]}
    mine = g.statements("Obligation", anchor)
    others = [o for o in g.statements("Obligation") if o["doc"] and o["doc"] != anchor]
    pairs = []
    for a in mine:
        ta = terms(a["text"])
        scored = []
        for b in others:
            if tuple(sorted((a.get("force"), b.get("force")))) not in opp:
                continue
            shared = ta & terms(b["text"])
            if len(shared) >= cfg["pairing"]["min_shared_terms"]:
                scored.append((len(shared), b["key"], b, sorted(shared)))
        scored.sort(key=lambda t: (-t[0], t[1]))
        for n, _k, b, shared in scored[: cfg["pairing"]["top_k"]]:
            pairs.append({"a": a, "b": b, "shared_terms": shared})
    return pairs


def doc_meta(g: pg.PolicyGraph, doc: str, manifest: dict) -> tuple[str, str]:
    entry = manifest.get(doc) or {}
    return entry.get("title") or doc, entry.get("doc_type") or "unknown"


def fill(template: str, **kw) -> str:
    for k, v in kw.items():
        template = template.replace("{" + k + "}", str(v))
    return template


def parse_verdict(content: str) -> dict | None:
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", (content or "").strip())
    m = re.search(r"\{.*\}", s, re.S)
    if not m:
        return None
    try:
        v = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if v.get("verdict") not in VERDICTS:
        return None
    rb = v.get("resolution_basis")
    if (v["verdict"] == "apparent_resolved") != (rb in BASES):
        return None
    try:
        v["confidence"] = float(v.get("confidence"))
    except (TypeError, ValueError):
        return None
    if not isinstance(v.get("rationale"), str) or not v["rationale"].strip():
        return None
    return {"verdict": v["verdict"], "resolution_basis": rb, "confidence": v["confidence"],
            "rationale": v["rationale"].strip()}


def pair_key(a: str, b: str) -> str:
    return hashlib.sha256(f"{a}|{b}".encode()).hexdigest()[:16]


def unit_key(pk: str, prompt_sha: str, role: str, model: str) -> str:
    return hashlib.sha256(json.dumps([pk, prompt_sha, role, model]).encode()).hexdigest()


#: exit codes beyond 0 (every unit settled) and 1 (some unit failed or unparseable): 3 a ceiling of this pass, 4 the
#: kit's spend governor refused a call (nothing was sent; the same command resumes once the line is raised or the job
#: is re-declared under a measured estimate), 2 the pilot settled no unit, so no projection is possible
EXIT_PILOT_FAILED = 2
EXIT_CEILING = 3
EXIT_HELD = 4
#: a unit is SETTLED when the model answered, parseable or not (`unparseable` is the model's answer, kept and reported,
#: not re-bought); a `failed` row (an exception, nothing answered) is an attempt, retried up to `run.max_attempts`
SETTLED = ("ok", "unparseable")
#: the usage keys the CLI reports per call that count toward `run.max_billable_tokens`
TOKEN_KEYS = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def read_rows(path: Path) -> list[dict]:
    rows = []
    if path.is_file():
        for ln in path.read_text().splitlines():
            try:
                rows.append(json.loads(ln))
            except json.JSONDecodeError:
                continue          # a line torn by a kill is not a settled call; its unit re-runs
    return rows


def read_checkpoint(path: Path) -> tuple[dict[str, dict], Counter]:
    """(the settled row per unit key, the count of failed attempts per unit key)."""
    held, failed = {}, Counter()
    for r in read_rows(path):
        if r.get("status") in SETTLED:
            held[r["unit_key"]] = r
        else:
            failed[r["unit_key"]] += 1
    return held, failed


def append(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def log(cfg: dict, msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] {msg}"
    print(line, flush=True)
    p = REPO / cfg["progress_log"]
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as fh:
        fh.write(line + "\n")


def build_units(cfg: dict) -> tuple[list[dict], pg.PolicyGraph]:
    g = pg.load()
    manifest = {d["id"]: d for d in yaml.safe_load((REPO / cfg["graph_root"] / "corpus/manifest.yaml").read_text())
                ["documents"]}
    template = (REPO / cfg["rubric_file"]).read_text()
    units = []
    for p in candidate_pairs(g, cfg):
        a, b = p["a"], p["b"]
        ta, ty_a = doc_meta(g, a["doc"], manifest)
        tb, ty_b = doc_meta(g, b["doc"], manifest)
        for ty in (ty_a, ty_b):
            if ty not in cfg["ranks"]:
                raise SystemExit(f"FATAL: doc_type {ty!r} has no authority rank in config/conflict_pass.yaml")
        prompt = fill(template, criteria_version=cfg["criteria_version"],
                      rank_a=cfg["ranks"][ty_a], doc_a=ta, force_a=a.get("force"), binds_a=a.get("binds") or "none named",
                      text_a=a["text"], rank_b=cfg["ranks"][ty_b], doc_b=tb, force_b=b.get("force"),
                      binds_b=b.get("binds") or "none named", text_b=b["text"])
        pk = pair_key(a["key"], b["key"])
        units.append({"pair_key": pk, "prompt": prompt, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                      "a": {"id": a["key"], "doc": a["doc"], "force": a.get("force"), "text": a["text"]},
                      "b": {"id": b["key"], "doc": b["doc"], "force": b.get("force"), "text": b["text"]},
                      "shared_terms": p["shared_terms"]})
    return units, g


def _spend_job(cfg: dict, client, todo: list[dict]):
    """The kit's spend job around the pass (squiddy DN-042: every model call reserves on a declared job; there is no
    unmetered path). Declared the way the kit's own extraction declares one (squiddy/extract.py
    `extract_by_protocol`): `job_or_inherit`, so an operator's `squiddy spend declare` outside is used when present,
    and a pass with no measured history is cut to the kit's pilot and continues, on the same command, under the
    estimate that pilot measured. A client that is not the kit's governed provider (a test's) runs ungoverned."""
    import contextlib
    from squiddy import model_client as mc
    from squiddy import spend
    if getattr(client, "provider", None) != mc.PROVIDER:
        return contextlib.nullcontext()
    scfg = spend.config()
    gcfg = yaml.safe_load((REPO / cfg["graph_root"] / "config.yaml").read_text())
    name = gcfg["engine"]["graph"]["name"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    guess = sum(len(u["prompt"]) for u in todo) / float(scfg["estimate"]["guess_chars_per_token"]) * \
        float(scfg["weights"]["cache_write"])
    spec = {"job": f"conflict_pass:{cfg['criteria_version']}:{stamp}", "lane": f"{name}:conflict_pass",
            "graph": name, "model": client.model, "profile": client.spend_profile(), "node": "conflict_pass",
            "units": len(todo), "token_cap": float(scfg["job_token_cap_default"]),
            "call_cap": len(todo) * int(scfg["calls_per_unit"]),
            "approval_dir": str((REPO / cfg["checkpoint"]).parent), "graph_root": str(REPO / cfg["graph_root"])}
    return spend.job_or_inherit(spec, guess)


def run(cfg: dict, client=None) -> int:
    units, g = build_units(cfg)
    ck = REPO / cfg["checkpoint"]
    held, attempts = read_checkpoint(ck)
    max_attempts = int(cfg["run"]["max_attempts"])
    if client is None:
        from squiddy import model_client as mc
        client = mc.ClaudeCLIClient(role=cfg["role"], timeout=int(cfg["run"]["timeout_seconds"]),
                                    max_turns=int(cfg["run"]["max_turns"]))
    model = getattr(client, "model", "unknown")
    keyed = [(unit_key(u["pair_key"], u["prompt_sha256"], cfg["role"], model), u) for u in units]
    exhausted = [k for k, _u in keyed if k not in held and attempts[k] >= max_attempts]
    todo = [(k, u) for k, u in keyed if k not in held and attempts[k] < max_attempts]
    log(cfg, f"conflict pass: {len(units)} pair(s), {len(held)} settled, {len(exhausted)} failed {max_attempts} "
             f"time(s) and not retried, {len(todo)} to call (role {cfg['role']} -> {model}; export {g.meta['path']})")
    if not todo:
        return 1 if exhausted else 0
    calls = tokens = failed = settled_now = 0
    t0 = time.monotonic()
    pilot = int(cfg["run"]["pilot_pairs"])
    from squiddy import calls as kit_calls
    from squiddy.spend import SpendRefused
    with _spend_job(cfg, client, [u for _k, u in todo]):
        for i, (key, u) in enumerate(todo, 1):
            if calls >= cfg["run"]["max_calls"]:
                log(cfg, f"CEILING max_calls ({cfg['run']['max_calls']}) reached; {len(todo) - i + 1} unit(s) not "
                         f"called")
                return EXIT_CEILING
            if tokens >= cfg["run"]["max_billable_tokens"]:
                log(cfg, f"CEILING max_billable_tokens ({cfg['run']['max_billable_tokens']}) reached at {tokens}")
                return EXIT_CEILING
            row = {"unit_key": key, "pair_key": u["pair_key"], "attempt": attempts[key] + 1,
                   "a": u["a"], "b": u["b"], "shared_terms": u["shared_terms"], "prompt_sha256": u["prompt_sha256"],
                   "role": cfg["role"], "criteria_version": cfg["criteria_version"],
                   "settled_at": None, "run_id": f"conflict_pass:{cfg['criteria_version']}"}
            try:
                inv = kit_calls.invoke(client, u["prompt"])
            except SpendRefused as exc:
                # nothing was sent: not this unit's failure, so no row; the pass stops and the same command resumes
                log(cfg, f"HELD by the kit's spend governor ({exc.reason}) before unit {i}/{len(todo)}: {exc.detail}; "
                         f"{i - 1} unit(s) settled this run; re-run the same command to continue")
                return EXIT_HELD
            except Exception as exc:  # a failed call is a row (constitution 15.7), retried on the next run
                failed += 1
                row.update(status="failed", error=f"{type(exc).__name__}: {exc}"[:500], verdict=None)
            else:
                usage = inv.usage or {}
                # every token the call processed, cache creation and reads included: on the CLI they are most of it
                # (AP-02: input+output alone was ~10K of ~373K), so a ceiling on input+output bounds almost nothing
                tokens += sum(int(usage.get(k) or 0) for k in TOKEN_KEYS)
                v = parse_verdict(inv.content)
                row.update(resolved_model=inv.resolved_model, usage=usage, raw=(inv.content or "")[:2000],
                           status="ok" if v else "unparseable", verdict=v)
                if v is None:
                    failed += 1
                else:
                    settled_now += 1
            calls += 1
            row["settled_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            append(ck, row)
            if i == pilot and len(todo) > pilot:
                if settled_now == 0:
                    log(cfg, f"PILOT FAILED: none of the {i} pilot unit(s) settled a verdict (see {ck}); no "
                             f"projection is possible, so the other {len(todo) - i} are not called")
                    return EXIT_PILOT_FAILED
                per = (time.monotonic() - t0) / i
                log(cfg, f"PILOT {i} unit(s): {per:.1f} s/unit, {tokens / i:.0f} billable tokens/unit; projected for "
                         f"the {len(todo) - i} left: {per * (len(todo) - i) / 60:.1f} min, "
                         f"{tokens / i * (len(todo) - i):.0f} tokens (measured on the pilot)")
            if i % int(cfg["run"]["progress_every_units"]) == 0 or i == len(todo):
                el = time.monotonic() - t0
                log(cfg, f"progress {i}/{len(todo)}, {i / el * 60:.1f}/min, eta {(len(todo) - i) * el / i / 60:.1f} "
                         f"min, tokens {tokens}, failures {failed}")
    return 1 if failed or exhausted else 0


def report(cfg: dict) -> int:
    latest = {}
    for r in read_rows(REPO / cfg["checkpoint"]):
        latest[r["pair_key"]] = r
    c = Counter((r["status"], (r.get("verdict") or {}).get("verdict")) for r in latest.values())
    print(f"n={len(latest)} pairs settled: {dict(c)}")
    for r in latest.values():
        v = r.get("verdict") or {}
        if v.get("verdict") and v["verdict"] != "no_conflict":
            print(f"- {v['verdict']} ({v.get('resolution_basis')}, {v['confidence']}): {r['a']['id']} vs {r['b']['id']}"
                  f"\n    {v['rationale']}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", default=str(REPO / "config/conflict_pass.yaml"))
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args(argv)
    cfg = yaml.safe_load(Path(args.config).read_text())
    if args.report:
        return report(cfg)
    if args.plan:
        units, _g = build_units(cfg)
        print(f"{len(units)} candidate pair(s)")
        for u in units:
            print(f"- {u['a']['force']} {u['a']['id']} | {u['b']['force']} {u['b']['id']} shared={u['shared_terms']}")
        return 0
    return run(cfg)


if __name__ == "__main__":
    sys.exit(main())
