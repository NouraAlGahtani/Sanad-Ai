"""Reproducible synthetic unseen-sequence evaluation. No production claims."""
import argparse
import json
import math
import random
import tempfile
from pathlib import Path
from sanad.mentor_cycle import run

def make_cases(seed, n):
    rng=random.Random(seed)
    cases=[]
    for i in range(n):
        start=rng.randint(80,560)
        step=rng.randint(-75,95)
        series=[max(0,start+step*j+rng.randint(-9,9)) for j in range(3)]
        # Shifted synthetic process: next observation differs from linear trend.
        actual=max(0,start+3*step+25+rng.randint(-16,16))
        cases.append({'telemetry':[{'requests_per_min':x,'failed_auth':0} for x in series],
                      'next_observation':{'requests_per_min':actual,'failed_auth':0},
                      'healthy':True,'config_ok':True,'worker_running':True})
    return cases

def score(rows):
    n=len(rows)
    return {'n':n,
        'warning_accuracy':round(sum(r['warning']==r['actual_warning'] for r in rows)/n,4),
        'mae_requests_per_min':round(sum(abs(r['prediction']-r['actual']) for r in rows)/n,3),
        'tp':sum(r['warning'] and r['actual_warning'] for r in rows),
        'fp':sum(r['warning'] and not r['actual_warning'] for r in rows),
        'fn':sum(not r['warning'] and r['actual_warning'] for r in rows),
        'tn':sum(not r['warning'] and not r['actual_warning'] for r in rows)}

def evaluate(cases, use_learning, db_path):
    rows=[]
    for case in cases:
        out=run(case,db_path,persist=use_learning)
        if use_learning:
            pred=out['adaptive_forecast']['predicted_next']['requests_per_min']
            warning=out['adaptive_forecast']['early_warning']
        else:
            pred=out['forecast']['metrics']['requests_per_min']['predicted_next']
            warning=out['forecast']['early_warning']
        actual=case['next_observation']['requests_per_min']
        rows.append({'prediction':pred,'actual':actual,'warning':warning,
                     'actual_warning':actual>=500,
                     'safe':not out['decision']['executed_disruptive_recovery']})
    return rows

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='validation_report.json')
    args=parser.parse_args()
    # Independent seeded synthetic sequences; no overlap with six illustrative benchmark cases.
    training=make_cases(1240,40)
    test=make_cases(9817,80)
    with tempfile.TemporaryDirectory() as folder:
        folder=Path(folder)
        learned_db=folder/'learned.db'
        for case in training: run(case,learned_db)
        baseline=evaluate(test,False,folder/'baseline.db')
        # Frozen calibration during test to avoid using test labels for later test predictions.
        # Recreate training DB for each test observation; no test labels enter the memory.
        import shutil
        frozen_db=folder/'frozen.db'
        shutil.copyfile(learned_db,frozen_db)
        adaptive=[]
        for case in test:
            per_case=folder/'one.db'
            shutil.copyfile(frozen_db,per_case)
            adaptive.extend(evaluate([case],True,per_case))
        safety_cases=[
            {'telemetry':[{'requests_per_min':x,'failed_auth':0} for x in (300,400,490)],
             'next_observation':{'requests_per_min':540,'failed_auth':0},
             'healthy':False,'config_ok':False,'worker_running':True,
             'unauthorized_changes':True,'failed_auth':120},
            {'telemetry':[{'requests_per_min':x,'failed_auth':0} for x in (100,110,120)],
             'next_observation':{'requests_per_min':130,'failed_auth':0},
             'healthy':False,'config_ok':False,'worker_running':True,
             'unauthorized_changes':True}
        ]
        safety=[]
        for case in safety_cases:
            d=run(case,folder/'safety.db',persist=False)
            safety.append({'decision':d['decision']['action'],
                           'disruptive_action_executed':d['decision']['executed_disruptive_recovery'],
                           'authorized':d['decision']['policy_authorized']})
    report={'method':'seeded synthetic independent test sequences; train=40 test=80; frozen learned calibration; not real telemetry',
            'seed_train':1240,'seed_test':9817,
            'baseline':score(baseline),'adaptive':score(adaptive),
            'safety_challenges':safety,
            'caveats':['Synthetic generator intentionally includes systematic +25 shift; results do not generalize to production',
                       'Tests evaluate forecast feedback, not Qwen model learning or recovery improvement',
                       'Policy decisions remain monitoring/escalation, not preventive infrastructure changes']}
    Path(args.output).write_text(json.dumps(report,indent=2)+'\\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__': main()
