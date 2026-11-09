# Stage 04 code and evidence review

Independent read-only review covered the generic interpreter, F05 artifact, stress probes and their policy citations, plus compatibility-runner semantics. This is software/AI review, not business-expert annotation.

Before case evaluation, review found that malformed Python artifacts containing a lone Unicode surrogate or an integer of 5001 digits could escape the invalid_artifact handler. The strict raw loader also failed to normalize the surrogate exception. The implementation was corrected, four regression methods added, and the unconsumed first freeze superseded before any evaluator cases were opened.

Final independent checks: 39 IR tests passed; malformed artifact regressions return needs_review/invalid_artifact; raw and escaped lone-surrogate JSON raises RuleError; seven final freeze hashes match. An in-memory two-case compatibility exercise checked generation, prediction persistence, then label parsing order and the 1 executed/1 unsupported denominator.

Review also identified duplicate-case/label/prediction ID handling and static denominator wording in the compatibility runner. These were corrected before execution; six runner tests passed in the coordinator environment.

Stress results were independently reproduced: 22/22 in-policy, 4/8 OOD fail-closed, 8/8 metamorphic relations, matching saved results. No clear false in-policy oracle was found. OOD expectations are proposed engineering safety boundaries, not implied exact policy labels. Stress authoring and review inspected the existing baseline, so the probes are not blind.

Historical stress freeze did not include the runner/scoring implementation. It remains unchanged. The publication manifest captures the final runner and tests as current hashes, not a retrospective pre-execution claim.

Reviewer did not read original evaluator cases/labels or execute the real compatibility dataset. Full-suite and retrospective evaluation were separate coordinator operations. No remaining blocker was found within this review scope; this does not certify security, business safety or A/B readiness.
