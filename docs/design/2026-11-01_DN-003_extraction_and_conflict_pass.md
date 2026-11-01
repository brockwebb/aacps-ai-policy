# DN-003: extraction, the conflict pass, and the admission path

**Date:** 2026-11-01. **Task:** AP-02 Part C. **Status:** decided (grounded; operator overrides if wrong).

## 1. Prior art this implements (read before building; operating doctrine section 1)

Search order followed: this repository's record (DN-001, DN-002), then the sibling repositories' record, which is where
the decomposition was already solved. No new literature search was run; the reason is in the last bullet.

- **fss-policy-kg** (`../icsp_notebook`) is the decomposition adopted, unchanged: Obligation with deontic force and
  addressee, Definition with term, Reference as a keyed node, Conflict adjudicated pairwise at a stamped criteria
  version.
  - `docs/2026-06-16_design_e3_extraction_architecture_resolved.md` (with its three corrections) and
    `docs/2026-06-16_e3_force_rootcause.md` supply the extraction lessons applied here:
    1. The prompt names every output key exactly and gives the force enum. fss's hollow extraction (force 0/8) was
       a key-name mismatch, not a capacity failure.
    2. Incidental modals ("may differ", "may be updated") get an explicit abstention instruction. Correct abstention
       is not laziness (correction 3).
    3. The section is the unit. A definitions heading split from its body truncated 70 percent of fss definitions
       (Defect A).
    4. Field values are validated after parsing, not only the JSON syntax (the CONSTRUCT / PARSE line, arXiv
       2510.08623).
  - `kg/conflict_rubric.md` is the conflict adjudication instrument, adopted with two changes. The domain sentence is
    changed. The authority ranks are supplied for this corpus (section 4).
- **Deontological Keyword Bias** (Park, Lee and Choi, arXiv 2506.11068, ACL 2025): LLM force classification
  over-fires on modal presence. Mitigations:
  - the abstention instruction above;
  - `responsible_party_stated` and `mechanism_stated` recorded as separate fields, so DN-001's anchor 3 ("obligation
    without mechanism") is read from the text rather than inferred from the modal.

  This threat is named here, as fss names it.
- **Defeasible Deontic Logic via LLMs** (Horner, Mateis, Governatori, Ciabattoni, ASAIL 2025): conflicts between norms
  are resolved by priority (lex superior, lex specialis, lex posterior). That is the rubric's step 4.
- **Why no fresh search.** Both papers were read and their citations verified in fss's citation-verification task
  (`docs/2026-06-16_e3_citation_verification.md`, rows 9 and 12). This session was NOT re-reading them: arxiv.org is
  outside AP-02's Network line. DN-001 section 3 asked for two papers before the prompt was written; these are the
  two, read through fss's verified record and not re-read here.
