from sanad.engine import Engine
from sanad.intelligence import recommend_from_memory


def test_learning_requires_examples(tmp_path):
    engine = Engine(tmp_path / 'memory.db')
    state = {'healthy': False, 'config_ok': True, 'worker_running': True, 'queue_depth': 0}
    assert not recommend_from_memory(engine.db_path, 'service_fault', state)['available']
    engine.run('service_outage')
    assert not recommend_from_memory(engine.db_path, 'service_fault', state)['available']
    engine.run('service_outage')
    rec = recommend_from_memory(engine.db_path, 'service_fault', state)
    assert rec['available']
    assert rec['recommended_action'] == 'restart_service'
    assert rec['candidates'][0]['successful'] == 2


def test_learning_cannot_override_current_state_or_security(tmp_path):
    engine = Engine(tmp_path / 'memory.db')
    engine.run('service_outage')
    engine.run('service_outage')
    healthy = {'healthy': True, 'config_ok': True, 'worker_running': True, 'queue_depth': 0}
    assert not recommend_from_memory(engine.db_path, 'service_fault', healthy)['available']
    assert not recommend_from_memory(engine.db_path, 'suspected_attack', healthy)['available']


def test_engine_exposes_learning_advice(tmp_path):
    engine = Engine(tmp_path / 'memory.db')
    engine.run('service_outage')
    engine.run('service_outage')
    result = engine.run('service_outage')
    assert result['adaptive_memory']['recommended_action'] == 'restart_service'
