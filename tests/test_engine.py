import os
os.environ['SANAD_USE_OLLAMA']='0'
from sanad.engine import Engine

def test_scenarios(tmp_path):
    e=Engine(tmp_path/'test.db')
    expected={'service_outage':'restart_service','bad_configuration':'restore_config',
              'suspected_intrusion':'preserve_and_escalate','ambiguous_incident':'preserve_and_escalate'}
    for scenario,action in expected.items():
        r=e.run(scenario)
        assert r['executed']==action and r['verified'], r
    assert len(e.history())==4

def test_attack_blocks_restart(tmp_path):
    r=Engine(tmp_path/'test.db').run('suspected_intrusion',override='restart_service')
    assert r['policy']['allowed'] is False and r['executed']=='preserve_and_escalate'
    assert r['final']['healthy'] is False

def test_unknown_action_blocked(tmp_path):
    r=Engine(tmp_path/'test.db').run('service_outage',override='delete_database')
    assert r['status']=='blocked_and_escalated'

def test_ambiguous_no_autorestart(tmp_path):
    r=Engine(tmp_path/'test.db').run('ambiguous_incident',override='restart_service')
    assert not r['policy']['allowed']

def test_evidence_immutable(tmp_path):
    r=Engine(tmp_path/'test.db').run('bad_configuration')
    assert r['initial']['config_ok'] is False and r['final']['config_ok'] is True
    assert len(r['evidence_sha256'])==64

def test_cascading_failure_order(tmp_path):
    r=Engine(tmp_path/'test.db').run('multi_failure')
    assert r['actions']==['restart_worker','drain_queue']
    assert r['verified'] and r['health_after']['ok']

def test_sandbox_changes_persist(tmp_path):
    e=Engine(tmp_path/'test.db')
    r=e.run('service_outage')
    assert r['evidence']['health_before']['ok'] is False
    assert e.sandbox.health()['ok'] is True

def test_attack_preserves_state(tmp_path):
    e=Engine(tmp_path/'test.db')
    r=e.run('suspected_intrusion')
    assert r['evidence']['health_before']['state']==r['health_after']['state']
