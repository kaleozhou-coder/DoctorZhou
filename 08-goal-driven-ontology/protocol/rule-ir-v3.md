# Rule IR v3: complete artifact validation

Versioned repair of the stage-05 structural validation bypass. The v1 and v2
implementations and their failures remain unmodified. This is engineering work,
not model output or a production security certification.

The API and resource limits are those of [v2](rule-ir-v2.md), except that the
required program version is `rule-ir-v3` and the following validation rules change:

1. An enum must contain complete typed values. Null at the root or in a declared
   nested record/collection, and missing declared record members, raise RuleError.
   UNKNOWN is a runtime fact value, never successful artifact validation.
2. All fields, rules, sources and default outcomes must be checked. Enum errors
   cannot return early and bypass the remainder of the program.
3. evaluate requires a validation dictionary whose valid entry is exactly True.
   Unknown, missing, false or merely truthy values never authorize execution.
4. Enum members are normalized by their declared types. Duplicate normalized
   members are rejected; set order does not affect enum membership. Canonical
   JSON comparisons avoid Python equality coercion in nested extra payloads.

A second adversarial-review fix validates duplicate known set members before
propagating UNKNOWN. Thus [null, 1, 1] is malformed rather than UNKNOWN; unique
known members plus null retain the documented three-valued semantics.

Runtime missing/null facts still propagate UNKNOWN under the old three-valued
rules. The F01 and F05 reference programs are exact v2 copies apart from the
version field. They remain manually authored, with the same restricted coverage.

Tests replay all 80 v2 scalar/collection checks and add 14 adversarial methods,
including the original exploit, nested null/missing values, later invalid
structure, invalid defaults, absent refs, and simulated failed validation returns.
Test methods contain subcases and are not independent business samples.

Structural validity is not business correctness. An always-true closure rule
can be valid; a model can omit required business checks while producing a valid
AST. Source locator existence does not establish entailment or source identity.
Only the known structural bypass is repaired. Model artifacts require separate
policy validation and isolated evaluation, and may not be used for real actions.

Development exposure: prior implementation, tests, reference programs, stage-05
failure report and historical summaries. This is a regression repair, not a
blinded generalization experiment. No paid model call, credential or network is
needed to run the interpreter or tests.

Run from the topic directory:

    python -B -m unittest discover -s tests -p test_rule_ir_v3.py -v
