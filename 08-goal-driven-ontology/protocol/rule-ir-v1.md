# Rule IR v1: bounded shared executable representation

Status: engineering reference, not a model-produced artifact or a six-family A/B readiness claim. Both arms can emit the same JSON representation and use the same validator/interpreter. No model has been run here. Reference F05 was authored from model-facing policy and prior baseline source, before any case-level evaluation. This is not independent blind policy induction.

## API and scope

`src/rule_ir.py` uses Python standard library only. `loads(text)` parses strict bounded JSON; `validate(program, available_refs=None)` checks structure and static types; `evaluate(program, facts, available_refs=None)` returns an outcome and ordered trace. `predict_case(case, artifact, materials)` is a transport adapter matching the existing prediction schema. The caller supplies an artifact explicitly. No runtime family dispatch, dynamic import, arbitrary Python, `eval`, plugins, shell or network operations exist.

Only scalar fields in nested objects are supported. Types: boolean, integer (not boolean, absolute value <= 2^53-1), nonempty string, canonical Gregorian ISO date (`YYYY-MM-DD`). Field declarations may constrain integer minimum and enum. There is no coercion. Paths are arrays of literal object keys, not attribute access or executable queries. Extra facts are ignored except for the whole-input JSON size/depth bound. Undeclared facts do not establish that an artifact covers an unsupported task.

Reference `ontology/ir-reference/F05.json` implements the synthetic receipt-date regime policy. F01, F02, F03, F04 and F06 are explicitly unsupported by reference artifacts. In particular there is no array quantification, identity/deduplication, conflict-aware set union, authority registry aggregation, supersession graph traversal, source-content interpretation or ontology inference. Future expansion requires a new version and independent checks. Do not execute the F05 artifact on another policy and call the result coverage.

## Semantics

Expressions are `field`, typed `literal`, `eq`, `ne`, `lt`, `le`, `gt`, `ge`, `not`, `all`, `any`, and `is_unknown`. Equality requires matching types. Ordered comparisons allow only integer/date operands. Dates compare lexicographically only after canonical validation. Null and missing path components represent UNKNOWN, not false. A non-object parent, wrong type, invalid enum or range is malformed input. `is_unknown` is the only explicit missingness test; it never hides malformed values.

Kleene truth tables: false dominates `all`; true dominates `any`; otherwise any unknown propagates, and `not unknown` is unknown. All operands are evaluated, so malformed facts in a boolean branch are not hidden. Field validation is lazy by visited rule, not a claim of validating every input field. Optional malformed release/transition data can therefore be rejected more strictly than the historical family-specific baseline even when an enclosing branch is false. That deliberate conservative behavior is outside claims of exact baseline equivalence.

Rules are evaluated in list order. First true returns its decision/reason. First UNKNOWN immediately returns `needs_evidence / condition_unknown`; it never falls through to a later close or adverse rule. False advances. Default may only be `needs_evidence` or `needs_review`; closure requires an explicit true rule. A syntactically valid always-true close rule is still possible: structural validation cannot certify policy correctness. Malformed artifact yields `needs_review / invalid_artifact`; malformed evaluated input yields `needs_review / malformed_input`. Payment authorization is always false. The outcomes are recommendations only.

Boundaries: 128 KiB per program/input, 8192 JSON values, JSON nesting 32, 64 fields/rules, path length 8, 512 AST expression nodes, expression depth 24, 32 operands/references, 4096 execution steps. No loops or recursion in the language. Host traversal is bounded. Duplicate JSON keys and non-finite numbers are rejected by `loads`; callers should not replace it with a permissive JSON loader. Python objects are independently checked for cycles/depth and non-JSON data.

## Provenance and transport

Each rule and default needs nonempty `{source_id, locator}` refs. With `available_refs`, validation checks exact membership in the supplied locator set. Without it the check is structural only. Neither establishes semantic support, source authenticity, completeness or entailment. Core output refs identify the terminal rule only; its trace lists all visited rule IDs and true/false/unknown states. These are not proofs.

The transport adapter checks the policy-source ID against supplied material and merges input source fact dictionaries without concatenating arrays or merging nested objects. Identical top-level values may repeat; different JSON representations for the same top-level key are conflicts and return `invalid_transport`. It emits all supplied fact-source refs plus terminal policy-rule refs as an audit inventory, not a minimal proof. It does not inspect policy prose or select a program by family. Its output does not include the richer core trace; call `evaluate` separately when retaining traces.

## Validation and experimental boundary

The adjacent JSON Schema is a structural interchange aid. The normative validator additionally checks static expression types, enum/minimum consistency, bounds, duplicate rule IDs and supplied source locator existence. Schema acceptance alone is insufficient. The reference, tests, implementation and protocol are hashed in `ontology/ir-reference/freeze.json` before retrospective evaluation by a separate worker. `scope-read-manifest.json` records actual material reads. Tests are implementation-authored engineering probes, not held-out generalization evidence. No original benchmark files or prior stage files are changed.

Run only the new checks with:

    PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p test_rule_ir.py -v

A/B model execution remains gated on broader policy coverage (or an explicitly narrowed protocol), backend/model authorization, equal resources and leakage controls. This implementation does not resolve those gates.
