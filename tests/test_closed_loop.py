from sanad.closed_loop import cycle, metrics

def event(seq, nxt=None):
    d={'telemetry':[{'requests_per_min':x,'failed_auth':0} for x in seq]}
    if nxt is not None: d['next_observation']={'requests_per_min':nxt,'failed_auth':0}
    return d

def test_warning_does_not_execute_restart(tmp_path):
    r=cycle(event([300,390,480], 530),tmp_path/'a.db')
    assert r['forecast']['early_warning']
    assert r['decision']['action']=='no_action'
    assert not r['decision']['executed_disruptive_recovery']
    assert r['verification']['warning_correct']

def test_security_escalates(tmp_path):
    e=event([300,390,480]); e['unauthorized_changes']=True; e['failed_auth']=70
    r=cycle(e,tmp_path/'b.db')
    assert r['decision']['action']=='preserve_and_escalate'

def test_metrics_count_only_verified(tmp_path):
    db=tmp_path/'c.db'
    cycle(event([300,390,480], 530),db)
    cycle(event([300,320,340]),db)
    m=metrics(db)
    assert m['cycles']==2 and m['verified_cycles']==1 and m['confusion_matrix']['tp']==1

def test_bad_input(tmp_path):
    import pytest
    with pytest.raises(ValueError): cycle(event([1,2]),tmp_path/'d.db')
