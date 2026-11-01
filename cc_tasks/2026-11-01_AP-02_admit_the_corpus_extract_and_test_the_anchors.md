# AP-02: adopt Seldon, admit the corpus, extract, and test DN-002's eight anchors

**Repo:** aacps-ai-policy. L4: commit in this repo. Kit defects go to `../squiddy/cc_tasks/` as proposed filings (factory F-002), never fixed here.
**Date:** 2026-11-01. **Authored by:** the factory Desktop session (FCT-1).
**Read first:** CLAUDE.md, docs/design/2026-10-31_DN-001_scope.md, docs/design/2026-10-31_DN-002_prior_analysis_anchors.md, cc_tasks/2026-10-31_AP-01_RESULT.md, the three files in corpus/candidates/.
**Model:** primary for the session; extraction roles from seldon's registry (extractor and rater sonnet, adjudicator opus). No Fable.
**Spend:** est. 2.5M tokens session plus extraction over 19 documents (most under 10 pages; the MSDE guidance and the two fiscal notes are the long ones). Stop at 4M.
**Network:** allowlist: www.ecfr.gov, ecfr.gov, www.govinfo.gov, govinfo.gov, uscode.house.gov, www.law.cornell.edu, github.com
**Exclusive:** yes

## Why

All 19 browser-gated documents are acquired and receipted in `corpus/inbox/` (Desktop session, through the operator's Chrome; factory F-009: no headless task fetches from a host that bot-challenges curl). This is the hand-launched bootstrap task the factory allows once per new repo (F-008); Part A makes every later task dispatchable.

## Part A: Seldon adoption (so AP-03 onward is dispatched, not hand launched)

`seldon init` for this repo as hazbrief-mcp and squiddy are set up: `seldon.yaml` with a dispatch block copied from `../hazbrief-mcp/seldon.yaml` (permission mode, stop file, lease, logs), a database named for the repo, and the standing dispatcher's launchd job installed the way seldon documents for a new project. Register AP-01 (closed) and this task. Verify with one dry dispatcher pass that reports this repo's queue.

## Part B: the machine-fetchable legal references

Fetch by script into `corpus/inbox/` with the same receipt fields the other candidates carry (url, retrieval time, HTTP status, content type, sha256, bytes): FERPA 34 CFR 99, COPPA 16 CFR 312, PPRA 34 CFR 98, CIPA 47 CFR 54.520 (eCFR, current), and the statute sections: 20 USC 1232g, 20 USC 1232h, 15 USC 6501-6506, 47 USC 254(h)(5)-(6). IDEA, Section 504, ADA, Title VI and Title IX are cited in the draft's footer as general compliance; catalog them as `reference` with their canonical citations and do not admit their full texts unless an anchor query needs a specific section. COMAR Title 13A: catalog only, record the host posture; if it blocks, mark `access: browser` and stop on it (the Desktop session acquires it).

## Part C: admit and extract

Every inbox document through squiddy: catalog, assess, admit, parse, extract (valve opened for this graph; DN-001 kept it closed until there was a corpus). Obligations with deontic force, definitions, cross-references (Related Entries, legal references), and the conflict pass across documents. Record every kit friction as a filing in `../squiddy/cc_tasks/`. Close `squiddy init --check`'s known red (AP-01 noted classes declared but not yet emitted) by emitting them, not by stripping them.

## Part D: the anchors

For each anchor A1 to A8 in DN-002, a query against the graph and a verdict: `confirmed`, `refuted` or `partial`, with the exact document, section and quoted text (under 15 words per quote) that decides it, plus any document in the corpus that changes the anchor (for example, a definition of AI in the MSDE guidance or the Act that the draft could have adopted; the MSDE model local board policy's text against the draft's, clause by clause, since the draft appears to adapt it). Add anchors the graph surfaces that DN-002 missed, marked as new. Output: `docs/findings/2026-11-01_anchor_evidence.md` and the query file that produced it, so the table regenerates from the graph.

## Part E: the record

RESULT with the dispatcher state after Part A, the admitted count against the candidate count (every candidate has a disposition), extraction counts by class, the anchor table summary, kit filings, and the spend. Do not draft the public comment: it goes out under the operator's name and is written in a Desktop session from the anchor evidence.
