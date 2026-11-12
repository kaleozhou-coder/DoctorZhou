"""Experimental trusted-review receipt boundary, version 1.

A receipt is an external assertion from an authenticated review service. This
module does not authenticate reviewers, sign receipts, understand prose, or
measure human review quality. Never let model output or case input populate the
trusted_receipt argument. SHA-256 binds content; it does not prove truth.
"""
from datetime import datetime
import hashlib
import json
import re

from input_contract import ContractError, bounded, loads_case, validate_case
from input_contract_v2 import unverified_text_paths

VERSION = 'review-receipt-v1'
SCOPE = 'all_prose_consistent_with_structured_facts_and_policy'
FIELDS = {'version', 'review_id', 'reviewer_id', 'scope', 'case_sha256',
          'materials_sha256', 'reviewed_paths', 'outcome', 'reviewed_at', 'expires_at'}


def canonical_sha256(value):
    """Digest bounded JSON, sorted object keys but exact array order and text."""
    bounded(value)
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False,
                     separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _utc(value):
    if type(value) is not str or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', value):
        raise ValueError('Expected second-resolution UTC timestamp')
    return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')


def check_receipt(receipt, case, materials, paths, as_of):
    """Return a public diagnostic only, never the receipt or reviewer's identity."""
    if receipt is None:
        return 'review_receipt_missing'
    try:
        bounded(receipt)
        if type(receipt) is not dict or set(receipt) != FIELDS:
            return 'review_receipt_invalid'
        if receipt['version'] != VERSION or receipt['scope'] != SCOPE:
            return 'review_receipt_invalid'
        for name in ('review_id', 'reviewer_id'):
            if type(receipt[name]) is not str or not receipt[name].strip():
                return 'review_receipt_invalid'
        for name in ('case_sha256', 'materials_sha256'):
            if type(receipt[name]) is not str or not re.fullmatch('[0-9a-f]{64}', receipt[name]):
                return 'review_receipt_invalid'
        covered = receipt['reviewed_paths']
        if (type(covered) is not list or any(type(p) is not str for p in covered)
                or len(set(covered)) != len(covered)):
            return 'review_receipt_invalid'
        if set(covered) != set(paths):
            return 'review_receipt_incomplete'
        if receipt['outcome'] not in ('consistent', 'contradictory', 'unresolved') or type(receipt['outcome']) is not str:
            return 'review_receipt_invalid'
        reviewed, expires, now = (_utc(receipt['reviewed_at']), _utc(receipt['expires_at']), _utc(as_of))
        if reviewed >= expires:
            return 'review_receipt_invalid'
        if now < reviewed:
            return 'review_receipt_future'
        if now >= expires:
            return 'review_receipt_expired'
        if receipt['case_sha256'] != canonical_sha256(case):
            return 'review_receipt_case_mismatch'
        if receipt['materials_sha256'] != canonical_sha256(materials):
            return 'review_receipt_materials_mismatch'
        if receipt['outcome'] != 'consistent':
            return 'review_receipt_' + receipt['outcome']
        return 'review_receipt_accepted'
    except (ContractError, ValueError, TypeError, OverflowError):
        return 'review_receipt_invalid'


def apply_contract(case, materials, predictor, *, trusted_receipt=None, as_of=None):
    """Validate inputs, preserve nonclosure, and conditionally lift prose abstention.

    as_of is a trusted runner UTC clock, not a field supplied by the model/case.
    Only F01/F05 are supported here. Receipts attest prose consistency only;
    predictor/rule correctness and source authenticity remain separate problems.
    """
    try:
        if type(case) in (bytes, str):
            case = loads_case(case)
        validate_case(case)
        bounded(materials)
    except ContractError as error:
        return {'case_id': case.get('case_id') if type(case) is dict and type(case.get('case_id')) is str else None,
                'decision': 'needs_evidence' if error.code == 'contract_missing' else 'needs_review',
                'evidence_ids': [], 'reason_codes': [error.code], 'source_refs': [],
                'payment_authorized': False,
                'input_contract': {'version': VERSION, 'status': 'blocked', 'code': error.code, 'path': error.path}}
    if case['family_id'] not in ('F01', 'F05'):
        return {'case_id': case['case_id'], 'decision': 'needs_review',
                'evidence_ids': [], 'reason_codes': ['review_receipt_unsupported_family'], 'source_refs': [],
                'payment_authorized': False,
                'input_contract': {'version': VERSION, 'status': 'unsupported'}}
    paths = unverified_text_paths(case)
    status = (check_receipt(trusted_receipt, case, materials, paths, as_of)
              if paths else 'review_receipt_not_required')
    result = dict(predictor(case, materials))
    result['input_contract'] = {'version': VERSION, 'status': 'validated',
                                'prose_verified': False,
                                'review_assertion_accepted': status == 'review_receipt_accepted',
                                'review_status': status,
                                'unverified_text_present': bool(paths),
                                'unverified_text_paths': paths}
    if paths and status != 'review_receipt_accepted' and result['decision'] == 'close_eligible':
        result['decision'] = 'needs_review'
        result['reason_codes'] = [status]
        result['input_contract']['status'] = 'abstained'
    result['payment_authorized'] = False
    return result
