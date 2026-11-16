# Stage 11 isolated AI pre-extraction freeze review

Review date: 2026-11-16. Reviewer: isolated AI worker, not a human/domain expert. Only materials.json, questions.json, contract.md, gold.json, and protocol.md were read. No extraction outputs or other arms were inspected. No input files were edited.

## Verdict

All 28 proposed **answer labels are accepted**, conditional on evaluating these snapshots under the current revision-4/CR-17 policy. No answer correction is required. Resolve the applicability ambiguity and citation issue below before final freeze; the proposed neutral wording revisions are also recommended if the intended challenge is not to explicitly cue conflict and UNKNOWN handling. This review does not confer human ground truth or real-world validity.

## Pre-freeze issues and proposed corrections

1. **Historical applicability:** D2.4 makes revision 4 govern *new records* from 2032-04-01. D3.3 dates evaluation snapshots, not record creation. Although current-policy intent is strong, evaluation after an effective date does not alone settle historical policy applicability. Add to D3.3 after its first sentence: `All cases in these snapshots were created on or after 2032-05-01.` This removes the residual ambiguity for Q05 and the case decisions without changing labels.
2. **Q01 gold source completeness:** D1.2 establishes necessity and says it does not assert joint sufficiency; that alone is not proof of non-sufficiency. Retain D1.2 and add D1.3 (the exclusive authorized routes impose further conditions), or D1.4 (a hold defeats closure despite reconciliation). Proposed sources: `["D1.2", "D1.3"]`. Label remains NECESSARY_ONLY.
3. **Question-vocabulary mismatch:** Q06 and Q07 are phrased as yes/no questions but contract permits DEFINED/UNKNOWN. The intended missing-definition answer is unambiguous under the contract, but this is a syntax-driven task rather than natural yes/no interpretation. Prefer Q06: `Is the authoritative mapping from settlement_flag Y to cleared settlement defined in this packet?` and Q07: `Is an authoritative mapping from paid_at to receipt_date or posting_date defined in this packet?` Keep their DEFINED/UNKNOWN vocabularies. UNKNOWN here is missing mapping, not permission to infer a negative settlement fact.
4. **Answer cueing:** The material often directly tells the solver the desired inference or failure mode. This is fair if all arms see it, but weakens claims about discovering unresolved definitions or resolving plausible conflicts unaided. In particular D2.2 says `intentionally not supplied` and prohibits Y/N inference; D2.3 explicitly instructs retaining uncertainty. D3.1 explains both alternatives twice, D3.3 labels the training note `plausible operational noise`, and D4.4 explicitly names the preservation targets. Contract and D4.2 legitimately define task semantics, but their assistance must be acknowledged. Longer prose alone is not greater retrieval difficulty.

### Minimal neutral replacements proposed, not applied

Replace D2.2 in full with:

> receipt_date records the date funds reached the collection bank. posting_date records the date the ledger entry was posted. The dictionary contains no settlement-clearance date field. Sample exports contain settlement_flag values Y, N, and blank; the export codebook is not included in this packet. Settlement-clearance attestations are maintained separately and may state cleared settlement directly.

Replace D2.3 in full with:

> Several screenshots display an optional dashboard column paid_at. Its metadata entry contains the column name but no definition, timezone, event basis, or mapping to registry fields. Local analytical worksheets use the column with different conventions.

These replacements retain the authoritative-definition gaps and separate attestation route, but stop narrating the correct UNKNOWN response. The D4.2/3 evidence rules still determine how gaps affect decisions. Do not eliminate the gap itself: mere silence without a scope/metadata description can make questions less fair rather than harder.

Optional neutral D3.3 replacement after adding the applicability fix:

> All evaluation snapshots in the attached sample packet are on 2032-05-02. All cases in these snapshots were created on or after 2032-05-01. An operator training note prepared before CR-17 states that an audit is mandatory for every exception. The controlled policy register contains no later entry.

D3's controlled-register title and effective date, D1.3, and D3.1 then supply the conflict resolution without labeling distractor prose as noise. If any wording changes are accepted, final freeze should follow a recheck of the changed source text. Do not describe this existing report as approval of unseen revisions.

## Per-label acceptance

`R` = reconciled; `H` = valid handover; `S` = cleared settlement; `W` = waiver; `A` = audit; `I` = independent inspection; `hold` = active hold. Current routine route: R AND H AND S AND NOT hold. Current exception route: R AND H AND W AND (A OR I) AND NOT hold. Missing attestations are unknown, not false. A false mandatory condition defeats every applicable route; a true hold independently blocks closure.

