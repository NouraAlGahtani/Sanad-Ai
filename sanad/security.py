"""Deterministic safety policy, independent of the AI model."""
ALLOWED = {'restart_service','restore_config','restart_worker','drain_queue','preserve_and_escalate','no_action'}
def assess(event):
    signals=[]
    if event.get('unauthorized_changes'): signals.append('unauthorized configuration change')
    if event.get('failed_auth',0)>=50: signals.append('authentication failure spike')
    if event.get('requests_per_min',0)>=500: signals.append('abnormal request volume')
    if len(signals)>=2: return {'classification':'suspected_attack','risk':'high','signals':signals}
    if not event.get('worker_running',True) and event.get('queue_depth',0)>=100 and not signals:
        return {'classification':'worker_queue_failure','risk':'low','signals':['worker offline','queue backlog']}
    if not event.get('config_ok',True) and not signals: return {'classification':'configuration_fault','risk':'low','signals':['invalid configuration']}
    if not event.get('healthy',True) and not signals and event.get('failed_auth',0)==0: return {'classification':'service_fault','risk':'low','signals':['service unavailable']}
    return {'classification':'uncertain','risk':'medium','signals':signals or ['insufficient evidence']}
def authorize(event, assessment, proposed):
    if proposed not in ALLOWED: return False,'Action not on allowlist'
    if assessment['risk']!='low' and proposed not in ('preserve_and_escalate','no_action'): return False,'Risk gate: recovery blocked pending investigation'
    if proposed=='no_action' and assessment['risk']=='low' and (
        not event.get('healthy', True) or not event.get('config_ok', True)
        or not event.get('worker_running', True) or event.get('queue_depth', 0)>=100
    ): return False,'No action prohibited: known recoverable failure remains'
    if proposed=='restore_config' and event.get('config_ok',True): return False,'Configuration is already valid'
    if proposed=='restart_service' and event.get('healthy',False): return False,'Service already healthy'
    if proposed=='restart_worker' and event.get('worker_running',True): return False,'Worker already running'
    if proposed=='drain_queue' and not event.get('worker_running',True): return False,'Worker must be running before queue recovery'
    if proposed=='drain_queue' and event.get('queue_depth',0)<100: return False,'Queue is not backed up'
    return True,'Authorized by deterministic policy'
