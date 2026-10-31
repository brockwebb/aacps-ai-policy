# aacps-ai-policy

An open, machine-readable review of Anne Arundel County Public Schools' draft **Policy DM, Responsible
Use of Artificial Intelligence** (October 2026), built with the tools the policy proposes to govern.

What this repository does:

1. Collects the draft policy and every document it cites or depends on into a public corpus with full
   provenance (URL, sha256, retrieval date, licence or public-record status).
2. Builds a knowledge graph of that corpus with [squiddy](https://github.com/brockwebb/squiddy), reusing
   the schema of the federal statistical policy graph: definitions, obligations, references, conflicts.
3. Queries the graph for contradictions between documents, undefined or inconsistently defined terms,
   obligations with no enforcing mechanism, and claims with no citation.
4. Produces a public comment, with every finding traceable to a document, section and quote.

Everything here is public. Code is MIT; data, graph exports and the comment are CC BY 4.0.

## Layout

| path | what |
|------|------|
| `corpus/` | manifest and inbox for documents (hand-acquired files go in `corpus/inbox/`, never committed if bulky; the manifest carries provenance) |
| `graphs/aacps-policy-dm/` | the squiddy graph: `graph.yaml` spec, rendered config, ledger, exports, evidence |
| `docs/design/` | design notes (scope, schema reuse decision, findings method) |
| `cc_tasks/` | work specification files for Claude Code |
| `comment/` | the public comment as submitted, with its evidence appendix |

## Status

Scaffold. First task: `cc_tasks/2026-10-31_AP-01_scope_corpus_and_graph_spec.md`.
