# Structured input contract v1 (stage 05)

This is a separate opt-in safety gate, not a modification to the historical
baseline or Rule IR. It is self-authored engineering code for synthetic inputs,
not expert-validated procurement policy or a natural-language extractor.

## Public API and execution order

`src/input_contract.py` exports:

- `loads_case(raw: str | bytes)`: decode strict UTF-8 JSON and enforce generic
  resource/type bounds. Raises `ContractError(code, path)`; does not validate the
  family schema until `validate_case` is called.
- `validate_case(case: dict)`: validate every supplied source/fact eagerly,
  merge identical top-level fact values without deep merging, validate required
  merged fields and safety constraints, and return merged facts. No mutation.
- `apply_contract(case, materials, predictor)`: accept a dict or raw JSON, run
  the gate, then call the trusted `predictor(case, materials)` only if validation
  succeeds. Preserve its fields, add `input_contract`, and force
  `payment_authorized=false`. Invalid input returns a nonclosing prediction.
- `predict_case(case, materials)`: convenience wrapper around the unchanged
  `policy_baseline.predict_case`.

The caller supplies trusted policy materials and a trusted callable. This gate
is not a sandbox for malicious predictors or policy metadata. Predictor errors
are not swallowed: the evaluator must count exceptions over the full denominator.
The gate does not read files, labels, network resources or execute input code.

`input_contract.status` is `blocked`, `validated` or `abstained`. Blocked output
includes the deterministic first diagnostic `code` and structural `path`, and
empty citation arrays because a valid trace has not been established. Missing
required input produces `needs_evidence`; invalid type, unknown field or an
unsafe combination produces `needs_review`. These are contract diagnostics,
not invented business-policy reasons. A validated input may still fail policy
checks. Passing validation never means its evidence is true or authoritative.

## Bounds and decoding

Raw payload: at most 262144 UTF-8 bytes. Python objects also undergo a canonical
size bound (JSON serialization including default separator spaces). Maximum
nesting 24, visited nodes 20000, collection size 1000, string length 8192 Unicode
code points, integer magnitude 10^12. Resource bounds count object keys too.
Strings must encode as strict UTF-8. Duplicate JSON keys, NaN/Infinity, floats,
non-string object keys, tuples and arbitrary Python objects are rejected. Bools
are not integers. Dates are canonical ISO `YYYY-MM-DD`. Cyclic Python objects
terminate at a traversal bound. Raw nesting is checked before JSON decoding.
These fixed bounds intentionally reject otherwise meaningful larger inputs.

## Closed envelopes and six fact schemas

All objects reject unknown fields, including records that a policy would skip.
An identifier is a nonblank string. Text may be empty. Quantities are integers,
not booleans. Required invoice quantities and F02 accepted quantities are positive;
other quantity/limit fields are nonnegative. Missing and null are not coerced.
The authoritative machine definitions are the exported `SCHEMAS` and `PARAGRAPH`.

Envelope required: `case_id`, `family_id` (F01–F06), `policy_source_id`, `sources`.
Optional: `split`, `question`, `synthetic` (bool), `raw_text`.
Each source requires `source_id`, `locator`, `facts`; optional `text`,
`source_kind`, `raw_text`. A repeated `(source_id, locator)` must have exactly
identical JSON payload. Sources can carry partial top-level facts, but the merged
facts must satisfy the family schema. Repeated fact keys must have identical
values; arrays are not concatenated. Inputs and metadata are bounded first.

Every family requires `request.po_line` and `request.invoice_quantity`.

- **F01:** request also requires `invoice_id`, unique `target_serials`.
  `lots[]` require `lot_id`, `po_line`, `status` accepted/pending and unique
  `serials`. Lot identity participation/overlap remains the baseline's policy
  logic, so an identity collision outside participating serials is not newly
  classified as an error.
- **F02:** `acceptance` requires `po_line`, `signer`, `signed_on`,
  `accepted_quantity`. Optional `status` must be a recognized status and must
  equal accepted to pass the gate. `delegation_registry[]` require `type`
  grant/deny, `signer`, `po_line`, `valid_from`, `valid_to` in nonreversed order.
  `max_quantity` is required on grant, optional but typed on deny.
- **F03:** `inspection_register[]` require `report_id`, `po_line`, `phase`
  final/preliminary, `status` accepted/rejected/pending/unknown, `quantity`,
  `recorded_on`. The gate types even preliminary and other-line records;
  policy participation and report conflicts still belong to the predictor.
