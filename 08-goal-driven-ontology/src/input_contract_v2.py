"""Opt-in v2 prose boundary; shared v1 structure validation remains unchanged.

No natural-language interpretation, semantic agreement or authenticity proof.
"""
from input_contract import ContractError, loads_case, validate_case
from policy_baseline import predict_case as baseline_predict


def unverified_text_paths(case):
    """List nonempty schema-declared free-text fields of a validated case.

    Whitespace counts as text. Scan all sources, including uncited paragraphs.
    Identifier/category strings are not evidence prose channels in this contract.
    """
    paths = []
    for key in ('question', 'raw_text'):
        if case.get(key):
            paths.append('$.' + key)
    for index, source in enumerate(case['sources']):
        prefix = '$.sources[' + str(index) + ']'
        for key in ('text', 'raw_text'):
            if source.get(key):
                paths.append(prefix + '.' + key)
        if case['family_id'] == 'F06':
            for catalog_index, entry in enumerate(source['facts'].get('source_catalog', [])):
                for paragraph_index, paragraph in enumerate(entry['paragraphs']):
                    if paragraph.get('text'):
                        paths.append(prefix + '.facts.source_catalog[' + str(catalog_index)
                                     + '].paragraphs[' + str(paragraph_index) + '].text')
    return paths


def apply_contract(case, materials, predictor):
    """Validate eagerly, then gate a trusted predictor using the v2 boundary.

    No caller-provided verification flag is accepted. Predictor errors propagate.
    """
    try:
        if type(case) in (bytes, str):
            case = loads_case(case)
        validate_case(case)
    except ContractError as error:
        return {'case_id': case.get('case_id') if type(case) is dict and type(case.get('case_id')) is str else None,
                'decision': 'needs_evidence' if error.code == 'contract_missing' else 'needs_review',
                'evidence_ids': [], 'reason_codes': [error.code], 'source_refs': [],
                'payment_authorized': False, 'input_contract': {
                    'version': '2', 'status': 'blocked', 'code': error.code, 'path': error.path}}
    # Determine the boundary before calling the trusted predictor. No mutation.
    paths = unverified_text_paths(case)
    result = dict(predictor(case, materials))
    result['input_contract'] = {'version': '2', 'status': 'validated',
                                'prose_verified': False, 'unverified_text_present': bool(paths),
                                'unverified_text_paths': paths}
    if paths and result['decision'] == 'close_eligible':
        result['decision'] = 'needs_review'
        result['reason_codes'] = ['contract_text_unverified']
        result['input_contract']['status'] = 'abstained'
    result['payment_authorized'] = False
    return result


def predict_case(case, materials):
    """Apply v2 to the unchanged deterministic synthetic policy baseline."""
    return apply_contract(case, materials, baseline_predict)
