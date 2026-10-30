import os
from unittest.mock import Mock, patch
from sanad.agent import propose

ASSESSMENT = {'classification': 'configuration_fault', 'risk': 'low'}
EVENT = {'log': 'bad config', 'config_ok': False}

def test_valid_model_proposal():
    with patch.dict(os.environ, {'SANAD_USE_OLLAMA': '1'}), patch('sanad.agent.requests.post') as post:
        post.return_value.json.return_value = {'response': '{"action":"restore_config","reason":"invalid configuration"}'}
        post.return_value.raise_for_status.return_value = None
        result = propose(EVENT, ASSESSMENT)
        assert result['source'] == 'ollama' and result['action'] == 'restore_config'

def test_invalid_action_falls_back():
    with patch.dict(os.environ, {'SANAD_USE_OLLAMA': '1'}), patch('sanad.agent.requests.post') as post:
        post.return_value.json.return_value = {'response': '{"action":"run_shell","reason":"bad"}'}
        result = propose(EVENT, ASSESSMENT)
        assert result['source'] == 'fallback' and result['action'] == 'restore_config'

def test_empty_model_response_falls_back():
    with patch.dict(os.environ, {'SANAD_USE_OLLAMA': '1'}), patch('sanad.agent.requests.post') as post:
        post.return_value.json.return_value = {'response': ''}
        result = propose(EVENT, ASSESSMENT)
        assert result['source'] == 'fallback'


def test_verbose_model_reason_is_replaced_with_current_state_summary():
    with patch.dict(os.environ, {'SANAD_USE_OLLAMA': '1'}), patch('sanad.agent.requests.post') as post:
        post.return_value.json.return_value = {'response': '{"action":"drain_queue","reason":"But wait, original worker_running was false. CURRENT STATE says true. The CURRENT STATE"}'}
        result = propose({'log':'worker stopped'}, {'classification':'worker_queue_failure','risk':'low'}, {'state':{'worker_running':True,'queue_depth':450}})
        assert result['source'] == 'ollama'
        assert result['action'] == 'drain_queue'
        assert '450' in result['reason']
        assert 'But wait' not in result['reason']
