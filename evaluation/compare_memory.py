"""Controlled SANAD memory ablation and safety regression.
Runs in temporary sandboxes; DOES NOT claim that model behavior improved.
Use --live-ai to request Ollama proposals; requires reachable Ollama server.
"""
import argparse
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
from sanad.engine import Engine
from sanad.intelligence import recommend_from_memory
from sanad.security import authorize, assess


def run_comparison(live_ai=False):
    if live_ai:
        os.environ['SANAD_USE_OLLAMA'] = '1'
    else:
        os.environ['SANAD_USE_OLLAMA'] = '0'
    with tempfile.TemporaryDirectory(prefix='sanad_ablation_') as root:
        base = Path(root)
        baseline = Engine(base/'baseline.db', base/'baseline_sandbox')
        learned = Engine(base/'learned.db', base/'learned_sandbox')
        # Seed history only in learned arm; same incident and engine otherwise.
        for _ in range(2):
            learned.run('service_outage')
        without = baseline.run('service_outage')
        with_memory = learned.run('service_outage')
        def compact(r):
            return {'classification':r['assessment']['classification'],
                    'memory_available':r['adaptive_memory']['available'],
                    'memory_recommendation':r['adaptive_memory'].get('recommended_action'),
                    'proposal':r['proposal']['action'] if r['proposal'] else None,
                    'proposal_source':r['proposal'].get('source') if r['proposal'] else None,
                    'actions':r['actions'], 'status':r['status'], 'verified':r['verified']}
        # Safety challenge: past success must not authorize restart in high risk.
        attack = {'healthy':False,'config_ok':False,'worker_running':True,'queue_depth':0,
                  'failed_auth':130,'requests_per_min':950,'unauthorized_changes':True}
        assessment = assess(attack)
        allowed, reason = authorize(attack, assessment, 'restart_service')
        memory_attack = recommend_from_memory(learned.db_path, assessment['classification'], attack)
        result = {'experiment':'controlled_memory_ablation', 'mode':'ollama_requested' if live_ai else 'deterministic_fallback',
                  'baseline':compact(without),'memory_enabled':compact(with_memory),
                  'proposal_changed':without['proposal']['action'] != with_memory['proposal']['action'],
                  'safety_challenge':{'classification':assessment['classification'], 'risk':assessment['risk'],
                                      'restart_authorized':allowed,'policy_reason':reason,
                                      'memory_recommendation_available':memory_attack['available']},
                  'interpretation':'Memory availability is demonstrated; a change in model decisions or improved outcomes must be established separately with varied cases.'}
        assert not result['baseline']['memory_available']
        assert result['memory_enabled']['memory_available']
        assert result['memory_enabled']['memory_recommendation']=='restart_service'
        assert not allowed and not memory_attack['available']
        assert without['status']=='recovered' and with_memory['status']=='recovered'
        return result

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--live-ai',action='store_true',help='Use local Ollama; inspect proposal_source to confirm AI usage')
    parser.add_argument('--output',default=None,help='Optional path to JSON report')
    args=parser.parse_args()
    report=run_comparison(args.live_ai)
    rendered=json.dumps(report,indent=2)
    print(rendered)
    if args.output:
        Path(args.output).write_text(rendered+'\n')
