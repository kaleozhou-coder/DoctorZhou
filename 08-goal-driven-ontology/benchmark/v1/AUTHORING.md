# Prospective synthetic ontology benchmark v1

This package freezes invented materials for future model construction and evaluation. It is not a completed experiment, customer corpus, real transaction record, human gold standard, or evidence of comparative performance.

## Provenance and authoring boundary

One AI data author created six policy/document families and all sixty case inputs and labels. The only pre-existing project document read for scope was `protocol/research-design.zh.md`. The author did not inspect project implementation, reference models, existing cases, earlier data, or model outputs. No customer materials, downloads, external calls, model runs, decision-engine runs, or human annotation were used. This is role separation from implementation, not independent human annotation. Policy and cases were co-designed prospectively, and label errors remain possible.

`SPLIT.json` was physically written before the case authoring script. The fixed, purposive assignment is F01/F02 development, F03 validation, and F04/F05/F06 test. There was no random sampling and no seed. All ten cases in a family stay together. Cases are dependent perturbations within family, not sixty independent real-world samples. The six families use distinct decision mechanisms: serial-set overlap, line/date/quantity delegation, negative final-status precedence, directed version-event graphs, receipt-date regime selection with grandfathering, and semantic support of exact pointers.

## Files and access boundary

- `model-facing/F01/materials.json` through `F06/materials.json`: invented policy paragraphs and document schemas only. The complete six-family policy pool may be supplied equally to all experimental arms. Test families mean held-out transaction combinations under distinct policies, not unseen policies when their materials are supplied. Do not claim unseen-policy transfer in that setup.
- `evaluator/inputs/F01.json` through `F06.json`: evaluator-only future transaction cases. Do not show these during ontology construction. Each file has `family_id`, `split`, and `cases`.
- `evaluator/source-registry.json`: `{sources:[{source_id,locators:[...]}]}` derived from the actual stored policy and case paragraphs, never from pointer claims or labels. This supports locator-existence checks only, not semantic support measurement.
- `evaluator/labels.json`: evaluator-only labels, exact sufficient source basis, primary reason and rationale. Root `cases` contains one label for each case, with no duplicate or omitted IDs.
- `evaluator/prediction.schema.json`: exact output shape for a future case-query evaluation. It contains all case IDs and is therefore not an ontology-builder input. The harness may provide the shape without the enum at inference time.
- `manifest.json`: exact one-to-one case/family/split/file assignment, family-level decision counts, status and limitations. It is evaluator metadata, not a model-facing source file.
- `author_benchmark.py`: deterministic source of all generated artifacts and labels. This is evaluator-sensitive, not model-facing and not an experimental model-generation program.
- `FILE_SHA256.json`: relative-path-to-SHA256 object covering every package file except itself, including this document, the fixed split and the authoring script. Self-exclusion avoids recursive hashing.

Export only the six explicit `families[].model_materials` files from the manifest to the future ontology builder, not the package root or the authoring script. If the study intentionally gives development cases as feedback, log that exception and give identical information to each arm. Keep validation/test inputs and all their labels hidden during model construction and tuning. A later frozen-model query step necessarily sees its own case input but not the label. This package itself performs none of those steps.

## Input and source schema

A case has `case_id`, `family_id`, `split`, `synthetic`, `policy_source_id`, `question`, and `sources`. Each source paragraph has `source_id`, `locator`, `text`, and `facts`; F06 attachment paragraphs also carry `source_kind`. IDs are stable within this frozen version. Policy paragraphs are stored in `policy_paragraphs`, with `source_id`, `locator`, and natural-language `text`.

The main case document uses locators p01, p02, etc. Its paragraph `text` is a canonical JSON statement of its explicit facts, not a hidden label. `facts` supplies the identical statement as structured data. Source snapshots are complete only for the explicitly stated available records, not an assumption that missing real-world facts are false. Policy text specifies whether absence means an evidence gap, records may be ignored, or an adverse fact requires review.

F06's catalog is a complete locator inventory; its pointer may deliberately name a nonexistent paragraph. Existing attachment paragraphs are also emitted as first-class source entries. This duplication is a representation of the same paragraph, not independent corroboration. Catalog evidence proves what is available; the actual attachment paragraph supports its semantics. A nonexistent pointer never appears in a required evidence list. Headers or adjacent paragraphs do not silently satisfy missing case linkage.

Every case includes the full fact snapshot needed for its authored decision, and policy paragraphs specify all precedence needed by the cases. Acceptance/authority authentication is a synthetic premise where the policy says so, not an external factual verification. All identity and date values are invented.

## Label and prediction schema

Labels root: `{benchmark_id, label_schema_version, cases:[...]}`. Each case label has:

- `case_id`, `family_id`, `split` matching manifest and input exactly.
- `expected_decision`: exactly `close_eligible`, `needs_evidence`, or `needs_review`.
- `required_evidence_ids`: unique strings formatted `source_id#locator`. Every required pointer resolves either to that family's policy or that case's sources. These are an exact, sufficient authored basis, sometimes deliberately including the full precedence chain, not a claim of minimality or the only logically valid proof.
- `required_reason_codes`: exactly one primary code, chosen by the policy's first-decisive-check precedence.
- `label_basis`: objects `{source_id, locator, support}` in the same order as the evidence IDs. The support quotes the normative clause or observed synthetic facts, so policy-only reasoning never substitutes for case evidence.
- `payment_authorized`: always false.
- `author_rationale` and `label_provenance`: evaluator-only explanation and limitations.

Future prediction shape: `{case_id, decision, evidence_ids, reason_codes, payment_authorized}` with no extra fields. Exact decision and primary reason comparison is possible. An evidence coverage score can test required-ID inclusion; separate locator validity must reject fabricated pointers. Exact source-basis matching is a strict benchmark-contract measure and must not be described as a general semantic entailment test. A genuinely supported alternative proof may not match the authored basis; adjudicate such alternatives separately without silently changing this freeze. Do not infer ontology structural correctness from lexical matching of class or property names.

No future experimental outcome is included. An all-abstain or all-review policy is not success: report eligible-case recall, false-close numerators/denominators and all three decision classes. Report family counts and case dependence. Six families cannot support a strong cluster-level generalization claim. Actual human review time remains unmeasured.

## Reproduction and integrity

Use Python 3 standard library only. From this directory run:

    python3 author_benchmark.py

The script reads the pre-existing fixed `SPLIT.json`, writes materials, inputs, labels, manifest and prediction schema, then computes `FILE_SHA256.json`. It contains explicit authored labels and performs only structural assertions (counts, IDs, class presence, pointer existence). It does not derive labels by executing an implementation or call any model. Reproduction overwrites the generated artifacts in this directory; preserve the original hash manifest before reproducing if auditing integrity.

To verify without regenerating, compute SHA256 over the bytes of every listed relative path and compare with its listed digest; also ensure there are no additional files other than `FILE_SHA256.json`. The manifest deliberately cannot authenticate itself; preserve its digest outside the package for a tamper-evident audit. Any later corrections require a new version and a documented diff, not silent replacement after results are observed.
