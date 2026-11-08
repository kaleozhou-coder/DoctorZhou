"""Author synthetic fixtures. This is not sample generation from business data."""
import copy
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
base = {'id': 'E1', 'type': 'AcceptanceRecord', 'order_line_id': 'PO1-L1', 'quantity': 10, 'unit': 'EA', 'status': 'accepted', 'authorized': True, 'revoked': False, 'policy_version': 'P0', 'source_id': 'synthetic:E1', 'source_locator': 'section:acceptance'}
cases = []
def add(cid, expected, records, description, line=None):
    cases.append({'id': cid, 'description': description, 'data_origin': 'authored_synthetic', 'policy_version': 'P0', 'invoice_line': line or {'order_line_id': 'PO1-L1', 'quantity': 10, 'unit': 'EA'}, 'records': records, 'expected': expected})
def rec(**kw):
    x=copy.deepcopy(base); x.update(kw); return x
add('C01', 'close_eligible', [rec()], 'Exact valid acceptance. Does not authorize payment.')
add('C02', 'needs_evidence', [], 'Invoice alone provides no acceptance evidence.')
add('C03', 'needs_evidence', [rec(type='DeliveryRecord')], 'Delivery is not inspection acceptance, even with status accepted.')
add('C04', 'needs_evidence', [rec(type='Invoice')], 'Invoice is not an acceptance record.')
add('C05', 'needs_evidence', [rec(order_line_id='PO2-L1')], 'Acceptance belongs to a different order line.')
add('C06', 'needs_review', [rec(authorized=False)], 'Acceptor is explicitly unauthorized under synthetic policy.')
add('C07', 'needs_review', [rec(authorized=None)], 'Unknown authority is not evidence of authority.')
add('C08', 'needs_evidence', [rec(quantity=9)], 'Accepted quantity does not cover the invoiced quantity.')
add('C09', 'close_eligible', [rec(quantity=4), rec(id='E2', quantity=6, source_id='synthetic:E2')], 'Two distinct records sum to sufficient quantity; synthetic policy assumes nonoverlapping lots.')
add('C10', 'needs_review', [rec(quantity=5), rec(quantity=5)], 'Duplicate evidence IDs cannot be double-counted.')
add('C11', 'needs_evidence', [rec(revoked=True)], 'Revoked record does not justify closing exception.')
add('C12', 'needs_review', [rec(unit='BOX')], 'Units require explicit mapping; EA and BOX are not silently equated.')
add('C13', 'needs_review', [rec(policy_version='P_OLD')], 'Unknown applicability of an earlier policy requires review.')
add('C14', 'needs_review', [rec(source_locator=None)], 'Evidence exists as a claim but has no checkable location.')
add('C15', 'needs_review', [rec(source_id=None)], 'Evidence lacks source identity.')
add('C16', 'needs_review', [rec(status='rejected')], 'Explicit rejection requires review, not automatic close.')
add('C17', 'needs_review', [rec(status='conflicting')], 'Conflicting acceptance status requires review.')
add('C18', 'needs_evidence', [rec(status=None)], 'A record with unknown acceptance status is not accepted by default.')
add('C19', 'needs_review', [rec()], 'Invoice lacks an unambiguous order-line link.', {'order_line_id': None, 'quantity': 10, 'unit': 'EA'})
add('C20', 'needs_review', [rec(quantity=0)], 'Zero accepted quantity is invalid for this positive invoice test.')
add('C21', 'needs_review', [rec()], 'Negative invoices require a return/credit-note model outside the scope.', {'order_line_id': 'PO1-L1', 'quantity': -1, 'unit': 'EA'})
add('C22', 'close_eligible', [rec(quantity=12)], 'Acceptance covers quantity; excess quantity does not alone block this narrow exception.')
add('C23', 'needs_evidence', [rec(quantity=4), rec(id='E2', quantity=5, source_id='synthetic:E2')], 'Partial records still total less than invoice quantity.')
add('C24', 'needs_review', [rec(id=None)], 'Missing evidence ID prevents reliable deduplication.')
add('C25', 'close_eligible', [rec(), rec(id='E2', type='DeliveryRecord', status='rejected')], 'Irrelevant delivery record must not replace valid acceptance decision.')
add('C26', 'close_eligible', [rec(), rec(id='E2', order_line_id='PO2-L1', status='rejected')], 'A different order line must not contaminate the targeted decision.')
add('C27', 'needs_review', [rec(), rec(id='E2', status='rejected')], 'Mixed accepted/rejected evidence on same line has unresolved conflict.')
add('C28', 'close_eligible', [rec(), rec(id='E2', revoked=True)], 'Revoked extra record is ignored when valid evidence independently suffices.')
(ROOT/'data/synthetic/acceptance_cases.json').write_text(json.dumps({'dataset_version':'0.1.0', 'provenance':'Hand-authored by an AI assistant for engineering tests; not real transactions or a held-out research benchmark.', 'cases':cases},ensure_ascii=False,indent=2)+'\n')
