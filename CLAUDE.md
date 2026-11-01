# CLAUDE.md — aacps-ai-policy

## What this is

Second consumer of the squiddy kit (after hazbrief-mcp): a small public corpus graph of AACPS draft
Policy DM (Responsible Use of AI, Oct 2026) and its cited documents, used to produce a public comment.
Its purpose for the portfolio is to test that squiddy generalizes beyond the hazmat domain; its purpose
for the operator is the comment.

## Governing documents

1. `~/.claude/CLAUDE.md` (operating doctrine; prior art before judgment)
2. `~/GitHub/CLAUDE.md` (engineering standards)
3. `~/GitHub/factory/decisions.md` (F-002 defect ownership, F-003 repo concurrency)

## Rules

- Public only. No document that cannot be fetched or lawfully redistributed enters the graph; a declined
  document gets a manifest entry with the reason (fss-policy-kg rule, carried over).
- Schema: reuse fss-policy-kg's classes (Document, Definition, Obligation, Reference, Conflict) through
  squiddy; a new class needs a design note saying why the federal schema does not fit.
- Kit defects found here are filed as proposed task files in `../squiddy/cc_tasks/`, never fixed here
  (F-002). This repo's thread does not touch squiddy's or hazbrief's graph or tasks.
- Hand-acquired documents (hosts that block machine pulls) go to `corpus/inbox/` with a receipt line in
  the manifest: source URL, retrieval date, method (`browser`), sha256.
- No Google, no scraping of student or staff data, no personal data of any kind. The corpus is policy
  text and public meeting records only.

## Commands

Once the graph spec exists: `cd graphs/aacps-policy-dm && ../../../squiddy/.venv/bin/squiddy init . --config graph.yaml`
(renders config.yaml from graph.yaml; `--check` reports drift; bare `init` crashes, SQ-AP01a). The task files name every other command.

## Seldon

Not yet Seldon-managed. Adoption (seldon.yaml, dispatcher block, launchd job) is AP-02 if the project
runs longer than one task batch; a one-batch project does not need a dispatcher.