- **ai-readiness-kg** (`graphs/ai-readiness/extract_protocol.py`, `emit.py`) is the kit precedent for a graph-declared
  protocol that emits non-Claim classes (squiddy SQ-021, DN-049 R-211). This graph adopts its contract (`plan`,
  `rows`, `emit_extraction`). It departs in units (sections, not ai-readiness's chunker) and in prompt (fss's, not
  ai-readiness's twelve-class schema).
- **document-ingest** (ai-readiness-kg DD-030, the skill) supplies the substrate contract and the HTML converter
  choice (docling, measured). The extent gate's thresholds come from Kohlschuetter et al., WSDM 2010.

## 2. Schema additions (CLAUDE.md: a new class needs a note saying why the federal schema does not fit)

- **`StatedIn` edge**, (Obligation | Definition)-[:STATED_IN]->(Work).
  - fss ties an Obligation to its document through a Segment node and a `source_doc` property.
  - This graph holds no Segment nodes, because the kit's parsed intermediate is the segment record. So the tie is one
    edge carrying the located span.
  - The kit's `Asserts` edge is not used: its range is Claim.
- **Obligation attributes** `responsible_party_stated` and `mechanism_stated`. They exist for DN-001 anchor 3. fss has
  `addressee` (here `binds`) but no mechanism field, because a federal statute's mechanism is usually another
  section.
- **Conflict attributes** `resolution_basis` and `confidence`. These are the rubric's own output fields; fss stores
  them on the CONFLICTS_WITH overlay.
- **Force stays a free string** in the schema, because the kit's spec cannot declare an enum (filed). The protocol
  enforces the closed vocabulary instead.
- **Supersedes** is emitted from the manifest (`supersedes:` in `corpus/admission/dispositions.yaml`), never by
  extraction:
  - MSDE's K-12 guidance (2026-10-03) supersedes the June release;
  - the September model policy supersedes the June URL.

  Both older editions are held as metadata only.

## 3. Extraction (`graphs/aacps-policy-dm/extract_protocol.py`, `prompts/extract_v1.md`)

- **Units.** Consecutive blocks of the kit's parsed intermediate, at most `domain.extract.unit_max_chars` (6000), cut
  before a heading once half full. 148 units over 33 texts at the plan (2026-11-01).
- **Items.** `obligation` (text, force, binds, responsible_party_stated, mechanism_stated), `definition` (term,
  text) and `reference` (text, cited_instrument).
- **Grounding.** An item's `text` must be found verbatim in the unit's span of `plain_text`.
  - The match is exact except for whitespace runs, and except for curly versus straight quotes and dashes.
  - Anything else is a row `ungrounded / text_not_in_passage`, kept in the evidence file and never emitted.
  - A force outside the four values is `ungrounded / force_outside_vocabulary`.
- **References.** Each reference resolves through `corpus/admission/citation_aliases.yaml` to a cataloged Work. An
  unmatched one becomes an ExternalReference `ref:<slug>`, so every citation is a keyed node (DI-046).
- **Roles.**
  - The extractor role is seldon registry `extractor` (sonnet, effort medium).
  - The conflict adjudicator role is `adjudicator` (opus). The task names these.
- **Checkpointing** is the kit's: `extract_by_protocol` appends each settled call to
  `evidence/<run>/calls_<doc>.jsonl`, keyed by unit, prompt hash, role and model, so a re-run never re-calls a settled
  unit. Constitution section 15 is met by the kit, not re-implemented here.

## 4. The conflict pass (`scripts/conflict_pass.py`, `prompts/conflict_rubric_v1.md`)

- **Scope (DN-001 anchor 4).** The scope is conflicts between the draft and what it cites or is bound by. Every
  candidate pair therefore has a draft Obligation on one side.
- **Excluded: pairs that do not involve the draft.** Conflicts among the federal regulations are fss-policy-kg's
  subject, not this comment's.
- **Excluded: Definition pairs.** The draft defines nothing (verified from its text), so no Definition pair has a
  draft side. Definitional consistency is answered by the anchor queries (A1, A3) instead: a term the draft uses
  against the Definitions held elsewhere.
- **Candidate pairs, generated mechanically (fss's pairing).**
  1. The forces must be opposed: prohibition against permission (fss class A) or against obligation (class B).
  2. The action texts must share at least `min_shared_terms` content words.
  3. At most `top_k` partners per draft Obligation are kept, ranked by shared terms.

  The pairing is not evidence of conflict; the rubric says so to the adjudicator.
- **Adjudication.** fss's rubric, unchanged in procedure:
  - the same act, addressee and scope gate;
  - then the resolution principles;
  - then `genuine_conflict` naming the actor who cannot comply with both.

  Authority ranks supplied: federal statute 1, federal regulation 2, Maryland statute 3, MSDE guidance 4 (guidance,
  binding only where the Act makes it so), AACPS board policy 5, AACPS administrative regulation 6. Verdicts carry
  `criteria_version: fss-conflict-rubric+aacps-v1`.
- **Into the graph.** The `conflicts` layer of `emit.py` adds a Conflict node and two ConflictsWith edges to the
  draft's entry for every verdict that is not `no_conflict`. A `no_conflict` verdict is a row in
  `evidence/conflicts/verdicts.jsonl`, which is the logged abstention.
- **Checkpointed** per constitution section 15:
  - one JSONL line per pair, keyed by both statement ids, the prompt hash, the role and the model;
  - a re-run skips settled pairs;
  - a pilot of the first `pilot_pairs`, then a projection;
  - call and token ceilings from config;
  - a failure is a row.

## 5. The admission path, and three departures from the kit's defaults (each filed, F-002)

1. **The catalog input is generated.**
   - The hand-written `corpus/candidates/*.yaml` are the acquisition record. Two are bare lists, and their field
     names disagree.
   - `scripts/build_admission_candidates.py` maps them, the Part B receipts and `corpus/admission/dispositions.yaml`
     onto the kit's catalog contract.
   - Every candidate gets a disposition there, including the one merged duplicate.
2. **Substrates are `.txt` (KLUDGE).**
   - The kit's acquire reads a held `kind: work` file as a PDF unless it is `.txt`. So the converted eCFR XML,
     GovInfo HTML, the struck-text-free Ch. 634 and the committee-page snapshot are written `.txt` holding markdown.
   - `.txt` is routed to the kit's markdown reader.
   - Removal is in `corpus/substrate.yaml`.
3. **Ch. 634's struck text is dropped before parse.**
   - The chapter PDF prints amendments struck in passage beside the enacted text, and the text layer keeps both.
   - `strike_pdf` drops every character crossed by a rule in the measured strike band: 1,744 characters, including
     the struck 7-2202(E) Morgan State certification.
   - A test pins the enacted and the struck readings.

## 6. What this note does not decide

- Whether the comment cites a conflict: the operator decides that in Desktop, from the anchor evidence.
- Whether to extract COMAR Title 13A: it is browser-only, and the draft names the title, not a chapter.

## ADDENDUM 01 (2026-11-01, after the run): what the run changed, on its face

Self-executing amendments (doctrine section 3: errata carry their grounding and a diff, no ratification). Each is in
the AP-02 RESULT with its measurement.

1. **Grounding span.** Section 3's span is now the kit's `GroundingSpan` exactly (`start`, `end`, `sha256` of the
   located text, `parsed_sha256` of the whole text). The pilot's commit stage refused the first form
   (`matches_in_unit` inside the span); that count now rides on the row. A test pins it against the generated schema.
2. **The extract control plane.** `extract/control.yaml` declares the index `not_applicable` (every reader reads the
   release export) and the transport's two switches (`setting_sources_disabled`, `nonessential_traffic_disabled`),
   hazbrief's, for its reason (H-005 R-23). The draft's one pilot call ran before the block existed. Its input,
   8,395 tokens, sits beside the model policy's 7,905 per call under the block, so no operator context reached it.
3. **The conflict pass runs inside the kit's spend job** (`squiddy.spend.job_or_inherit`, as the kit's own extraction
   declares one). The first run sent nothing: every call was `SpendRefused (undeclared)`. With no measured history
   the governor cut the job to its 20-unit pilot; the same command continued under the measured estimate.
   Section 4's checkpoint list gains four rules, each pinned by a test:
   - a spend refusal stops the pass and writes no row;
   - a `failed` row is retried up to `run.max_attempts` (3); an `unparseable` answer is settled, not re-bought;
   - a pilot that settles no verdict stops before the rest;
   - `max_billable_tokens` counts cache creation and reads. Input and output alone were 10,019 of the pass's
     373,257 tokens.
4. **Alignment threshold.** `min_jaccard` is 0.2, not 0.3. At 0.3, two of the model's clauses, reworded, went
   unpaired: C.7 (0.25) and C.1 (0.27). It is a display threshold, with every score printed, and it still has no
   measured basis.
5. **Section labels for the draft are derived from its text.** The kit's section path for every draft block is the
   running header (SQ-AP02g), so `anchor_queries.derived_where` computes `B`, `C.1`, `C.2` and so on from the held
   text's headings and clause numbers.
6. **Observed recall limit of `extract_v1`, not corrected in AP-02.** 58 items were refused `text_not_in_passage`;
   31 of them follow one pattern. The model stitches a list's lead-in onto each item, for example "Users may not
   use AACPS technology: ii. ...". Verbatim grounding refuses these correctly, so those list items are absent from
   the graph. A prompt revision would tell the model to quote the item and give the lead-in as a separate field.
   It would be a new instrument (`extract_v2`) and a re-extraction. No anchor rests on a refused item.