| ID | Proposed label | Review | Basis |
|---|---|---|---|
| Q01 | NECESSARY_ONLY | Accept; supplement citation | D1.2 requires R; exclusive routes in D1.3 require additional conditions. |
| Q02 | NOT_SUFFICIENT | Accept | D1.3 exclusive routes require more than R and H; D1.4 hold overrides them. |
| Q03 | ROUTINE_ONLY | Accept | D1.5 explicitly restricts S necessity to routine; exception route lacks S. |
| Q04 | WAIVER_AND_EITHER_AUDIT_OR_INSPECTION | Accept | D3.1 replaces A with alternative I, retaining W and D1.3 common prerequisites. Inclusive OR, not both required. |
| Q05 | NO | Accept subject to applicability clarification | D2.1 receiving-lead definition and D2.4 supersession defeat driver-only legacy card for current records. |
| Q06 | UNKNOWN | Accept | D2.2 lacks authoritative Y mapping; this is a definition-gap label, not a false clearance. |
| Q07 | UNKNOWN | Accept | D2.3 lacks authoritative paid_at mapping. |
| Q08 | NO | Accept | D4.1 arithmetic contribution alone does not establish cause. |
| Q09 | NO | Accept | D1.5 explicitly says closure is neither sufficient nor necessary for payment authorization; payment outcome itself remains unspecified. |
| Q10 | NO | Accept | D3.1 expressly preserves W. |
| Q11 | NO | Accept | D2.2 distinguishes receipt and posting events. |
| Q12 | NO | Accept | D1.4 hold prohibits closure despite full positive route. |
| C01 | ALLOW | Accept | Routine R/H/S true, hold false. |
| C02 | UNKNOWN | Accept | S null; raw Y cannot resolve it; routine cannot borrow exception route. |
| C03 | ALLOW | Accept | Exception R/H/W/I true, hold false; A false and S false do not defeat inspection route. |
| C04 | ALLOW | Accept | Exception R/H/W/A true, hold false; I false irrelevant. |
| C05 | BLOCKED | Accept | W false defeats both exception alternatives. |
| C06 | BLOCKED | Accept | hold true overrides complete routine route. |
| C07 | UNKNOWN | Accept | hold null prevents establishing hold-free route; no affirmative prohibition established. |
| C08 | UNKNOWN | Accept | A false and I null leave alternative unresolved. |
| C09 | BLOCKED | Accept | A and I both false defeat every exception alternative. |
| C10 | BLOCKED | Accept | H explicitly false; driver signature cannot replace current H. |
| C11 | UNKNOWN | Accept | S null; receipt/posting dates do not attest clearance. |
| C12 | BLOCKED | Accept | R false defeats all closure routes. |
| C13 | ALLOW | Accept | I true establishes alternative despite A null. |
| C14 | ALLOW | Accept | A true establishes alternative despite I null. |
| C15 | BLOCKED | Accept | Routine necessary S false. |
| C16 | UNKNOWN | Accept | H null; other positives neither establish H nor prove it false. |

Counts: 12/12 fact labels accepted, 16/16 decision labels accepted; decisions include 5 ALLOW, 6 BLOCKED, 5 UNKNOWN. No duplicates or omissions in gold. The direct attestation convention prevents demands for missing raw signatures. No assumption of closed-world falsity is needed.

## Fairness and scope

The same final materials, questions, and answer vocabulary across arms support within-run comparison. Fixed two-document batches are not autonomous retrieval. All positive routes, vetoes, alternative logic, supersession, and missing mappings are present in the packet. Sixteen synthetic snapshots in one domain do not support superiority, general ontology quality, or human/expert validity. The protocol correctly discloses unmatched compute, unknown model version/seed, unmeasured cost/time, and author-known labels. First-batch answers that lack later documents should be assessed as intermediate, not as equally informed final conclusions. A second-pass arm has extra inference opportunity, so any differences are workflow observations, not a controlled efficiency claim.

## Final revision recheck and freeze acceptance

After the coordinator applied revisions, the reviewer reread D2 and D3 in full, the revised Q06/Q07, and Q01 gold sources. The original caveats and proposed wording above remain as an audit trail, not as descriptions of the final text.

- Q01 now cites D1.2 and D1.3: source-completeness issue resolved.
- Q06/Q07 now ask whether an authoritative mapping is defined in the supplied packet: vocabulary issue resolved.
- D3.3 explicitly states all cases were created on 2032-05-02 under current policy: applicability ambiguity resolved.
- D2.2 now references absent SI-9, with distinct bank/ledger event definitions and a separate attestation route. D2.3 supplies blank semantic metadata and missing migration/definition documents. Both retain the same UNKNOWN labels without explicit instructions naming that answer.
- D3.3 dates the non-authoritative training note before CR-17 and removes its explicit characterization as operational noise.

**Final decision: ACCEPT FOR FREEZE before extraction. All 28 labels remain accepted; no unresolved blocking label/fairness defect was identified.** Residual explicit guidance in D3.1, D3.2, D4, and the answer contract still makes this a bounded policy classification challenge rather than unaided discovery. No claim that all conflict/UNKNOWN cues have been eliminated is warranted. The review is independent isolated AI review only, with zero human approvals.

Reviewed final artifact SHA-256 hashes (to identify this acceptance scope):

- `data/stage-11/materials.json`: `89ac898f96c3ae9eb672016e3567596f92bb9a105bd7190497987992d4f808d0`
- `data/stage-11/questions.json`: `6edbc65a78c1d9f7c33cff9a0ab9ed55a8d208a703f96e6726896aeca60e605a`
- `data/stage-11/contract.md`: `66b52e020057cf6b7fae5aeca3791f190034e12a0fecf250a05e2ccd3161ae4f`
- `data/stage-11/gold.json`: `eaafc0c807313c27b183e786fc99b80e9cb8f729fe4bd797b20ac8c62329d106`
- `experiments/stage-11/protocol.md`: `f1e9a5d6c7ae06d3508ace89a686cbe629bb526011995d04a0554c8f0532ec65`
