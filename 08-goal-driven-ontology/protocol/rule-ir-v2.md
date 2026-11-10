# Rule IR v2: bounded typed collections

Engineering extension, manually authored from policy and existing baseline, not a model arm or blinded induction. Reference scope is F01 and F05 only. F02/F03/F04/F06 remain unsupported. Nothing here establishes six-family coverage, business accuracy, semantic provenance entailment, or A/B readiness. No evaluator inputs, labels or stage-04 stress probes were read during implementation. Stage-04 files remain unchanged.

## API and compatibility

`src/rule_ir_v2.py` exposes strict `loads(text)`, `validate(program, available_refs=None)`, `evaluate(program, facts, available_refs=None)`, and explicit-artifact `predict_case(case, artifact, materials)`. Version must equal `rule-ir-v2`. The v1 file is neither modified nor imported at runtime. F05 is the v1 reference with only its version changed. Scalar operators, rule ordering, conservative first-UNKNOWN stopping, audit trace, and transport merge semantics are retained. No family dispatch, dynamic code, imports from artifact data, eval, network, or filesystem operations occur in the interpreter.

## Types

Scalar types remain boolean, integer, string, date, without coercion. A type can also be `{kind: array, items: TYPE}`, `{kind: set, items: SCALAR}`, or `{kind: record, fields: {NAME: TYPE}}`. Set element types are string, integer, or date. Sets are encoded as distinct JSON arrays; duplicate members are malformed rather than silently removed. Runtime normalization sorts declared set fields. Arrays preserve order. Record fields are typed and required for a known record. Extra keys are retained unmodified, including in identity comparisons; they are not accessible via typed item expressions. No scalar comparison between records or collections is accepted.

A missing/null scalar, collection, record or declared record member yields UNKNOWN. Any unknown member makes its containing collection/record UNKNOWN, not a partially usable collection. All members are validated before this propagation; a malformed sibling cannot hide behind a missing member. Entire accessed collections are validated eagerly, even records later filtered out. Declared root fields remain lazy by visited rule. Other input values receive whole-JSON bounds validation but are not semantic scope checks.

## New operators

- `item` with literal `key`: read a declared record property within a filter predicate. No ambient item outside a record filter.
- `filter` with `arg` array and `where` boolean expression: evaluate all rows, retaining true rows. Any unknown predicate makes the entire result UNKNOWN. Nested filter predicates bind the innermost item; no named variables or outer-item capture.
- `count` with `arg` array or set: return its length.
- `intersects` and `subset` with same-typed set `left` and `right`: nonempty intersection and left-set inclusion respectively.
- `identity_conflict` with record-array `arg` and string-field `key`: detect repeated identity values whose complete normalized payload differs.
- `distinct_by` with the same arguments: collapse identical repeated identities, preserving first identity order. Conflicting payloads raise an input error instead of silently choosing one. JSON object key order and declared set order are immaterial; other payload array ordering and extra keys remain material. JSON integer/float representations in extra payloads remain distinguishable.
- `union` with record-array `arg` and set-field `key`: sorted distinct set of that field across records.
- `overlap` with the same arguments: true if any two records share a set member. Callers needing identity-level overlap must explicitly use `distinct_by` first.

These are generic typed operators, not F01 calls. A generic integer-set test also exercises the language without family material. There are no reusable named expressions, joins, arithmetic aggregation, maxima, graph traversal, source-content interpretation, ontology reasoning, or general quantifiers. Repeated AST subexpressions execute repeatedly and count against the budget.

## F01 reference and intentional limits

F01 explicitly checks request completeness, count mismatch, invalid lot status, identity conflicts, cross-identity overlap, coverage, then closure. It filters by line, accepted status and target intersection. Coverage unions accepted serial sets rather than summing quantities. Full participating payload identity is preserved, including extra supplied fields. Additional serials and overlap outside target serials follow policy p04/p05.

Eager validation differs from the historical baseline for incomplete/malformed irrelevant or nonparticipating records: v2 can return UNKNOWN or malformed_input where baseline would ignore that data. Missing collection members produce generic condition_unknown; exact missingness reason agreement is not claimed. The reference's missing-request rule precedes numbered policy checks. The status validation rule is an explicit structural guard. This is not a language-level validation of business scope (services, credits, units, multiple invoice lines, authenticated acceptance, and snapshot completeness are assumptions). F05 carries its existing scope assumptions unchanged. An always-true closure rule remains structurally possible; type validation is not policy correctness.

## Budgets and fail-closed behavior

Whole program and input: 128 KiB serialized UTF-8, 8192 JSON values, nesting depth 32. Type nesting: at most depth 4, up to 32 declared fields per record. Every source array/set is bounded to 128 items at every level; derived union is also at most 128 distinct members. Root fields/rules: 64 each; literal path length: 8. Expression nodes: 512 across all rules; expression depth: 24; boolean operands and refs: 32. Execution: 4096 charged steps (each expression, record scanned by aggregation, and set member merged). Filtering charges predicate evaluation for every row. Fixed array/JSON bounds additionally bound normalization, canonical identity comparison and set operations; not every Python primitive or byte is individually step-charged. No unbounded user loop or graph recursion is available.

Unknown blocks fallthrough to later closure; malformed evaluated input, exhausted budgets, or dedup conflicts return needs_review/malformed_input. Invalid artifacts return needs_review/invalid_artifact. Python API type/key/cycle/Unicode/huge-integer failures fail closed as well. Duplicate JSON keys and non-finite numbers are rejected by the loader. Payment authorization is always false. Source locator existence checks do not establish semantic support. Transport includes supplied fact refs as an inventory, not a minimal proof.

## Reproduction and freeze

Run from topic root:

    PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p test_rule_ir_v2.py -v

The suite includes the existing v1 scalar probes exercised against v2 and newly authored collection/safety probes. These are implementation-authored tests, not held-out evidence. `ontology/ir-reference-v2/read-manifest.json` records actual source reads. `freeze.json` hashes the v2 implementation, tests, protocol, references, and read manifest before independent retrospective evaluation. Freeze also hashes the unchanged v1 test dependency. No test or reference reads evaluation cases or labels. Any later amendment requires a new freeze and must be described as post-evaluation if evaluation has already occurred.
