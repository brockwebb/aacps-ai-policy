# AP-02: adopt Seldon, admit the corpus, extract, and test DN-002's eight anchors

**Repo:** aacps-ai-policy. L4: commit in this repo. Kit defects go to `../squiddy/cc_tasks/` as proposed filings (factory F-002), never fixed here.
**Date:** 2026-11-01. **Authored by:** the factory Desktop session (FCT-1).
**Read first:** CLAUDE.md, docs/design/2026-10-31_DN-001_scope.md, docs/design/2026-10-31_DN-002_prior_analysis_anchors.md, cc_tasks/2026-10-31_AP-01_RESULT.md, the three files in corpus/candidates/.
**After:** none
**Governing:** DN-001, DN-002 (this repo); squiddy DN-028 (anchors not questions), DN-034 (visibility public); factory F-002, F-009. No new ruling.
**Framework layer served (DN-005 §5 rule 1):** none (consumer graph).
**Model:** primary
**Spend:** est. 2.5M tokens plus extraction over 19 documents on the extractor and rater roles (most under 10 pages; the MSDE guidance and the two fiscal notes are the long ones). Floor 131K.
**Parts:** A 0.25, B 0.45, C 0.25, D 0.05.
**Network:** allowlist: www.ecfr.gov, ecfr.gov, www.govinfo.gov, govinfo.gov, uscode.house.gov
**Exclusive:** yes
**Premises:**
- premise: the inbox holds the 19 receipted documents | check: sh -c "test $(ls corpus/inbox/*.pdf corpus/inbox/*.txt | wc -l) -ge 19"
- premise: this repo is under seldon with a dispatch block (SEL-019) | check: sh -c "grep -q '^dispatch:' seldon.yaml"
- premise: the graph is initialized | check: sh -c "test -f graphs/aacps-policy-dm/config.yaml"

## Stop condition (AD-037-R6, by the dispatcher)

Tokens 4M. Stop and report if a kit defect blocks admission for more than two documents (file it, do not patch the kit here), or if any document's licence or public-record basis is in doubt.

## Why

All 19 browser-gated documents are acquired and receipted in `corpus/inbox/` (Desktop session, through the operator's Chrome; factory F-009). Seldon adoption of this repo is seldon SEL-019, which also registers this task; this task is launched by this repo's standing dispatcher, never by hand.

## Part A: the machine-fetchable legal references

Fetch by script into `corpus/inbox/` with the same receipt fields the other candidates carry (url, retrieval time, HTTP status, content type, sha256, bytes): FERPA 34 CFR 99, COPPA 16 CFR 312, PPRA 34 CFR 98, CIPA 47 CFR 54.520 (eCFR, current), and the statute sections: 20 USC 1232g, 20 USC 1232h, 15 USC 6501-6506, 47 USC 254(h)(5)-(6). IDEA, Section 504, ADA, Title VI and Title IX are cited in the draft's footer as general compliance; catalog them as `reference` with their canonical citations and do not admit their full texts unless an anchor query needs a specific section. COMAR Title 13A: catalog only, record the host posture; if it blocks, mark `access: browser` and stop on it (the Desktop session acquires it).

## Part B: admit and extract

Every inbox document through squiddy: catalog, assess, admit, parse, extract (valve opened for this graph; DN-001 kept it closed until there was a corpus). Obligations with deontic force, definitions, cross-references (Related Entries, legal references), and the conflict pass across documents. Record every kit friction as a filing in `../squiddy/cc_tasks/`. Close `squiddy init --check`'s known red (AP-01 noted classes declared but not yet emitted) by emitting them, not by stripping them.

## Part C: the anchors

For each anchor A1 to A8 in DN-002, a query against the graph and a verdict: `confirmed`, `refuted` or `partial`, with the exact document, section and quoted text (under 15 words per quote) that decides it, plus any document in the corpus that changes the anchor (for example, a definition of AI in the MSDE guidance or the Act that the draft could have adopted; the MSDE model local board policy's text against the draft's, clause by clause, since the draft appears to adapt it). Add anchors the graph surfaces that DN-002 missed, marked as new. Output: `docs/findings/2026-11-01_anchor_evidence.md` and the query file that produced it, so the table regenerates from the graph.

## Part D: the record

RESULT with the admitted count against the candidate count (every candidate has a disposition), extraction counts by class, the anchor table summary, kit filings, and the spend. Do not draft the public comment: it goes out under the operator's name and is written in a Desktop session from the anchor evidence.
