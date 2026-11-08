# Policy-baseline code review

Date: 2026-11-08. AI-assisted independent code review, not a human or domain-expert study.

Review inputs were the six policy-only materials, baseline implementation/documentation, runner, and existing scorer. The reviewer did not inspect evaluator cases, labels, registry, old outputs, or prior policy implementation.

No blocking rule-order mismatch was found for valid, in-scope inputs. Additional self-authored checks covered F01 overlap outside the target, F04 no predecessor restoration, F04 nonpropagating revocation, and F05 the inclusive grandfathering boundary. These are engineering checks, not additional held-out transactions.

Before freeze, review findings led to the following changes:

- Require implementation, runner, scorer, tests, and all six policies in the implementation manifest; reject path traversal.
- Bind the executed benchmark manifest hash to the implementation freeze.
- Reject nonempty result directories to preserve first-run outputs.
- Distinguish pre-run hash-only label-byte access from post-prediction label parsing.
- Validate reason-label list shape and retain every labeled case in reason-audit rows.
- Check conflicting payloads for relevant F03 report IDs.
- Document partial input validation and inventory citations rather than semantic proof.

Remaining limits: no full external-input validator, no reconciliation of every F04 event identity, ambiguous convenience encoding for pointer components containing `#`, and no decision-specific semantic-support proof. The benchmark's valid-input domain avoids relying on those unsupported behaviors.

No evaluation-driven code patch was made after the implementation freeze.
