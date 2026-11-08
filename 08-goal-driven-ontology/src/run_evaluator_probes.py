"""Exercise the evaluator using intentional label-fed probes, NOT model runs.
All outputs are tagged engineering_probe. Label replay and positive-only probes
are deliberate oracle checks, not predictions from any learned system.
"""
from pathlib import Path
import argparse
import json
import subprocess
import sys
from benchmark_eval import load_json, verify_freeze


def run(benchmark, output):
    benchmark, output = Path(benchmark), Path(output)
    verified=verify_freeze(benchmark)
    labels=load_json(benchmark/'evaluator/labels.json')['cases']
    output.mkdir(parents=True,exist_ok=True)
    summary={'experiment_type':'evaluator_engineering_probes',
             'model_runs':0,'human_review_participants':0,
             'claims_not_supported':['model accuracy','A/B superiority','human time savings','business safety'],
             'benchmark_freeze_sha256':verified['freeze_sha256'],'results':[]}
    for split in ('development','validation','test'):
        cases=[c for c in labels if c['split']==split]
        for probe in ('label_replay','close_all','review_all','empty','oracle_positive_only'):
            predictions=[]
            for c in cases:
                if probe=='empty': continue
                if probe=='oracle_positive_only' and c['expected_decision']!='close_eligible':continue
                decision={'close_all':'close_eligible','review_all':'needs_review'}.get(probe,c['expected_decision'])
                row={'case_id':c['case_id'],'decision':decision,'payment_authorized':False}
                if probe=='label_replay':
                    row.update(evidence_ids=c['required_evidence_ids'],reason_codes=c['required_reason_codes'])
                predictions.append(row)
            submission={'run':{'run_id':f'{split}-{probe}','method':probe,'execution_kind':'engineering_probe',
                               'benchmark_freeze_sha256':verified['freeze_sha256'],'split':split,
                               'uses_labels':True,'purpose':'Evaluator plumbing check; not a model output'},
                        'predictions':predictions}
            prefix=output/f'{split}-{probe}'
            submission_path=prefix.with_suffix('.submission.json')
            report_path=prefix.with_suffix('.report.json')
            submission_path.write_text(json.dumps(submission,indent=2)+'\n')
            completed=subprocess.run([sys.executable,str(Path(__file__).with_name('benchmark_eval.py')),
                                      '--benchmark',str(benchmark),'--submission',str(submission_path),
                                      '--split',split,'--output',str(report_path)],check=True,capture_output=True,text=True)
            prefix.with_suffix('.stdout.txt').write_text(completed.stdout)
            report=load_json(report_path)
            m=report['metrics']
            if probe=='label_replay':
                assert m['exact_decision_accuracy']==1
                assert report['source_locator_audit']['existence_rate']==1
            if probe in ('review_all','empty'): assert m['positive_close_recall']==0
            if probe in ('empty','oracle_positive_only'):assert m['conservative_false_close_rate_if_missing_negatives_close']==1
            if probe=='close_all':assert m['false_close_rate']==1
            summary['results'].append({'split':split,'probe':probe,'metrics':m,
                                       'source_locator_audit':report['source_locator_audit']})
    (output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'probe_run_n':len(summary['results']),'model_runs':0,'summary':str(output/'summary.json')},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--benchmark',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();run(args.benchmark,args.output)
