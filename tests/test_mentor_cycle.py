from sanad.mentor_cycle import run
def event(next_value=500):
    return {'healthy':True,'config_ok':True,'worker_running':True,
      'telemetry':[{'requests_per_min':300,'failed_auth':0},
                   {'requests_per_min':350,'failed_auth':0},
                   {'requests_per_min':400,'failed_auth':0}],
      'next_observation':{'requests_per_min':next_value,'failed_auth':0}}
def test_feedback_adapts_only_after_three_verified_outcomes(tmp_path):
    db=tmp_path/'cycles.db'
    for _ in range(3):
        d=run(event(480),db)
        assert d['decision']['executed_disruptive_recovery'] is False
    d=run(event(480),db)
    assert d['adaptive_forecast']['past_verified_examples']==3
    assert d['adaptive_forecast']['bias_correction']['requests_per_min']==30
    assert d['adaptive_forecast']['predicted_next']['requests_per_min']==480
def test_high_risk_preserves_and_escalates(tmp_path):
    e=event()
    e['failed_auth']=60
    e['unauthorized_changes']=True
    d=run(e,tmp_path/'cycles.db')
    assert d['decision']['action']=='preserve_and_escalate'
    assert not d['decision']['executed_disruptive_recovery']
