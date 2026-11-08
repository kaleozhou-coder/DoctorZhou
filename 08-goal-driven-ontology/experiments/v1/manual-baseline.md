# Manually programmed policy baseline

This independently implemented, AI-assisted coding artifact is a standard-library Python 3.10+ implementation of the six supplied **invented** policies. It is a hand-coded structured-fact baseline, not ontology discovery, a learned system, or a natural-language interpreter. No novelty, model-performance, human-gold, real-transaction, or payment-approval claims are made. No human study was conducted. Self-authored test success is not benchmark performance.

## Interface and execution

Import `predict_case` from `src/policy_baseline.py` and call `predict_case(case, materials)`. `materials` is the **single parsed policy JSON object** for `case.family_id`, not a mapping of families. The case has the assigned envelope: `case_id`, `family_id`, `split`, `policy_source_id`, `question`, and `sources` containing `source_id`, `locator`, `text`, and a `facts` dictionary. Pass the supplied policy without modification. The manually coded rules are fixed to these six policy versions, not synthesized from material text at runtime.

Facts are merged at the top level. Repeat occurrences of a top-level field must have identical canonical JSON values; contradictory duplicates produce `needs_review / conflicting_facts`. Nested dictionaries are not merged; arrays are not concatenated. Thus splitting a single request object or a ledger array between sources is unsupported. Unknown top-level facts are ignored by decisions, but contradictory duplicate fields are still rejected. JSON object key ordering is immaterial; repeated array-valued top-level fields must agree in array ordering as well as content. Record order *inside a single snapshot* does not affect valid policy decisions.

`case_id` is passed through. `family_id` selects manually written code. `split` and `question` never select a decision. Source text is not parsed; explicit structured facts are authoritative under the synthetic policies. The baseline does not detect text/fact disagreements or authenticate sources. These would require a separate ingestion/verification layer.

The result always has `case_id`, `decision`, `evidence_ids`, `reason_codes`, `source_refs`, and `payment_authorized: false`. Valid supported cases receive exactly one first-decisive policy reason, or `criteria_met`. A `close_eligible` recommendation **never authorizes payment**.

Run only the self-authored checks:

```
python -m unittest discover -s tests -v
```

## Policy mechanisms

- F01: target cardinality; participating lot identity consistency; pairwise overlap including non-target serials; set coverage. Nonintersecting, pending, and other-line lots do not participate. Serial order is normalized for identity comparisons.
- F02: acceptance line; date/line/signer-scoped denial; scoped grant existence; largest grant limit; quantity coverage. Inclusive date boundaries, never summed grant limits.
- F03: relevant final acceptance/rejection contradiction; rejection; missing acceptance; maximum cumulative accepted quantity. Relevant conflicting payloads under one report ID are structural input conflicts.
- F04: as-of filtering; endpoint existence; directed cycle before fork; retirement/revocation; surviving rejection/missing acceptance; maximum cumulative quantity. Iterative topological cycle detection avoids recursion limits. Duplicate edges have no additional effect. Revocation neither restores predecessors nor propagates to successors.
- F05: receipt missing; chronology; rejection; receipt-selected OLD/NEW evidence rules; quantity. Inclusive regime and grandfather boundaries; no inference from invoice/review dates.
- F06: exact catalog pointer; source kind and assertion mode; explicit linkage; literal acceptance status; detail/unit/role checks in their stated order; quantity. No neighboring-paragraph rescue or lexical search for “accepted.”

## Scope and fail-safe behavior

The policies assume synthetic positive-quantity EA goods, one invoice line, and authenticated inputs with complete available snapshots. The baseline accepts JSON-shaped Python values only. Relevant quantities must be nonnegative integers (invoice quantities and F02 acceptance quantities strictly positive), not booleans or floats. Dates used in decisions must be exact `YYYY-MM-DD` ISO dates. Required identifiers must be nonempty strings. Missing fields that have a policy-defined meaning follow that policy (for example F06 absent linkage or F05 absent release).

Otherwise, absent required decision inputs return `needs_evidence / input_missing`; invalid types, domains, or date formats return `needs_review / malformed_input`; conflicting repeated facts/identities return `needs_review / conflicting_facts`; unsupported family, mismatched policy identity, or F04 wrong-line records return `needs_review / unsupported_case`. These four input-handling reasons are implementation extensions, not policy paragraph rules. Out-of-scope services, returns, conversion, and payment are not implemented. No approval should be inferred for external uses of the API.

This is a partial validator, not a full schema validator. F04 event identifiers are required but repeated event IDs are not globally reconciled; edge semantics govern the result. F03 relevant repeated report IDs are checked for conflicting full payloads, but ignored reports are not reconciled. Pointer components containing `#` are not escaped in `evidence_ids`, so that convenience encoding can be ambiguous; use the separate fields in `source_refs` as the authoritative pair.

Validation is lazy along the ordered decision path. A decisive earlier policy check can return without inspecting downstream fields. Irrelevant records and unused descriptive fields are not exhaustively validated. This is deliberate: e.g. future ledger records/events have no effect, and F03 timestamps cannot establish last-write-wins. Missing whole snapshots are input gaps, while supplied empty snapshots take their explicit policy paths. Exact duplicates of F04 record IDs are tolerated idempotently; contradictory active record payloads are input conflicts. Exact F06 pointer duplicates are likewise idempotent; contradictory cited payloads are conflicts. F01 serial arrays must contain distinct strings as specified by its schema.

## Audit trace, not proven support

`source_refs` is a sorted, deduplicated list of supplied policy-paragraph and factual-envelope source/locator pairs. `evidence_ids` is the corresponding `source_id#locator` list. These are a conservative **audit trace**, including irrelevant supplied facts, an inventory trace, not decision-specific semantic grounding, a minimal proof, or an assertion that every paragraph supports the result. Catalog entries are inspected as structured facts carried by their envelope source; the code never manufactures an envelope source for a nested catalog record. On malformed input, only valid references collected before the input error are returned. The code does not invent missing locators or resolve citations externally.

## Isolation and provenance

Implementation and tests were written using only `materials/F01.json` through `materials/F06.json`, the assignment, and general environment instructions. No evaluator transactions, labels, author scripts, source registries outside those policy schemas, prior interpreters, or other repositories were read. `READ_MANIFEST.json` records explicit task-content reads and material checksums. On integration, `materials/F01.json` maps to `benchmark/v1/model-facing/F01/materials.json`, and equivalently for F02–F06. Python and shell used standard runtime libraries; those are execution dependencies, not research inputs. Tests are newly authored examples derived from the six policies, including first-check precedence, boundaries, reordering, duplicate invariance where supported, irrelevant facts, stable output identifiers, input nonmutation, and fail-safe handling.

Freeze implementation, tests, documentation, and manifest before opening evaluator inputs. Any future evaluation belongs to a separate phase and must distinguish manual baseline results from model results and expert-verified evidence.
