# Stage 05 independent review

2026-11-10. Read-only review of frozen implementation and first-run results, with a separate post-freeze adversarial probe. No frozen code, tests, challenge, or first-run outputs were edited. Review is bounded, not a security certification. The recorded test logs report 228 passing tests and a 25-file byte-identical repeat; this reviewer did not independently rerun those checks.

## Findings

### HIGH: invalid artifact can return close_eligible

`src/rule_ir_v2.py:177–182` uses runtime `_value` to validate enum members. Null returns the UNKNOWN sentinel; `_validate` then returns it successfully before checking rules, defaults, source references, or remaining fields. `evaluate` at lines 298–301 ignores the return value and proceeds. An artifact with integer field `x`, `enum: [null]`, empty rules, and default `close_eligible`/`bypass`/empty source refs therefore closes on `{}`. This violates the explicit default-no-close, mandatory-source-ref and invalid-artifact-fails-closed contracts.

Independent execution confirmed the bypass even with an empty available-reference set. Minimal artifact, input, actual output and implementation SHA-256 are in `adversarial-artifact.json`; executable reproduction is `adversarial-artifact-probe.py` (run with Python in this workspace). Its assertions establish the observed failure, not desired safety. This post-freeze discovery is separate from benchmark scores. It blocks executing untrusted model-generated artifacts with this interpreter. Payment remains unauthorized, so it is an unsafe eligibility recommendation, not an actual payment execution. Existing valid hand-authored reference scores are not invalidated by the distinct failure, but cannot establish interpreter safety. The broad fail-closed statement in `protocol/rule-ir-v2.md` is contradicted by this evidence and must be qualified in publication. Repair only in a separately versioned future implementation, with null/unknown enum rejection and explicit validated-success checking.

### HIGH for unverified ingestion: source-envelope prose bypass remains

`src/input_contract.py:287–289` checks case/source `raw_text` and F06 paragraph `text`, but not ordinary source-envelope `text`, although that field is accepted by the schema. The frozen E22 challenge changes source-envelope text without changing structured facts. `first-run/gated_baseline.challenge.report.json` records E22 still closing, while `prose_verified` remains false. This is not evidence of text comprehension or safe source reconciliation. Preserve it as the remaining adverse-input failure. E09 is the converse cost: a valid control is conservatively blocked. Strict rejection of unknown fields is structural abstention, not semantic contradiction detection. Known nullable/missing fields and lazy IR root-field evaluation likewise do not establish completeness of evidence ingestion.

### Scope limitation: coverage and provenance

IR v2 has hand-authored references only for F01/F05. The runner explicitly excludes F02/F03/F04/F06; absence of those executions is unsupported coverage, not safe abstention or correct predictions. Locator existence checks and fact-ref inventories do not prove that statements support an outcome, that sources are genuine, or that structured extraction matches prose. The input gate wraps a trusted predictor and trusted materials; it does not validate arbitrary predictor code or fix the enum-null artifact defect.

## Accounting and comparison

Inspection of `src/run_stage05.py`, `tests/test_stage05_runner.py`, the frozen challenge contract and `first-run/summary.json` found the reported counts consistent with the stated design:

- Gated baseline legacy: 57/60 decision and reason matches, 17/20 positive closure recall, 0/40 negative unsafe closures. Ungated baseline: 60/60 and 20/20. This is a regression/abstention tradeoff, not an accuracy gain.
- Gated baseline old stress: 22/22 exact policy decisions and 8/8 adverse-input nonclosures. These known regression inputs are not unseen validation.
- Gated baseline new challenge: 9/10 exact close controls, 8/9 adverse-input nonclosures, 4/5 benign abstentions. The last number is a coverage cost, not a success rate. E22 is the adverse failure; E09 is the control failure.
- Each IR configuration: 20/20 legacy matches in F01/F05 only, with 40/60 cases unsupported. Stress executes 11/30 and leaves 19 unsupported; challenge executes 8/24 and leaves 16 unsupported. The gated IR challenge's 4/4 controls and 2/2 adverse cases cannot be compared directly to the baseline's six-family denominators.
- The runner preserves exceptions as failed executions and reports unsupported counts; probe exceptions do not count as safe nonclosure. Payment flags are separately counted. Existing recorded executions show no exceptions and all payment flags false. None of this proves real payment-system isolation.

One defensive accounting limitation: `summarize_labels` rejects duplicate IDs but does not itself require all planned cases to be present. The current runner constructs the selected list explicitly and records counts, so no demonstrated missing-case error exists in these first-run results. Future external-model runners must reconcile predictions against an explicit planned manifest rather than rely on this helper alone.

The fair-comparison protocol appropriately distinguishes four engineering configurations from model arms. Shared input gating does not make hand-authored IR versus baseline a model experiment. Legacy materials were available during development; challenge authors knew prior failure categories; local freeze hashes are integrity checks rather than external preregistration. The 24 probes/12 pairs are dependent synthetic examples without expert gold. No significance or population-risk estimate is justified.

## Publication recommendation

Publish as a bounded, zero-model-call, zero-paid-call retrospective engineering audit with a prospective local synthetic challenge and an explicit post-freeze safety failure. Report control retention, adverse nonclosure, benign abstention, exception counts and unsupported coverage separately. Preserve first-run failures and the adversarial artifact unchanged.

Allowed claim: the specific shared gate improved adverse-input nonclosure on these fixtures while reducing closure coverage, and hand-authored F01/F05 references reproduce 20 selected legacy decisions. Not allowed: six-family IR support, safe execution of untrusted generated artifacts, general input safety, semantic provenance verification, expert business validity, goal-driven-model superiority, or readiness for a real model A/B study. Publication of transparent research is reasonable; deployment and untrusted-artifact execution are not supported.
