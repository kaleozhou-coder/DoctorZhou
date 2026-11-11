# Stage-06 report fact and methodology review

Reviewed `report.zh.md`, `first-run/summary.json`, both new protocol documents, the frozen prose-pack README/manifest, the fair-comparison plan, runner/scorer code, reproduction manifest, and independent probe evidence. No numerical correction was found in the report's stated tables or coverage counts.

Verified directly:

- The report's baseline/gate v1/gate v2 counts match the saved summaries, including 0/20 legacy positive recall, 0/10 old challenge normal-close retention, and new-probe strata 6/6 normal closure, 5/5 safety nonclosure, 7/7 benign abstention, and 2/2 policy-shortfall preservation.
- All 20 new probes are F02/F03/F06. IR v2, IR v3 and gated IR v3 execute zero of them and record all 20 as unsupported. The report correctly avoids attributing baseline-gate results to IR coverage.
- All listed implementation-freeze hashes match current files. F01/F05 v2 and v3 reference artifacts differ only in version; saved old-suite v2/v3 prediction objects are identical.
- All 49 stage-06 first-run JSON files and 25 stage-05 first-run JSON files match their corresponding actual `/tmp/ontology-stage06-repeat-20261111` and `/tmp/ontology-stage05-repeat-20261111` files byte-for-byte and match reproduction-manifest hashes. The saved final suite log reports 338 tests, OK. This review did not independently rerun the entire 338-test suite.
- The restored pre-review source snapshot SHA256 equals the original review output's `a9afa89125f0ff5c5c018f459300a48401b218e4509b256f3220e52d946314f7`. It is correctly described as restored from the diff, not a contemporaneously saved source file. The original failing runtime JSON and assertion-failure log remain separate from the repaired results.
- After-probe rerun semantic sections in `/tmp/ontology-reviewer-after-repeat-20261111.json` equal the archived after-probe JSON, including hashes, runtime probes, mutations, contract probes and legacy/fixed exploit outputs.

## Reproduction correction verified

The earlier report command would overwrite archived reviewer results. This was corrected in reproduction plumbing only: `reviewer-probe-after.py` now writes no result file by default; optional `--output` opens its destination exclusively with mode `x`. I ran `PYTHONDONTWRITEBYTECODE=1 python -B results/stage-06/reviewer-probe-after.py`: exit 0, 27 artifact mutations / 7 runtime / 7 contract probes passed, both suites exited 0, and the archived after-probe JSON SHA256 remained unchanged. No probe expectations or frozen implementation changed for this correction.

## Methodology caveat disclosed

The pack README specifies optional expected contract status, but `run_stage06.adapt_prose` drops `input_contract_status`, and the shared scorer evaluates safety as nonclosure rather than exact reason/status. Current report counts are correctly described as nonclosure/cost and do not require correction. The report now explicitly discloses that the runner does not score the complete oracle metadata; exact status/path coverage is supplied by engineering tests, not these aggregate probe scores. This resolves the identified disclosure gap without changing frozen results. Do not change the frozen pack or retroactively relabel results to resolve this disclosure gap.

## Limits and interpretation

The report and fair-comparison plan appropriately separate engineering repair, policy correctness, conservative abstention and future model generation. They do not claim semantic contradiction understanding, independent business sampling, model A/B outcomes, production safety, or measured labor savings. Matched probes are not independent observations. Authorship isolation and zero external calls are documented provenance assertions; this local review cannot independently reconstruct all historical reads or prove absence of every external action. The remote-base verification JSON records 229 matching blobs, but this reviewer made no fresh remote request. Freeze timestamps are local records, not external preregistration. Preserved failures and hash parity support the narrow reproducibility claims, not an authenticity or safety certification.
