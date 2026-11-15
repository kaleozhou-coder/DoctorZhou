# Reusable prompt record

These are the substantive instructions used, normalized to relative file paths for reuse, not a byte-for-byte conversation export. All workers were spawned without inherited conversation history. Only designated input files and the worker's own output were authorized. No gold, other-arm, repository, web or API reads were allowed. Reading an own generated JSON to validate it was allowed. The coordinator did not send gold-dependent feedback.

## Common extraction contract

All six cases are independent. Use the business question and supplied documents to extract a minimal sufficient set of reviewable ontology/policy propositions. Preserve evidence IDs, scope, negation, ambiguity and active contradictions; do not invent rules or resolve undefined roles. Every candidate must have status `proposed`, even if certain: no human has reviewed it. Output JSON list of `{case_id,facts:[{subject,relation,value,sources:[D1 or D2],status:'proposed'}]}`. Use readable snake_case strings; ordinary natural-language values are allowed. Cover answers to the business question, not irrelevant facts. Do not execute business decisions.

## One-shot

Read only `data/stage-10/materials.json`. In one pass, perform the common extraction task using all documents. Save `results/stage-10/arm_one.json` once; do not revise after saving. Report path and files read.

## Fixed question-driven batch

Pass 1: read only `data/stage-10/batch1.json`. Perform common extraction; identify what evidence is missing and which question it blocks. Include a `next_question` string for each case. Save `arm_batch_pass1.json`.

Pass 2: read only `data/stage-10/batch2.json` plus own `arm_batch_pass1.json`. Treat new D2 as the second evidence batch; revise using business questions and both batches retained in context. Resolve only explicit replacements; preserve unresolved conflicts/unknowns; retain provenance D1/D2. Save final `arm_batch.json` without `next_question`. No further revision after saving.

## Strong full-material iterative

Pass 1: read only `data/stage-10/materials.json`. Perform common extraction and save `arm_strong_pass1.json`.

Pass 2: read only same materials plus own first pass. Self-review each business question for missed relevant concepts, negations, replacements, unknowns, active contradictions and accurate D1/D2 provenance. Correct mistakes and remove unnecessary propositions. Self-review is not human review; status remains proposed. Save `arm_strong.json` once.

## Identity-masked grader

Read only `data/stage-10/materials.json`, `data/stage-10/gold.json`, `results/stage-10/review/masked.json`. Do not read reveal, named arm files, code, protocol, history or other agents. For each anonymous output and each gold target, score semantic coverage and strict source completeness separately. Synonyms/merged facts are allowed, raw quotes count when they assert the target; two conflicting quotes do not count as explicitly identifying unresolved conflict. An omitted value is not an explicit unknown. Source completeness requires matching supporting output facts to collectively cite all gold-required IDs. Additional facts may be valid; identify unsupported assertions and dangerous overclaims separately. Proposed status does not excuse unsupported content. Save exactly 23 targets per candidate, with `case_id`, zero-based `gold_index`, `covered`, `source_complete`, and `reason`. Save unsupported and dangerous-overclaim lists plus a short limitations review. Do not revise after identity reveal. This grader is AI, not human or expert gold standard.
