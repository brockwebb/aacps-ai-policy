You are extracting the normative content of one passage of a public policy or legal document. Return only JSON.

=== THE DOCUMENT ===

Document: {doc_title}
Kind: {doc_type}
Section: {section_path}

=== WHAT TO EXTRACT ===

Three item types, and nothing else.

1. `obligation`: a sentence (or a self-contained clause of an enumerated list, with its lead-in) by which the document
   requires, forbids, allows or recommends that someone do something. Classify its deontic force with exactly one of:
   - `obligation`: the party must act ("shall", "must", "is required to", "will ensure", "is responsible for").
   - `prohibition`: the party must not act ("shall not", "may not", "must not", "is prohibited", "only ... may").
   - `permission`: the party is allowed but not required to act ("may", "is authorized to", "is permitted").
   - `recommendation`: the party is encouraged ("should", "is encouraged to", "consider", "best practice").
   A modal verb is not enough. "AI may create risks", "data may differ", "this guidance may be updated" describe or
   predict; they bind no one, so they are NOT items. Return nothing for a passage that only describes. Questions a
   guidance document poses for the reader ("Who coordinates AI implementation?") are not obligations.
2. `definition`: the document states what a term means ("X means ...", "X refers to ...", "X: ..." in a definitions
   list, "In this subtitle, X has the meaning stated in ..."). Give the term and the defining sentence.
3. `reference`: the document cites another instrument by name or citation (a statute, regulation, policy, regulation
   code, guidance document, standard): "34 CFR Part 99", "Policy DI", "Section 4-131 of the Education Article",
   "the Maryland K-12 Artificial Intelligence Guidance". One item per instrument named in the passage.

=== THE TEXT FIELD IS A QUOTATION ===

`text` must be copied VERBATIM from the passage: the exact characters, in order, with the same words, punctuation and
capitalisation. Do not paraphrase, shorten with "...", fix typos, expand abbreviations, or join text that is not
adjacent. Line breaks may be written as single spaces. An item whose `text` is not in the passage is discarded.
For an obligation, quote the whole sentence or clause that carries the force. For a reference, quote the citation as
written (a few words).

=== FIELDS (exact key names; any other key is ignored) ===

obligation:  {"type": "obligation", "text": "...", "force": "obligation|prohibition|permission|recommendation",
              "binds": "the party the text names as bound, in its words, or null if it names none",
              "responsible_party_stated": true or false,
              "mechanism_stated": "a verbatim phrase naming the process, deadline, approver or consequence the text
                                   attaches, or null if it attaches none"}
definition:  {"type": "definition", "term": "...", "text": "..."}
reference:   {"type": "reference", "text": "...", "cited_instrument": "the instrument's usual short name or citation"}

`responsible_party_stated` is true only when the sentence (or the passage's lead-in it depends on) names who must
act. "AI tools shall be vetted before adoption" names no one: false. "The Superintendent shall establish procedures":
true. Passive voice with no agent is false.

=== OUTPUT ===

Return ONLY this JSON object. No prose before or after. No code fence.

{"items": [ ... ]}

An empty list, {"items": []}, is the correct answer for a passage with no obligation, definition or reference.

=== THE PASSAGE ===

{unit_text}
