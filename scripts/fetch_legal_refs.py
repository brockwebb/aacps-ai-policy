"""Fetch the machine-fetchable legal references of draft Policy DM into corpus/inbox/ with receipts (AP-02 Part B).

Every number, host and URL comes from corpus/legal_refs.yaml (constitution section 2). The loop is a network loop, so
it is checkpointed per constitution section 15, scaled to its size (thirteen free GETs, no model call, no spend):

- unit of work: one `fetch` entry; its key is (id, url), so a changed URL is a new unit, never a stale reuse;
- checkpoint: corpus/legal_refs_receipts.jsonl, one JSON line per finished unit (ok or failed), flushed and fsynced
  before the next request;
- resume rule: re-run the same command. A unit whose last receipt is `ok` and whose file on disk still hashes to the
  receipt's sha256 is skipped; anything else is fetched again;
- failures are rows: a unit that fails after the bounded retries gets a `failed` receipt with the error and the loop
  continues; the exit code is non-zero if any unit failed;
- no pilot and no ceiling: thirteen requests to two public government hosts cost nothing and take under a minute,
  so section 15.4 and 15.5's estimate and abort ceiling have nothing to bound. Recorded here as the decision.

The allowlist is enforced on the request URL and again on the final URL after redirects: a redirect off the list is
a failed unit, and its bytes are not written.

    /Users/brock/GitHub/squiddy/.venv/bin/python scripts/fetch_legal_refs.py [--config corpus/legal_refs.yaml]
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import yaml

REPO = Path(__file__).resolve().parent.parent


class FetchRefused(Exception):
    """A host outside the configured allowlist, before or after a redirect."""


def load_config(path: Path) -> dict:
    cfg = yaml.safe_load(path.read_text())
    for key in ("network", "inbox_dir", "receipts", "fetch"):
        if key not in cfg:
            raise SystemExit(f"{path}: required key `{key}` is missing")
    for key in ("allowlist", "user_agent", "timeout_seconds", "inter_request_delay_seconds", "retry_attempts",
                "retry_backoff_seconds"):
        if key not in cfg["network"]:
            raise SystemExit(f"{path}: required key `network.{key}` is missing")
    ids = [u["id"] for u in cfg["fetch"]]
    if len(ids) != len(set(ids)):
        raise SystemExit(f"{path}: duplicate fetch ids")
    return cfg


def unit_key(unit: dict) -> str:
    return f"{unit['id']}|{unit['url']}"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def read_receipts(path: Path) -> dict[str, dict]:
    """The last receipt per unit key (a later line wins: a retry after a failure supersedes it)."""
    last: dict[str, dict] = {}
    if not path.exists():
        return last
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{n}: unreadable receipt line ({exc}); repair the checkpoint by hand") from exc
        last[row["unit_key"]] = row
    return last


def is_done(unit: dict, receipts: dict[str, dict], repo: Path) -> bool:
    row = receipts.get(unit_key(unit))
    if not row or row.get("status") != "ok":
        return False
    held = repo / row["path"]
    return held.exists() and sha256_file(held) == row["sha256"]


def append_receipt(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def check_host(url: str, allowlist: list[str]) -> None:
    host = urlparse(url).hostname or ""
    if host not in allowlist:
        raise FetchRefused(f"host {host!r} is not on the allowlist")


def fetch_one(unit: dict, net: dict) -> tuple[bytes, dict]:
    check_host(unit["url"], net["allowlist"])
    # eCFR's versioner API answers 406 ("requires response compression") to a request that does not permit gzip
    # (observed 2026-11-01). The receipt's sha256 is over the DECODED document bytes, the file that is held.
    req = urllib.request.Request(unit["url"], headers={"User-Agent": net["user_agent"], "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=net["timeout_seconds"]) as resp:  # noqa: S310 (allowlisted https)
        final_url = resp.geturl()
        check_host(final_url, net["allowlist"])
        body = resp.read()
        encoding = resp.headers.get("Content-Encoding")
        if encoding == "gzip":
            body = gzip.decompress(body)
        elif encoding not in (None, "identity"):
            raise OSError(f"unsupported Content-Encoding {encoding!r}")
        meta = {
            "final_url": final_url,
            "http_status": resp.status,
            "content_type": resp.headers.get("Content-Type"),
            "content_encoding": encoding,
            "last_modified": resp.headers.get("Last-Modified"),
        }
    return body, meta


def run(config_path: Path, repo: Path = REPO, fetcher=fetch_one) -> int:
    cfg = load_config(config_path)
    net = cfg["network"]
    inbox = repo / cfg["inbox_dir"]
    receipts_path = repo / cfg["receipts"]
    receipts = read_receipts(receipts_path)
    units = cfg["fetch"]
    failed = 0
    started = time.monotonic()
    for i, unit in enumerate(units, 1):
        if is_done(unit, receipts, repo):
            print(f"[{i}/{len(units)}] {unit['id']}: done (receipt and sha256 match), skipped", flush=True)
            continue
        body, meta, error = None, {}, None
        for attempt in range(1, net["retry_attempts"] + 1):
            try:
                body, meta = fetcher(unit, net)
                break
            except FetchRefused as exc:
                error = f"refused: {exc}"
                break  # a refusal is a property of the URL, not a transient: never retried
            except urllib.error.HTTPError as exc:
                error = f"attempt {attempt}: HTTP {exc.code}: {exc.reason}"
                if exc.code < 500 and exc.code != 429:
                    break  # a 4xx other than 429 is the server's answer about the request, not a transient
                if attempt < net["retry_attempts"]:
                    time.sleep(net["retry_backoff_seconds"])
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                error = f"attempt {attempt}: {type(exc).__name__}: {exc}"
                if attempt < net["retry_attempts"]:
                    time.sleep(net["retry_backoff_seconds"])
        retrieved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        base = {"unit_key": unit_key(unit), "id": unit["id"], "url": unit["url"], "retrieved_at": retrieved_at,
                "citation": unit.get("citation")}
        if body is None:
            failed += 1
            append_receipt(receipts_path, {**base, "status": "failed", "error": error})
            print(f"[{i}/{len(units)}] {unit['id']}: FAILED ({error})", flush=True)
        else:
            out = inbox / f"{unit['id']}.{unit['ext']}"
            out.parent.mkdir(parents=True, exist_ok=True)
            tmp = out.with_suffix(out.suffix + ".part")
            tmp.write_bytes(body)
            os.replace(tmp, out)
            row = {**base, **meta, "status": "ok", "path": str(out.relative_to(repo)),
                   "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
            append_receipt(receipts_path, row)
            print(f"[{i}/{len(units)}] {unit['id']}: ok {meta['http_status']} {meta['content_type']} "
                  f"{len(body)} bytes", flush=True)
        time.sleep(net["inter_request_delay_seconds"])
    print(f"done: {len(units) - failed}/{len(units)} held, {failed} failed, "
          f"{time.monotonic() - started:.1f} s", flush=True)
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", default=str(REPO / "corpus/legal_refs.yaml"))
    args = ap.parse_args(argv)
    return run(Path(args.config))


if __name__ == "__main__":
    sys.exit(main())
