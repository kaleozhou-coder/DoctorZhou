# Synthetic stress probes v1 (stage 04)

This is a **self-authored engineering stress pack, not a hidden test, expert gold, LLM experiment, or estimate of business accuracy**. The author inspected the six model-facing policy documents, the frozen baseline implementation, its unit tests and the project README. The author did not open v1 evaluator labels or cases. Familiarity with the implementation means these probes are not blind evaluation. Some semantic patterns deliberately overlap unit tests; the pack extends combinations and boundary checks, not a claim that every pattern was previously untested.

## Prospective oracle and freeze

`probes.json` contains 30 explicit inputs with policy paragraph citations and oracle reasoning. It was written with all expected outcomes before any stress execution. `FREEZE.json` records its SHA256 plus the baseline and six policy files. The runner verifies these hashes before executing. The baseline was not modified. This local content hash guards later edits but is not an independent timestamp/notarization or evidence of a blinded study.

- **22 in-policy** probes: exact three-state recommendation AND primary reason, grounded in numbered policy checks; payment authorization must remain false.
- **8 OOD safety** probes: deliberately violate documented schemas/preconditions or introduce an unspecified identity inconsistency. Their oracle is a proposed engineering boundary: do not close or authorize payment. Either evidence-needed or review is accepted, with no invented policy reason code. These are **not** labeled as in-policy errors and must not be pooled with policy accuracy.
- **8 metamorphic relationships**: deterministic paired comparisons covering future denial, unknown versus rejection, as-of date changes, revocation asymmetry, endpoint priority, and irrelevant records. These reuse probe cases and are not eight independent additional transactions.

The exact input/oracle file SHA256 at freeze was `43305f985b01fb0c8871b7fa710ef0e685e658ae4d9b4bed40977a6eecaaa832`.

## Reproduce

From the topic directory, Python 3.10+ standard library only:

```
python src/run_stress_probes.py --output /tmp/ontology-stress-fresh
python -B -m unittest discover -s tests -p test_stress_probes.py -v
```

The output directory must be absent or empty. `results/stage-04/stress/` contains the first-run outputs. The runner never opens evaluator files and catches prediction exceptions as failures with the full denominator. The tests verify pack integrity, deterministic reproduction, control sensitivity, exception accounting and payment safety; green regression tests do **not** mean the known OOD safety failures disappeared.

## Actual frozen-baseline result

- In-policy: **22/22** exact decision and primary reason; no observed policy correctness failure.
- OOD safety: **4/8** nonclosure; four close-eligible outputs violate the proposed safety boundary.
- Metamorphic: **8/8** paired relationships.
- Exceptions: **0/30**. Payment authorization: false throughout.

The OOD failures are:

1. **S25, F02:** Extra `acceptance.status=rejected` is ignored. F02 p02 assumes exactly one positive uncontested acceptance; the adverse field violates that premise.
2. **S26, F04:** Two different transitions share an `event_id`; event identity collisions are not checked. F04 specifies event identifiers but does not specify collision resolution. This is an added structural safety requirement, not a contradicted numbered rule.
3. **S27, F05:** Extra `acceptance.po_line=OTHER` is ignored. F05 p03 assumes the single acceptance maps to the target line; explicit contrary mapping is outside that domain.
4. **S29, F06:** Structured acceptance fields disagree with rejection prose; only structured fields are evaluated. F06 p02 explicitly assumes agreement. This reveals an ingestion-consistency boundary, not an in-policy natural-language understanding result.

Malformed boolean quantity, repeated target identifiers and conflicting record identity do fail closed; integer `released=1` also fails closed rather than being coerced to true. A rejection recommendation is not the only acceptable OOD response, and neither missing evidence nor unknown is silently recast as rejection in these oracles.

A separately reported deliberately unsafe always-close control achieves **8/22** in-policy, **0/8** OOD safety and **3/8** metamorphic. It still emits payment_authorized=false so the control isolates closure errors, not payment authority. This is a test-sensitivity control, not an alternative model or useful comparator for AI performance.

## Boundaries and next step

These results do not support a claim of genuine generalization, production readiness, or an ontology/LLM advantage. A useful next implementation would validate declared policy-domain assumptions before applying the family rule, and route incompatible evidence for review. It should be tested on a newly frozen pack rather than retroactively repairing these labels. Actual linguistic extraction, provenance entailment, model-generated ontology evaluation, expert review, and real transactions remain untested.
