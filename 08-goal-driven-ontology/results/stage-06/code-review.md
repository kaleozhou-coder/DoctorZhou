# Independent adversarial review: Rule IR v3 and input contract v2

## Confirmed issue before reviewer fix

**Runtime null masks an otherwise invalid duplicate set, allowing closure.** In the reviewed `rule_ir_v3.py`, `_value` returns `UNKNOWN` if any collection member is unknown before checking duplicate set membership (lines 133–136). A structurally valid condition `any(true, count(field(s)) == 1)` produces:

- `s = [1, 1]`: `needs_review`, `malformed_input`.
- `s = [null, 1, 1]`: `close_eligible`; the condition trace is `true`.
- The same occurs with null in either remaining position.
- `s = [null, 1, "bad"]`: `needs_review`, `malformed_input`, so scalar type validation remains eager.

The `true` operand deliberately makes UNKNOWN masking observable. Unconditional closure is allowed by this IR and is not itself the finding. The defect is the change from malformed duplicate input to non-error UNKNOWN when null is added, despite both boolean operands being evaluated. It is a runtime boundary failure, not recurrence of the artifact enum early-return bug. `payment_authorized` remains false throughout. Recommended repair: validate duplicate **known** set members before propagating UNKNOWN; preserve UNKNOWN for null with unique known members.

## Confirmed repairs and negative findings

The old enum-null exploit still reproduces in v2 and returns closure. v3 refuses it before traversing rules. Independently authored probes reject 27 malformed artifact variations, including empty/wrong-shaped program sections, nested incomplete enums, normalized duplicate set enums, bad typed members, default closure, and integer-as-boolean literals. No remaining artifact-validation bypass was found in this limited review.

For `input_contract_v2.py`, independent probes cover simultaneous envelope/source/uncited-paragraph prose, null in three prose levels, duplicate JSON question keys, duplicate source identity with changed text, and empty prose. Malformed cases block before invoking the trusted predictor. Simultaneous prose records all five paths and downgrades closure. Empty strings remain allowed as documented. These results support the narrow declared prose-channel boundary, not natural-language agreement, authenticity, or policy entailment.

## Commands and evidence

Working directory: `/workspace/shared/doctorzhou-research-20261111/08-goal-driven-ontology`.

Executed: `PYTHONDONTWRITEBYTECODE=1 python results/stage-06/reviewer-probe.py`.

Result: 27 artifact mutation probes, 7 runtime probes, 7 input-contract probes, all expected assertions satisfied. The script also ran:

- `python -m unittest discover -s tests -p test_rule_ir_v3.py -v`: 93 tests, OK.
- `python -m unittest discover -s tests -p test_input_contract_v2.py -v`: 13 tests, OK.

Full outputs and hashes are preserved in `reviewer-probe.json`; the independent executable probe is `reviewer-probe.py`.

Pre-fix SHA256:

- `src/rule_ir_v3.py`: `a9afa89125f0ff5c5c018f459300a48401b218e4509b256f3220e52d946314f7`.
- `src/input_contract_v2.py`: `5eeb51571b670880644ae31ed748539d04fc775c525c70e2f6f7604c1f1a93f8`.

## Limits

This is synthetic engineering testing, not independent business or model-evaluation samples. The v3 evaluator does not eagerly validate all declared fact fields: unused fields and later rules can remain unexamined after an earlier match. Valid unconditional closure and deliberate three-valued boolean semantics remain policy-author choices. Missing records can collapse a collection to UNKNOWN before semantic identity analysis; absence of detected identity conflict is not evidence of identity consistency. Source-locator existence is not entailment or authenticity. Identifier/category strings are not treated as prose channels by the opt-in contract. The contract wraps a trusted predictor, whose exceptions deliberately propagate. No implementation was modified by the reviewer. No external/network calls, secrets, or publication were used. A data-only AST without code-loading/eval operators does not establish production safety, tamper resistance, or a complete resource-isolation guarantee.

## After-fix independent verification

The implementation owner repaired duplicate-known-member validation before UNKNOWN propagation. The unchanged pre-fix probe was rerun and failed its expected-closure assertion, exit code 1, recorded in `reviewer-probe-after-test.log`. The pre-fix script and JSON remain unchanged.

An explicitly adapted reproducible script, `reviewer-probe-after.py`, changes that assertion to require `malformed_input` for all three null positions, checks that true OR UNKNOWN with `[null]` still closes intentionally, and writes a distinct `reviewer-probe-after.json`.

Executed: `PYTHONDONTWRITEBYTECODE=1 python results/stage-06/reviewer-probe-after.py`.

Result: 27 artifact mutations, 7 runtime probes, and 7 contract probes passed their expectations. `[1,1]` and all permutations of `[null,1,1]` now return `needs_review` / `malformed_input`. Both engineering test suites remain green. This closes the demonstrated duplicate-set masking defect; it does not change or condemn the intentional true OR UNKNOWN semantics.

After-fix hashes:

- `src/rule_ir_v3.py`: `f73b417c46478b284e816eec5eee519dd024700c29064ffb18d991733cf9f495`.
- `src/input_contract_v2.py`: `5eeb51571b670880644ae31ed748539d04fc775c525c70e2f6f7604c1f1a93f8`.

Suite totals after fix:

- test_suite: Ran 94 tests in 0.058s; OK
- contract_suite: Ran 13 tests in 0.058s; OK



## Safe reproduction entry point

The after-fix probe now accepts optional `--output PATH` using exclusive file creation.
Without that option it writes no result file and prints a summary, preserving archived
evidence. A new temporary-output run reproduced all sha256/runtime/mutations/contract/
legacy_exploit/fixed_exploit sections exactly; unittest timing text is not deterministic.
The original pre-fix script remains historical evidence, not the current reproduction
entry point.
