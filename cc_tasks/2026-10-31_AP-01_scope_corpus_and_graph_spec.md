# AP-01: scope the corpus, write the graph spec, initialize the graph

**Status:** proposed
**Author:** Desktop factory session, 2026-10-31 08:10 EDT
**Repo:** aacps-ai-policy. L4: commit in aacps-ai-policy only.
**Model:** primary
**Spend:** zero model calls beyond the session itself; no extraction. `squiddy init` is local.
**Network:** allowlist: aacps.org, www.aacps.org, marylandpublicschools.org, ed.gov, ecfr.gov, govinfo.gov
**Touches:** docs/design/, graphs/aacps-policy-dm/, corpus/
**Premises:**
- premise: squiddy's kit is importable from the sibling checkout | check: sh -c "test -x ../squiddy/.venv/bin/squiddy"
- premise: hazbrief's graph spec exists as the reference shape | check: sh -c "test -f ../hazbrief-mcp/graphs/hazbrief-corpus/graph.yaml"

## Why

The repo is a scaffold. Before any document is admitted the project needs a scope note, a candidate list
with provenance, and a squiddy graph spec that reuses the fss-policy-kg schema. This is the second
consumer of the kit; the point is to change nothing in squiddy and record every place the kit resists
a policy corpus (those become proposed tasks in `../squiddy/cc_tasks/`, F-002).

## Part A: scope note (docs/design/2026-10-31_DN-001_scope.md)

1. Scope statement in the operator's words (from CLAUDE.md and README): the draft policy, what it cites,
   what governs it, and public meeting records; nothing else.
2. Questions the comment must answer are NOT the input (squiddy DN-028); anchors are: definitional
   consistency, uncited claims, obligations without mechanism, conflicts between the draft and documents
   it cites or is bound by.
3. Prior art section: cite the fss-policy-kg schema (../icsp_notebook), its `docs/adding_a_document.md`,
   and hazbrief's graph.yaml as the shape. Name any public policy-analysis KG work found in a web search.

## Part B: candidate list (corpus/candidates/*.yaml)

Locate the draft Policy DM on aacps.org (board policy pages and the public comment page). For each
candidate record title, url, publisher, date, document type, licence or public-record basis, and host
access posture (fetchable by machine, or `browser` required). Do not download anything whose licence is
unclear. Record declined candidates with the reason.

## Part C: graph spec (graphs/aacps-policy-dm/graph.yaml)

Adapt hazbrief's graph.yaml. `policy: public_only`. Classes: Document, Definition, Obligation, Reference,
Conflict as fss-policy-kg names them, plus the kit's claim overlay only if the kit requires an edge class
(hazbrief's note on the two release gates). Extraction closed (`extract: closed`) until the downstream
test earns it. Run `squiddy init`; commit graph.yaml and the rendered config.yaml. Record every place the
spec needed a workaround.

## Part D: the record

`cc_tasks/..._AP-01_RESULT.md`: what was located, what was declined and why, the init outcome, and a list
of kit frictions each written as a proposed task file in `../squiddy/cc_tasks/` with a back-reference here.
