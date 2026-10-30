from sanad.intelligence import analyze, memory_summary
from sanad.engine import Engine

def test_forecast_needs_telemetry():
    assert analyze({'healthy': True})['forecast']['available'] is False

def test_forecast_early_warning():
    event={'healthy':True,'telemetry':[{'failed_auth':10,'requests_per_min':100},{'failed_auth':25,'requests_per_min':120},{'failed_auth':42,'requests_per_min':140}]}
    result=analyze(event)
    assert result['forecast']['early_warning'] is True
    assert result['detection']['detected'] is False

def test_memory_is_descriptive(tmp_path):
    engine=Engine(tmp_path/'test.db')
    engine.run('service_outage')
    result=memory_summary(engine.db_path)
    assert result['sample_size']==1
    assert result['by_classification']['service_fault']['observed']==1

def test_engine_exposes_intelligence(tmp_path):
    engine=Engine(tmp_path/'test.db')
    result=engine.run('service_outage')
    assert 'intelligence' in result and 'prior_incident_memory' in result
