import os
os.environ['SANAD_USE_OLLAMA']='0'
from sanad.engine import Engine
from sanad.investigator import TOOLS,execute_tool

def test_investigation_is_read_only(tmp_path):
    e=Engine(tmp_path/'t.db')
    event={'healthy':False,'config_ok':True,'service':'test','log':'outage','requests_per_min':5,'failed_auth':0}
    e.sandbox.reset(event)
    before=e.sandbox.inspect()
    for tool in TOOLS: execute_tool(tool,event,e.sandbox)
    assert before==e.sandbox.inspect()

def test_investigation_trace_and_recovery(tmp_path):
    e=Engine(tmp_path/'t.db')
    result=e.run('multi_failure')
    assert result['actions']==['restart_worker','drain_queue']
    assert result['status']=='recovered'
    assert len(result['investigation'])==4
    assert result['investigation'][0]['tool']=='check_health'

def test_suspicious_incident_stays_blocked(tmp_path):
    result=Engine(tmp_path/'t.db').run('suspected_intrusion',override='restart_service')
    assert result['status']=='blocked_and_escalated'
    assert not result['health_after']['ok']

def test_tool_rejects_unknown(tmp_path):
    e=Engine(tmp_path/'t.db')
    try: execute_tool('run_shell',{},e.sandbox)
    except ValueError: pass
    else: assert False