- **F04:** request requires `as_of`. `acceptance_ledger` requires `records` and
  `events`. Records require `record_id`, `po_line`, `status` accepted/rejected,
  `quantity`, `created_on`. Events require `event_id`, `type` revoke/supersede,
  `old_id`, `effective_on`. `new_id` is required and nonnull for supersede;
  optional nullable string for revoke (legacy supplied values are retained but
  do not create a revoke target edge). All events, including future ones, must
  have equal payloads for equal IDs. Exact repeated events are allowed. Endpoint,
  record identity, graph, time filtering and live status remain policy logic.
- **F05:** request permits nullable/absent `receipt_on` and optional dates
  `invoice_on`, `reviewed_on`. Acceptance requires `signed_on`, `declared_regime`
  OLD/NEW, `quantity`, `status` accepted/rejected. Optional `po_line`, if present,
  must equal the request line. `quality_release` is optional/nullable, with
  optional typed `released` bool and nullable `released_on`. `transition_register`
  is optional/nullable, with optional `po_line`, `permitted` bool and nullable
  `grandfather_until`. Incomplete optional objects remain evidence gaps for the
  baseline, but any supplied field must have its declared type.
- **F06:** request also requires `invoice_id`; `closure_claim` requires
  `source_id`, `locator`. `source_catalog[]` require `source_id`, `kind`,
  `paragraphs`, optionally nullable document-level `invoice_id`. Paragraph fields
  are optional: `locator`, `paragraph_mode` asserted/quoted/example, nullable
  `invoice_id`, `po_line`, `status`, `accepted_quantity`, `unit`, `signer_role`,
  and `text`. Status is accepted/rejected/not_accepted/pending/unknown.
  Missing optional paragraph values remain policy evidence gaps, never inferred
  from neighboring paragraphs. Legacy top-level attachment facts for the seven
  paragraph assertion fields are allowed, typed, and checked against their own
  source/catalog locator; they cannot fill absent catalog values. No enum of
  all possible document kinds, roles or units is invented: these are strings
  whose eligibility is checked by policy.

F02 missing explicit status preserves the legacy positive-acceptance premise;
F05 missing explicit acceptance line preserves the legacy pre-mapped premise.
This compatibility choice does **not** establish either fact from external
records. Such facts must be supplied by a trustworthy structured-data producer.
If explicit fields contradict these premises, the contract blocks them.

## Prose boundary and coverage cost

Legacy source-level `text`, `question` and `source_kind` are descriptive metadata,
not evaluated assertions. Their type is checked, but their meaning is not. In
particular this gate makes no safety claim about contradictory text hidden there.
For new ingestion, put unverified prose in optional envelope/source `raw_text`.
Any nonempty raw_text prevents closure. Existing F06 paragraph `text` is also
always treated as unverified prose, regardless of language, polarity, matching
keywords or alleged agreement. Any nonempty paragraph text in the catalog
prevents closure. There is no “verified=true” caller override.

The wrapper first retains any nonclosing policy result and its original reason.
If policy would close but unverified prose exists, the wrapper returns
`needs_review` / `contract_text_unverified`, marks status `abstained`, and
`prose_verified=false`. This is broad abstention, not contradiction detection.
It blocks both matching and conflicting prose, and may block closure due to an
uncited paragraph. A structured-only input without prose can still close; this
means trusting its supplied structured facts, not proving entailment. Validation
alone is not the closure-safe API: use `apply_contract` or `predict_case`.

## Development exposure and regressions

The implementer read README, baseline code and tests, stage-04 report, all of
stress-v1 probes (including its embedded oracles), and all six existing v1
**input** files. No evaluator `labels.json` was opened by the implementer.
A development-only comparison with baseline outputs was run before the final
implementation freeze. Therefore neither these 60 cases nor stress-v1 is an
independent prospective test, and the freeze must not be described as preceding
inspection of those inputs or development results. The independent new challenge
is a separate evaluation, if run after the final file hashes are recorded.

The new tests explicitly retain old failures S25, S26, S27, S29 as regression
probes; they are not newly discovered or hidden tests. Regression expectations:
all 22 old in-policy probes retain exact decision/reason, all 8 old OOD probes
are nonclosing, and 57 of 60 old cases retain baseline decision/reason. The
three former F06 closures C01/C02/C03 abstain because of prose, an intentional
coverage loss rather than demonstrated increased business accuracy. Test counts
are engineering test methods, not independent transactions.

Run `python -B -m unittest discover -s tests -p test_input_contract.py -v`.
The regression test reads only existing input JSON and stress probe JSON, never
labels. The project-wide suite includes older evaluator tests that may read
labels; distinguish that execution from this module's direct read boundary.

No historical baseline, rule_ir.py, stress-v1 data, or historical result is
modified. No real model call, expert annotation, real transaction or payment is
performed. This contract does not supply the missing common array/graph IR or
establish that goal-driven ontology induction has an advantage.
