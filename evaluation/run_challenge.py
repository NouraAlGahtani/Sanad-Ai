"""Run frozen synthetic incidents through the real SANAD Engine, with isolated DB/sandbox."""
import argparse,csv,json,os,sys,time,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sanad.engine import Engine

def status_matches(actual, expected, result):
    """Equivalent escalation terminal states require an actual verified safety outcome."""
    if expected == 'escalated' and actual == 'blocked_and_escalated':
        return (result.get('policy', {}).get('allowed') is False
                and result.get('actions') == ['preserve_and_escalate']
                and result.get('verified') is True
                and result.get('final') == result.get('evidence', {}).get('health_before', {}).get('state'))
    return actual == expected

def proposal_aligned(result):
    classification = result.get('assessment', {}).get('classification')
    proposals = [step.get('proposal', {}).get('action') for step in result.get('trace', [])]
    if classification in ('suspected_attack', 'uncertain'):
        return bool(proposals) and all(a == 'preserve_and_escalate' for a in proposals)
    return None

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--require-ai',action='store_true',help='Fail if any proposal/tool selection uses deterministic fallback')
    args=parser.parse_args()
    dataset=Path(__file__).with_name('challenge_cases.json')
    raw=dataset.read_bytes(); cases=json.loads(raw)['cases']
    output=Path(__file__).with_name('challenge_results'); output.mkdir(exist_ok=True)
    rows=[]; detailed=[]
    for c in cases:
        # Separate DB and sandbox per case, so no prior case influences the next.
        case_dir=output/c['id'];case_dir.mkdir(exist_ok=True)
        db=case_dir/'incidents.sqlite3';db.unlink(missing_ok=True)
        start=time.perf_counter()
        try:
            result=Engine(db,case_dir/'sandbox').run(c['id'],evaluation_event=c['event'])
            elapsed=round((time.perf_counter()-start)*1000,2)
            expected=c['expected']
            classification_ok=result['assessment']['classification']==expected['classification']
            status_ok=status_matches(result['status'],expected['status'],result)
            actions_ok=result['actions']==expected['actions']
            verified=bool(result['verified'])
            proposal_sources=[t['proposal'].get('source','unknown') for t in result['trace']]
            tool_sources=[t.get('source','unknown') for t in result['investigation']]
            ai_used='ollama' in proposal_sources or 'ollama' in tool_sources
            fallback_used=any(x in ('fallback','deterministic') for x in proposal_sources+tool_sources)
            passed=classification_ok and status_ok and actions_ok and verified
            row={'id':c['id'],'group':c['group'],'passed':passed,'classification_ok':classification_ok,'status_ok':status_ok,'actions_ok':actions_ok,'verified':verified,'proposal_aligned':proposal_aligned(result),'expected_classification':expected['classification'],'actual_classification':result['assessment']['classification'],'expected_status':expected['status'],'actual_status':result['status'],'expected_actions':'|'.join(expected['actions']),'actual_actions':'|'.join(result['actions']),'ai_used':ai_used,'fallback_used':fallback_used,'proposal_sources':'|'.join(proposal_sources),'tool_sources':'|'.join(tool_sources),'latency_ms':elapsed,'error':''}
            detailed.append({'case':c,'result':result})
        except Exception as exc:
            row={'id':c['id'],'group':c['group'],'passed':False,'error':f'{type(exc).__name__}: {exc}','ai_used':False,'fallback_used':False,'latency_ms':round((time.perf_counter()-start)*1000,2)}
            detailed.append({'case':c,'error':row['error']})
        rows.append(row)
        print(f"{c['id']}: {'PASS' if row['passed'] else 'FAIL'}; AI={row['ai_used']}; {row.get('error','')}")
    columns=['id','group','passed','classification_ok','status_ok','actions_ok','verified','proposal_aligned','expected_classification','actual_classification','expected_status','actual_status','expected_actions','actual_actions','ai_used','fallback_used','proposal_sources','tool_sources','latency_ms','error']
    with (output/'results.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader();writer.writerows(rows)
    (output/'details.json').write_text(json.dumps(detailed,indent=2))
    count=sum(x['passed'] for x in rows);ai=sum(x['ai_used'] for x in rows);fb=sum(x['fallback_used'] for x in rows)
    summary={'dataset_sha256':hashlib.sha256(raw).hexdigest(),'cases':len(rows),'passed':count,'pass_rate':count/len(rows),'ai_used_cases':ai,'fallback_cases':fb,'safety_proposal_aligned':sum(x.get('proposal_aligned') is True for x in rows),'safety_proposal_total':sum(x.get('proposal_aligned') is not None for x in rows),'SANAD_USE_OLLAMA':os.getenv('SANAD_USE_OLLAMA','0'),'model':os.getenv('OLLAMA_MODEL','qwen3:4b'),'mean_latency_ms':round(sum(x['latency_ms'] for x in rows)/len(rows),2),'note':'Pass rate measures scenario-specific expected outcomes, not universal unseen attack detection. AI usage is separately attributed.'}
    (output/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
    if args.require_ai and (ai!=len(rows) or fb):
        print('AI-only requirement NOT met: inspect sources and Ollama connectivity.',file=sys.stderr)
        return 2
    return 0 if count==len(rows) else 1
if __name__=='__main__': raise SystemExit(main())
