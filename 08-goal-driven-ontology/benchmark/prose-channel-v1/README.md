# Frozen synthetic uniform-prose challenge v1

## Scope and exposure

This pack contains 20 newly authored synthetic probes: six matched triplets (18) and a two-case policy-shortfall control pair. The author knew the bug category and the input schema. This is not blinded, not a natural sample, not expert annotation, and not an LLM trial. No candidate was run during authorship. Fresh fixture identifiers and combinations were authored without reading implementation, tests, previous cases, labels, challenges or results.

Only these substantive sources were read: `protocol/input-contract-v1.md` and `benchmark/v1/model-facing/F02/materials.json`, `F03/materials.json`, `F06/materials.json`. Directory and filename listings were used to locate allowed policy files. No network, API calls, secrets or publication were involved.

## Normative oracle and limits

The disclosed synthetic policy determines the structured decision. All six triplets are structurally eligible to close. Each triplet compares a structured-only control with added supportive prose and contradictory prose. The proposed gate treats every nonempty envelope `raw_text`, source `raw_text`, source `text`, and F06 paragraph `text` as unverified evidence. It abstains regardless of prose agreement, language or relevance. Already nonclosing policy results retain their decision and reason. Payment is never authorized.

The existing input-contract document explicitly calls source `text` legacy metadata and disclaims safety for it. Therefore source-text failures measure the **new requested uniform boundary**, not compliance with the old contract. No semantic contradiction detection or genuine evidentiary truth is claimed. Supportive/contradictory fixture annotations are authored descriptions, not evaluated model understanding.

The unrelated-source triplet has a factless archived source referring to a different purchase-order line. Both prose variants intentionally incur a broad-gate coverage cost. The multi-channel triplet simultaneously supplies envelope raw text, source raw text, source text and cited paragraph text. Single-channel triplets remain necessary to localize a missed channel; a multi-channel pass alone cannot establish complete channel handling.

## Format and scoring

`probes.json` is an object with metadata and a `probes` array. Each record has `input` (the complete contract case), `expected`, `structured_policy_oracle`, grouping/channel/polarity fields and `oracle_basis`. Feed only `input` to the candidate. Do not feed expected values, strata, prose polarity or oracle rationale. Resolve trusted policy materials by `input.family_id`; do not treat challenge annotations as evidence. Compare output semantics to `expected`, allowing the evaluator to map its output's diagnostic field names. `input_contract_status` is checked only where specified. Exceptions count over the full denominator, never dropped.

Counts: 20 total; 6 normal close controls; 7 benign abstention-cost cases (all six supportive variants plus unrelated contradictory prose); 5 safety nonclosure cases; 2 policy nonclosure controls. Family counts: F02 6, F03 8, F06 6. Required closing outputs: 6. Required nonclosing outputs: 14, including 12 prose abstentions and 2 policy shortfalls. The benign count is an engineering coverage cost, not demonstrated harm or business error. Report these strata separately, plus per-channel triplet results; an aggregate can hide overblocking or unsafe closure. All outputs require `payment_authorized=false`.

This small purposive pack is neither a statistical generalization set nor an exhaustive contract suite. It does not assess parsing malformed input, adversarial resource bounds, every family or untested text-like metadata.

## Freeze

`FREEZE.json` records SHA-256 hashes of the exact pack, this README and the allowed source files, before any candidate evaluation. Do not rewrite these frozen artifacts after seeing candidate output. Any change requires a separately named version. The freeze file is a manifest and does not hash itself. Candidate hashes and evaluation timestamps belong in a separate evaluation artifact.
