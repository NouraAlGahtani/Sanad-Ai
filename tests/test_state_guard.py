from sanad.engine import Engine
from unittest.mock import patch

def test_stale_llm_restart_is_corrected_after_worker_recovers(tmp_path):
    stale={'action':'restart_worker','source':'ollama','reason':'stale observation'}
    with patch('sanad.engine.propose',return_value=stale):
        r=Engine(tmp_path/'test.db').run('multi_failure')
    assert r['status']=='recovered'
    assert r['actions']==['restart_worker','drain_queue']
    assert r['trace'][1]['proposal']['source']=='state_guard'
    assert r['trace'][1]['proposal']['original_proposal']['source']=='ollama'
    assert r['health_after']['ok'] is True

def test_stale_action_never_bypasses_attack_safety(tmp_path):
    with patch('sanad.engine.propose',return_value={'action':'restart_worker','source':'ollama','reason':'bad'}):
        r=Engine(tmp_path/'test.db').run('suspected_intrusion')
    assert r['status']=='blocked_and_escalated'


def test_llm_no_action_corrected_for_invalid_configuration(tmp_path):
    stale={'action':'no_action','source':'ollama','reason':'incorrectly overlooked configuration'}
    with patch('sanad.engine.propose',return_value=stale):
        r=Engine(tmp_path/'test.db').run('bad_configuration')
    assert r['status']=='recovered'
    assert r['actions']==['restore_config']
    assert r['trace'][0]['proposal']['source']=='state_guard'
    assert r['trace'][0]['proposal']['original_proposal']['action']=='no_action'
    assert r['health_after']['ok'] is True

def test_llm_no_action_corrected_for_service_outage(tmp_path):
    stale={'action':'no_action','source':'ollama','reason':'incorrectly overlooked outage'}
    with patch('sanad.engine.propose',return_value=stale):
        r=Engine(tmp_path/'test.db').run('service_outage')
    assert r['status']=='recovered'
    assert r['actions']==['restart_service']
    assert r['trace'][0]['proposal']['source']=='state_guard'

def test_no_action_rejected_by_independent_policy_for_unhealthy_service():
    from sanad.security import authorize
    allowed, reason=authorize({'healthy':False,'config_ok':False,'worker_running':True,'queue_depth':0},
                              {'classification':'configuration_fault','risk':'low'},'no_action')
    assert not allowed
    assert 'No action prohibited' in reason
