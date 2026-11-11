# Structured input contract v2: explicit unverified prose boundary

This opt-in version fixes a documented input-boundary omission, not natural-language
reasoning. It is hand-written synthetic engineering, not a real model experiment,
expert-validated procurement rule, authenticity check or production safety proof.
Historical v1 code, fixtures and results are unchanged.

## API and shared structure checks

`src/input_contract_v2.py` exposes `loads_case`, `validate_case`, `ContractError`,
`apply_contract(case, materials, predictor)` and `predict_case(case, materials)`.
The decoder, error class and validator are the exact imported v1 objects. All
v1 bounds, strict JSON decoding, closed schemas, eager checks, required fields,
conflict checks and compatibility premises remain unchanged. See
[input-contract-v1.md](input-contract-v1.md) for those structural requirements.
Calling `validate_case` alone does not enforce closure abstention.

The wrapper accepts a Python dict or strict JSON string/bytes, validates before
calling the trusted predictor, then preserves a nonclosing policy decision and
its reasons. Missing required data returns `needs_evidence`; other structural
errors return `needs_review`, with `input_contract.version="2"`, status `blocked`,
and the same deterministic code/path as v1. Invalid input never calls the
predictor. Predictor exceptions propagate and must remain evaluation failures.
The wrapper does not mutate inputs or predictor output dictionaries, access
files/network, or execute input code. Materials and predictor are trusted.
Every returned prediction forces `payment_authorized=false`.

## Exhaustive supported prose-channel boundary

All schema-declared free-text fields are unverified prose:

- Envelope `question` and `raw_text`.
- Every source's `text` and `raw_text`.
- F06 `sources[*].facts.source_catalog[*].paragraphs[*].text`, including
  uncited catalog entries and paragraphs.

Absence and the empty string mean no prose in that channel. Every other string,
including whitespace, non-Latin text, invisible characters, matching assertions,
contradictory assertions and irrelevant descriptions, counts. The implementation
uses only nonemptiness, not keywords, case identifiers, language, polarity,
asserted verification, or text-to-fact matching. `question` is included because
a caller can put assertions there; it is not safely exempted as a harmless prompt.

Any such prose causes a would-be `close_eligible` result to become `needs_review`
with reason `contract_text_unverified` and status `abstained`. Valid structured
input without such prose can still close. Otherwise status is `validated`, which
means structure validated, not prose or policy approved. Metadata always reports
`prose_verified=false`, `unverified_text_present`, and exact
`unverified_text_paths` (paths, not copied prose). Multiple occurrences remain
visible, including repeated identical sources. The path helper expects already
validated input and is not itself a validation entry point.

No `verified`, `prose_verified`, `text_verified` or other caller flag bypass exists:
unknown fields fail the unchanged closed schema, including text under unsupported
record fields. Nonclosing policy outputs retain their policy reasons even when
prose is present. Structural errors take precedence over prose abstention.

Identifiers and category/role values, including `case_id`, `policy_source_id`,
`source_id`, `locator`, `split`, `source_kind`, catalog `kind`, units and signer
roles, retain their v1 typed meaning as opaque structured values. They are not
supported evidence prose channels. No claim is made to detect assertions hidden
inside these strings, validate their real-world referents, or prove a caller has
faithfully extracted facts. In particular, a caller deleting contradictory prose
and retaining false structured facts can still produce closure. v2 supplies no
trusted extraction, signature/provenance verification or text-semantic agreement
detection. F02's missing-status and F05's missing-line legacy premises persist.

## Coverage cost and research interpretation

This deliberately broad abstention rejects matching and contradictory prose
identically. Harmless source descriptions, a generic question, or an uncited
paragraph can prevent closure. Merely renaming supplied prose into `question` or
legacy `source.text` no longer avoids the boundary. This is a stricter input
contract, not a business-policy label or a finding that the prose conflicts.

All 60 legacy benchmark inputs contain nonempty questions and source text
(parent's inspection); consequently all formerly closing positives are expected
to abstain under v2. This anticipated loss of all 20 legacy positive closures
must be reported alongside any reduction in unsafe closures and confirmed by
the separate retrospective evaluation. Do not strip benchmark prose to improve
its score, add JSON-echo exceptions, relabel controls, or overwrite old results.
The new structured-only engineering fixtures intentionally omit prose, including
questions, solely to test that this API still allows structurally trusted inputs.
They are not a substitute for the legacy coverage denominator.

## Tests, exposure and reproduction

The author read v1 implementation/protocol/tests, relevant baseline test fixture
builders and the stage-05 report describing E22. This is repair after exposure,
not a blind generalization claim. No historical evaluation labels or challenge
fixtures were opened for this implementation. New tests use only synthetic
in-memory fixtures. The old v1 test module independently contains retrospective
input/stress checks; running it is a regression, not held-out evaluation.

Run from the topic directory:

```sh
python -B -m unittest discover -s tests -p 'test_input_contract*.py' -v
```

The 13 new test methods cover every supported channel across applicable families,
matching/contradictory/neutral/whitespace parity, empty text, uncited paragraphs,
structured-only closure for all six families, nonmutation, type/unknown-field
rejection, verification-bypass rejection, validation order, JSON parity, exception
propagation and preservation of the v1 source-text failure. Test methods and their
parameter combinations are engineering checks, not independent business cases.
No model API, secrets, paid calls, real transactions or publication are involved.
