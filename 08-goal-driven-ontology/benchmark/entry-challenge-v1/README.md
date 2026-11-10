# Stage 05 prospective entry challenge v1

This self-authored synthetic engineering challenge has 24 complete cases in 12 paired comparisons. It is newly authored outside the implementation and frozen before predictor execution. It is **not** an independent hidden holdout, expert gold, real-transaction evaluation, language-model experiment, or evidence of generalization. Several challenge categories intentionally revisit stage04 findings; E02/E12 and benign annotations add different concrete payloads, not proof of novel semantic coverage.

## Author's read boundary

The author read all six `benchmark/v1/model-facing/F*/materials.json` files, the entire `benchmark/stress-v1/README.md`, and the first 12,000 bytes of `benchmark/stress-v1/probes.json`. The stage04 README disclosed previous outcomes and failure categories. The author did not read any implementation, unit tests, evaluator cases/labels, `src/input_contract.py`, or `rule_ir_v2`, and did not run any predictor. The pack therefore has policy and prior failure-category knowledge, not implementation blindness to all prior research. Directory listing of the six policy families was also performed. No publication or external transmission was performed.

## Prospective scoring contracts

- **10 in_policy controls:** require exact `expected.decision` and `expected.reason`. All ten deliberately remain close-eligible under the stated structured assumptions. They test whether a conservative entry gate leaves valid closure reachable. This subset is not a balanced estimate of business accuracy.
- **9 ood_safety cases:** require a nonclosure response (`needs_evidence` or `needs_review`), with no imposed primary business reason. These inputs are malformed, contradict policy-domain assumptions, have conflicting event identity, or contain incompatible evidence channels. Do not relabel them as exact business rejections. Exceptions are failures, not safe abstention.
- **5 unsupported_benign cases:** no business decision label is assigned. Report close-eligible, conservative abstention, unexpected output, and exceptions as separate counts. Benign here means the author deliberately added irrelevant metadata or consistent text; it does not establish that arbitrary unknown fields are safe. Abstention on these cases is an operational coverage cost, not a false business label.
- **Every case:** payment must remain unauthorized. Report this invariant separately, with all 24 cases in the denominator. Do not omit exceptions or malformed cases.

`pairs` names the single evidence change and its intended interpretation. Every member includes its own complete case facts, source envelope, source citation(s), and rationale. No runner may repair inputs, mutate expected labels, or silently coerce malformed values. Shared controls and the repeated adverse-status case create dependence; neither 24 cases nor 12 pairs should be treated as independent samples. Report the three scope denominators separately rather than a pooled accuracy.

## What entry validation can and cannot show

A new input gate can reject unknown fields without understanding their text. P07 and P10 deliberately compare consistent and contradictory values in the same unsupported field. Rejecting both satisfies the adverse-input nonclosure boundary but incurs benign abstention; it does not demonstrate semantic contradiction detection. P05 changes a supported cited paragraph's text and P11 changes source-envelope text while preserving structured facts. Their nonclosure requirements are prospective engineering safety expectations, not proof that the existing schemas specify a complete natural-language interpreter.

Event-ID collision handling is likewise an added safety expectation where F04 does not provide collision-resolution rules. Extra wrong-line acceptance in F05 contradicts a stated target-line premise. Source-envelope inconsistency in F03 is a proposed ingestion safety boundary rather than an invented F03 reason code. No unknown or missing value is labeled as rejection merely for being unknown.

## Freeze and later execution

`FREEZE.json` hashes this README, probes, and the six policy sources, and records the pre-run state. It intentionally does not hash the implementation because this author has not inspected it. Local hashes and timestamp are edit-detection aids, not independent notarization. A runner should verify the frozen files before execution, record its own implementation/version hash separately, and write outputs outside this directory. Any correction to the pack after freeze requires a new version and explicit disclosure; do not quietly repair these labels after observing predictions.

This pack's author makes no outcome claim. Later execution should compare exact-control retention, adverse-input nonclosure, benign abstention, errors, and payment safety separately. The concrete probes test small designed engineering boundaries only.
