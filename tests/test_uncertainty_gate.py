import unittest
from sanad.security import authorize, assess
from sanad.engine import Engine
from tempfile import TemporaryDirectory
from pathlib import Path

class UncertaintyGateTests(unittest.TestCase):
    def test_uncertain_no_action_denied(self):
        allowed, reason = authorize({'healthy':False}, {'classification':'uncertain','risk':'medium'}, 'no_action')
        self.assertFalse(allowed)
    def test_attack_no_action_denied(self):
        allowed, reason = authorize({'healthy':False}, {'classification':'suspected_attack','risk':'high'}, 'no_action')
        self.assertFalse(allowed)
    def test_escalation_allowed(self):
        for classification,risk in [('uncertain','medium'),('suspected_attack','high')]:
            self.assertTrue(authorize({}, {'classification':classification,'risk':risk}, 'preserve_and_escalate')[0])
    def test_unknown_action_denied(self):
        self.assertFalse(authorize({}, {'classification':'uncertain','risk':'medium'}, 'delete_logs')[0])
    def test_engine_uncertain_override_cannot_silently_exit(self):
        event={'service':'test','healthy':False,'config_ok':True,'worker_running':True,'queue_depth':0,'requests_per_min':550,'failed_auth':0,'unauthorized_changes':False,'log':'Possible traffic spike'}
        with TemporaryDirectory() as d:
            result=Engine(Path(d)/'incidents.db',Path(d)/'sandbox').run('test',override='no_action',evaluation_event=event)
        self.assertEqual(result['status'],'blocked_and_escalated')
        self.assertEqual(result['actions'],['preserve_and_escalate'])
        self.assertTrue(result['verified'])

if __name__=='__main__': unittest.main()
