You are adjudicating whether two provisions are in deontic conflict. One is from a DRAFT school-district board policy
(Anne Arundel County Public Schools Policy DM, Responsible Use of Artificial Intelligence). The other is from a federal,
Maryland or district document the draft cites or is bound by. Apply the criteria below exactly. Return only JSON.

(Instrument: fss-policy-kg kg/conflict_rubric.md, adopted with the domain sentence and the authority ranks changed;
criteria version {criteria_version}.)

=== WHAT YOU ARE READING ===

Each candidate is a pair of extracted provisions from two different instruments, with their deontic forces. They were
paired because their forces are opposed and their action texts share words. The pairing is mechanical. It is not
evidence of conflict.

=== THE CENTRAL FACT ABOUT THIS DOMAIN ===

In a legal corpus most force-opposed pairs are NOT conflicts. Shared vocabulary is not shared subject matter. Two
provisions can both say "student" and "data" and govern entirely different acts. Most candidates you see are
`no_conflict`, and saying so is the correct and expected answer, not a failure to find something.

Of the pairs that do oppose, most are resolved by ordinary legal principles. A genuine unresolved conflict is rare and
is a strong claim. Do not manufacture one.

=== DECISION PROCEDURE (apply in order; stop at the first that decides) ===

STEP 1 — SAME ACT?
Do the two provisions govern the same conduct? Not the same topic, the same ACT.
If they govern different acts, return `no_conflict`.

STEP 2 — OVERLAPPING ADDRESSEE?
Could one actor be bound by both provisions at the same time? If no single actor could be subject to both, return
`no_conflict`.

STEP 3 — OVERLAPPING SCOPE AND CONDITION?
Do the triggering conditions co-occur? If the conditions cannot co-occur, return `no_conflict`.

Steps 1 to 3 are a gate. A pair failing any of them is `no_conflict` no matter how strongly the forces appear to
oppose.

STEP 4 — DOES A RESOLUTION PRINCIPLE APPLY?
If the provisions do oppose, test these in order and return `apparent_resolved` with the first `resolution_basis`
that applies:

  `exception_clause` — One provision explicitly carves out the other, by text visible in the spans.
  `specificity` — One provision is a narrower case of the other (lex specialis).
  `hierarchy` — The instruments sit at different authority ranks (below; rank 1 is highest). The higher governs.
      CAUTION: a lower instrument implementing a discretion the higher one grants is NOT a hierarchy conflict. It is
      `no_conflict`.
  `temporality` — Both in force and their effective dates order them. Only when the dates are supplied and differ.

STEP 5 — OTHERWISE
If the provisions oppose, the addressee and scope overlap, and no resolution principle applies, return
`genuine_conflict`. The rationale MUST name the actor who cannot comply with both.

Authority ranks: 1 federal statute; 2 federal regulation; 3 Maryland statute; 4 Maryland State Department of Education
guidance (guidance, binding on a local school system only where Maryland law requires alignment with it); 5 AACPS
board policy (the draft is a board policy); 6 AACPS administrative regulation.

=== CONFABULATION GUARD (binding) ===

Reason ONLY from the text supplied in the two spans and the metadata given. Do not rely on provisions, definitions,
exceptions, or authorities that are not present in what you are shown. Never quote text that does not appear verbatim
in the supplied spans.

=== THE PAIR ===

A (rank {rank_a}, {doc_a}, force {force_a}, binds {binds_a}):
{text_a}

B (rank {rank_b}, {doc_b}, force {force_b}, binds {binds_b}):
{text_b}

=== VOCABULARY (exact strings; any other value is invalid) ===

verdict:           `no_conflict` | `apparent_resolved` | `genuine_conflict`
resolution_basis:  `specificity` | `temporality` | `hierarchy` | `exception_clause` | null
                   Non-null if and ONLY if verdict is `apparent_resolved`.
confidence:        a number from 0.0 to 1.0.
rationale:         1 to 3 sentences.

=== OUTPUT ===

Return ONLY this JSON object, with the four keys in exactly this order. No prose before or after. No code fence.

{"verdict": "...", "resolution_basis": null, "confidence": 0.0, "rationale": "..."}
