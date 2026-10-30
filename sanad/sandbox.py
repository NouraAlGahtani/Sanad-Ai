"""File-backed local demo environment. Never targets real services."""
import json
from pathlib import Path

class Sandbox:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_file = self.root / 'demo_service.json'
        self.good_file = self.root / 'known_good.json'
        if not self.good_file.exists():
            self.good_file.write_text(json.dumps({'config_ok': True, 'version': 1}))
    def reset(self, event):
        state = {'healthy': bool(event['healthy']), 'config_ok': bool(event['config_ok']),
                 'worker_running': bool(event.get('worker_running', True)), 'queue_depth': int(event.get('queue_depth', 0)),
                 'service': event['service']}
        self.state_file.write_text(json.dumps(state, indent=2))
        return self.inspect()
    def inspect(self):
        return json.loads(self.state_file.read_text())
    def health(self):
        s = self.inspect()
        checks = {'service': s['healthy'], 'configuration': s['config_ok'], 'worker': s['worker_running'], 'queue': s['queue_depth'] < 100}
        return {'ok': all(checks.values()), 'checks': checks, 'state': s}
    def apply(self, action):
        s = self.inspect()
        if action == 'restart_service': s['healthy'] = True
        elif action == 'restore_config': s['config_ok'] = True; s['healthy'] = True
        elif action == 'restart_worker': s['worker_running'] = True
        elif action == 'drain_queue':
            if not s['worker_running']: raise ValueError('Cannot drain queue while worker is stopped')
            s['queue_depth'] = 0
        else: raise ValueError('Unsupported sandbox operation')
        self.state_file.write_text(json.dumps(s, indent=2))
        return self.inspect()
