# Independent AI consistency review of benchmark v1

## Verdict and scope

No decision/reason inconsistency or actual model-export leakage found in the frozen 60-case package. This is an independent AI consistency review, not human adjudication, human gold labels, an experimental model run, or evidence of real-world effectiveness. No source or frozen benchmark files were edited. The data-authoring program was neither read nor executed.

The reviewer read each family policy and all ten case snapshots, then saved 60 manually derived decisions and primary reasons before opening labels. Manifest aggregate decision counts were already visible, so this was not fully blinded. The later label comparison matched all 60 decisions and all 60 primary reasons. Per-case derivations and comparison evidence are in `data-audit-evidence.json`.

## Policy and fact review

- F01: Union coverage, identical-record deduplication, insufficient coverage, wrong-line/pending exclusion, target-count mismatch, lot identity conflicts, and overlap outside the target all agree with the policies and labels. In C10 the shared non-target serial x still triggers overlap.
- F02: Inclusive delegation expiry and maximum rather than summed limits are correctly applied. Empty/wrong-line/expired grants do not prove authority; scoped denial overrides grants. Acceptance-line mismatch and quantity shortfall have the stated outcomes.
- F03: Preliminary or wrong-line rejections are ignored; unknown status does not contradict acceptance. Empty/preliminary-only/pending-only records fail to establish final acceptance. C06's 2 and 3 cannot be added to meet 5; later acceptance does not erase a final rejection in C08.
- F04: Successors remain usable after predecessor revocation; revocation alone removes live acceptance; absent endpoints precede other checks; supersession lowers available quantity in C06 and makes rejection decisive in C07. Cycles, forks, and future-event exclusion agree with labels.
- F05: Receipt date selects the regime. Inclusive boundary, grandfathering deadline, missing receipt, missing/early release, chronology violation, OLD/NEW mismatch, and rejection all follow the prescribed priority. C01's later signature does not disqualify its OLD receipt.
- F06: Exact locator existence, record kind, assertion mode, linkage, negation, and unit checks agree with labels. C04's claimed F06-C04-ATT#s99 is absent despite the source having s01. Shipping and quotation cases do not establish acceptance. C09's negative wording is not treated as positive acceptance.

## Structural and source checks

- 60 distinct cases; family membership agrees across inputs, labels, manifest, and SPLIT.json.
- Development: F01/F02, 20 cases. Validation: F03, 10 cases. Test: F04/F05/F06, 30 cases. No family crosses splits.
- 472 label-basis references resolve to actual sources. Each support string reproduces its referenced policy or observed source text after its descriptive prefix. Required evidence IDs exactly match their label-basis pointer sets.
- The 208 actual source/locator pairs exactly equal the source registry. Structured JSON source text agrees with structured facts. F06 attachment text/facts agree with their catalog entries.
- The deliberate missing pointer F06-C04-ATT#s99 is absent from the actual source pairs and registry. Its label cites the catalog snapshot rather than inventing the missing paragraph.
- All six model-facing files were inspected: policy text, schemas, metadata, and construction task only. They contain no transaction snapshots or case-specific labels. Explicit policy decision rules are intentionally present; this benchmark tests their representation/application, not discovery of undisclosed business rules.

## Freeze and export

Freeze verification passed for 19 files. Manifest SHA256:
`99e026b7cc47a87da948b4eaa82af3808e46dcfaab9af67149f4f800de5767b3`

Read `src/export_model_inputs.py` and exercised the actual package using temporary archives. The archive contains exactly six policy/schema materials plus a public input manifest. No evaluator files, authoring script, case IDs, or transaction snapshots are included. Two exports were byte-identical, SHA256:
`dd7e6a9b29fc8ac1bb76adfddea3f9419d680bed538d32622d4654614be24dc1`

An output destination inside the frozen benchmark was rejected before writing. Source paths receive relative-path/root-containment checks. The recursive forbidden-key check is additional hygiene, not proof against arbitrary information concealed under another key or in prose. The implementation correctly warns that an allowlisted archive is not an OS sandbox: future construction workers must receive only the exported archive, not the repository root. Frozen hashes need independent preservation to establish prospective registration rather than mere internal consistency.

## Limits

The six families and ten designed perturbations each do not cover every policy branch or establish statistical generalization. Exact authored evidence lists are not exhaustive lists of equivalent explanations. AI agreement does not replace independent human/domain review. No benchmark model arms were executed in this review and no performance or superiority conclusion is supported.
