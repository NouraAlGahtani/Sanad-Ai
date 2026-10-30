"""Mentor-aligned, sandbox-only sequential intelligence cycle.

Uses past *verified* forecasts to correct next-sample projections.
No automatic service changes are authorized by a forecast.
"""
import json
import sqlite3
from .closed_loop import cycle, init_db
from .security import assess, authorize

def _past_errors(db_path, limit=30):
    init_db(db_path)
    with sqlite3.connect(str(db_path)) as db:
        rows=db.execute("SELECT details FROM forecast_cycles WHERE breach IS NOT NULL ORDER BY id DESC LIMIT ?",(limit,)).fetchall()
    errors={'requests_per_min':[], 'failed_auth':[]}
    for (raw,) in rows:
        try:
            d=json.loads(raw)
            for key in errors:
                forecast=d['forecast']['metrics'][key]['predicted_next']
                observed=d.get('observed_next',{}).get(key)
                if observed is not None:
                    errors[key].append(float(observed)-float(forecast))
        except (KeyError,TypeError,ValueError): continue
    return {k:round(sum(v)/len(v),3) if len(v)>=3 else 0 for k,v in errors.items()},min(len(v) for v in errors.values())

def run(event, db_path, *, persist=True):
    # Read memory BEFORE inserting current observation, avoiding leakage.
    bias, count=_past_errors(db_path)
    result=cycle(event,db_path,persist=False)
    forecast=result['forecast']
    corrected={}
    for key,metric in forecast['metrics'].items():
        corrected[key]=max(0,round(metric['predicted_next']+bias.get(key,0),2))
    adaptive_warning=corrected['requests_per_min']>=500 or corrected['failed_auth']>=50
    current=dict(event)
    current.update(event['telemetry'][-1])
    assessment=assess(current)
    # The only preventive action is monitoring/escalation; no speculative restart.
    if assessment['risk']!='low' and (assessment['classification']=='suspected_attack' or not current.get('healthy',True) or not current.get('config_ok',True) or not current.get('worker_running',True) or current.get('unauthorized_changes')):
        action='preserve_and_escalate'
        reason='Current security/uncertain evidence requires human investigation'
    elif adaptive_warning:
        action='no_action'
        reason='Forecast warning: increase observation and prepare response; do not execute disruptive changes'
    else:
        action='no_action'
        reason='No projected threshold crossing; continue observation'
    allowed,policy_reason=authorize(current,assessment,action)
    if not allowed and action=='no_action':
        action='preserve_and_escalate'
        allowed,policy_reason=authorize(current,assessment,action)
        reason='Current state needs guarded incident response, not observation alone'
    observed=event.get('next_observation')
    adaptive_correct=None
    if observed is not None:
        breach=observed['requests_per_min']>=500 or observed['failed_auth']>=50
        adaptive_correct=bool(adaptive_warning)==bool(breach)
    result['adaptive_forecast']={'method':'verified_outcome_bias_correction','past_verified_examples':count,
        'bias_correction':bias,'predicted_next':corrected,'early_warning':adaptive_warning,
        'warning_correct':adaptive_correct,'trained_model':False}
    result['decision']={'action':action,'type':'observation_or_escalation','rationale':reason,
        'policy_authorized':allowed,'policy_reason':policy_reason,'executed_disruptive_recovery':False}
    result['learning']={'method':'past_verified_forecast_error_feedback','examples_used':count,
        'outcome_recorded':observed is not None and persist,'does_not_change_safety_policy':True}
    if observed is not None: result['observed_next']=observed
    if persist:
        init_db(db_path)
        with sqlite3.connect(str(db_path)) as db:
            cursor=db.execute('INSERT INTO forecast_cycles (warning,breach,correct,details) VALUES (?,?,?,?)',
                (int(forecast['early_warning']),None if observed is None else int(breach),
                 None if observed is None else int(forecast['early_warning']==breach),json.dumps(result)))
            result['cycle_id']=cursor.lastrowid
    return result
