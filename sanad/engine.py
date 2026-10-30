import copy, hashlib, json, sqlite3, threading
from pathlib import Path
from .scenarios import SCENARIOS
from .security import assess, authorize
from .agent import propose, fallback
from .sandbox import Sandbox
from .investigator import investigate
from .intelligence import analyze, memory_summary, recommend_from_memory

class Engine:
    def __init__(self, db_path, sandbox_dir=None):
        self.db_path=str(db_path)
        self.sandbox=Sandbox(sandbox_dir or (Path(db_path).parent/'sanad_sandbox'))
        self.lock=threading.RLock()
        with sqlite3.connect(self.db_path) as con:
            con.execute('CREATE TABLE IF NOT EXISTS incidents (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, scenario TEXT, classification TEXT, risk TEXT, proposed TEXT, executed TEXT, status TEXT, details TEXT)')
    def run(self, scenario, override=None, *, evaluation_event=None):
        if evaluation_event is None and scenario not in SCENARIOS: raise ValueError('Unknown scenario')
        with self.lock:
            event=copy.deepcopy(evaluation_event if evaluation_event is not None else SCENARIOS[scenario]); event.pop('name',None)
            initial=copy.deepcopy(event)
            self.sandbox.reset(event)
            evidence={'logs':[event['log']], 'metrics':{'requests_per_min':event['requests_per_min'],'failed_auth':event['failed_auth']}, 'health_before':self.sandbox.health()}
            investigation=investigate(event,self.sandbox)
            assessment=assess(event)
            intelligence=analyze(event)
            prior_memory=memory_summary(self.db_path, assessment["classification"])
            adaptive_memory=recommend_from_memory(self.db_path, assessment["classification"], self.sandbox.health()["state"])
            digest=hashlib.sha256(json.dumps({'initial':initial,'evidence':evidence,'investigation':investigation},sort_keys=True).encode()).hexdigest()
            trace=[]; executed=[]; proposal=None; policy=None; status='pending'
            for iteration in range(3):
                observed=self.sandbox.health(); current=observed['state']
                if observed['ok'] and not executed and assessment['risk']=='low': status='already_healthy'; break
                proposal=propose(event,assessment,{'state':current,'health':observed,'investigation':investigation,'adaptive_memory':adaptive_memory},executed)
                if override is not None and iteration==0: proposal={'action':override,'source':'test_override','reason':'Injected test proposal'}
                action=proposal['action']
                # A model may reason from stale initial observations after a repair.
                # Correct redundant actions from CURRENT sandbox state, without
                # mislabeling the correction as an AI decision.
                if assessment['risk']=='low' and assessment['classification']=='worker_queue_failure':
                    expected=fallback(assessment,current)
                    if action != expected and (not current.get('worker_running',False) or current.get('queue_depth',0)>=100):
                        proposal={'action':expected,'source':'state_guard',
                                  'reason':f'Corrected stale {action} proposal using current worker/queue state',
                                  'original_proposal':proposal}
                        action=expected
                # An unhealthy low-risk system must not be left untouched when a
                # known, reversible repair is available. The guard uses observed
                # sandbox state, never the model's explanation or original logs.
                if assessment['risk']=='low' and not observed['ok']:
                    required=None
                    if assessment['classification']=='configuration_fault' and not current.get('config_ok', True):
                        required='restore_config'
                    elif assessment['classification']=='service_fault' and not current.get('healthy', True):
                        required='restart_service'
                    if required and action in ('no_action', 'restart_service', 'restore_config', 'restart_worker', 'drain_queue') and action != required:
                        proposal={'action':required,'source':'state_guard',
                                  'reason':f'Current sandbox health requires {required}; corrected {action} proposal',
                                  'original_proposal':proposal}
                        action=required
                policy_allowed,reason=authorize(current,assessment,action)
                policy={'allowed':policy_allowed,'reason':reason}
                if not policy_allowed:
                    executed.append('preserve_and_escalate'); status='blocked_and_escalated'
                    trace.append({'step':iteration+1,'proposal':proposal,'policy':policy,'action':'preserve_and_escalate','health':observed})
                    break
                if action in ('preserve_and_escalate','no_action'):
                    executed.append(action); status='escalated' if action=='preserve_and_escalate' else 'no_action'
                    trace.append({'step':iteration+1,'proposal':proposal,'policy':policy,'action':action,'health':observed})
                    break
                self.sandbox.apply(action)
                executed.append(action)
                after=self.sandbox.health()
                trace.append({'step':iteration+1,'proposal':proposal,'policy':policy,'action':action,'health':after})
                if after['ok']: status='recovered'; break
            else: status='retry_limit_escalated'
            final_health=self.sandbox.health()
            verified=final_health['ok'] if status in ('recovered','already_healthy') else status in ('escalated','blocked_and_escalated') and final_health['state']==evidence['health_before']['state']
            if status=='retry_limit_escalated': verified=False
            result={'scenario':scenario,'initial':initial,'evidence':evidence,'investigation':investigation,'assessment':assessment,'intelligence':intelligence,'prior_incident_memory':prior_memory,'adaptive_memory':adaptive_memory,'proposal':proposal,'policy':policy,
                    'executed':executed[-1] if executed else 'no_action','actions':executed,'trace':trace,'status':status,'verified':verified,
                    'final':final_health['state'],'health_after':final_health,'evidence_sha256':digest,
                    'note':'Recovery modifies only SANAD local sandbox JSON files. No production infrastructure is touched.'}
            with sqlite3.connect(self.db_path) as con:
                cur=con.execute('INSERT INTO incidents (scenario,classification,risk,proposed,executed,status,details) VALUES (?,?,?,?,?,?,?)',
                    (scenario,assessment['classification'],assessment['risk'],proposal['action'] if proposal else '',','.join(executed),status,json.dumps(result)))
                result['id']=cur.lastrowid
            return result
    def history(self, limit=30):
        with sqlite3.connect(self.db_path) as con:
            con.row_factory=sqlite3.Row
            return [dict(r) for r in con.execute('SELECT id,created_at,scenario,classification,risk,proposed,executed,status FROM incidents ORDER BY id DESC LIMIT ?', (limit,))]
