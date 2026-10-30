"""Auditable, sandbox-only forecast-to-decision-to-outcome cycle.

Forecast warnings are NOT authority to change services. Security indicators
always require investigation. Outcomes are observed only when next telemetry
is supplied, never fabricated from a forecast.
"""
import json
import sqlite3
from .intelligence import analyze
from .security import assess, authorize


def _validate(event):
    if not isinstance(event, dict):
        raise ValueError('event must be a JSON object')
    telemetry = event.get('telemetry')
    if not isinstance(telemetry, list) or len(telemetry) < 3 or len(telemetry) > 1000:
        raise ValueError('telemetry must contain 3 to 1000 samples')
    for sample in telemetry:
        if not isinstance(sample, dict):
            raise ValueError('each telemetry sample must be an object')
        for key in ('requests_per_min', 'failed_auth'):
            value = sample.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1000000:
                raise ValueError('telemetry values must be nonnegative finite numbers')
    for key in ('requests_per_min', 'failed_auth'):
        if key in event and (isinstance(event[key], bool) or not isinstance(event[key], (int,float)) or not 0 <= event[key] <= 1000000):
            raise ValueError('invalid current metric')
    observed = event.get('next_observation')
    if observed is not None:
        if not isinstance(observed, dict):
            raise ValueError('next_observation must be an object')
        for key in ('requests_per_min', 'failed_auth'):
            value = observed.get(key)
            if isinstance(value, bool) or not isinstance(value, (int,float)) or not 0 <= value <= 1000000:
                raise ValueError('next_observation must contain both valid metrics')


def init_db(db_path):
    with sqlite3.connect(str(db_path)) as con:
        con.execute('''CREATE TABLE IF NOT EXISTS forecast_cycles
            (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
             warning INTEGER NOT NULL, breach INTEGER, correct INTEGER, details TEXT NOT NULL)''')


def cycle(event, db_path, *, persist=True):
    _validate(event)
    init_db(db_path)
    current = dict(event)
    for key in ('requests_per_min', 'failed_auth'):
        current[key] = event['telemetry'][-1][key]
    current.pop('next_observation', None)
    analysis = analyze(current)
    assessment = assess(current)
    warning = analysis['forecast']['early_warning']
    # No speculative restart or throttling based only on extrapolation.
    if assessment['classification'] == 'suspected_attack' or current.get('unauthorized_changes'):
        action = 'preserve_and_escalate'
        rationale = 'Security/uncertain classification: preserve evidence for investigation'
    elif warning:
        action = 'no_action'
        rationale = 'Early warning: monitor and prepare response; forecast does not authorize disruptive action'
    else:
        action = 'no_action'
        rationale = 'No forecast threshold crossing; continue monitoring'
    # Monitoring is an observation-only decision, not recovery authorization.
    allowed, reason = (True, 'Observation-only monitoring; no recovery authorized') if action == 'no_action' and current.get('healthy', True) and current.get('config_ok', True) and current.get('worker_running', True) else authorize(current, assessment, action)
    # If known failures exist, avoid misrepresenting no_action as approved.
    if not allowed:
        action = 'preserve_and_escalate'
        allowed, reason = authorize(current, assessment, action)
        rationale = 'Known fault requires investigation or recovery via the existing guarded engine'
    next_sample = event.get('next_observation')
    verification = {'available': next_sample is not None, 'method': 'compare_with_supplied_next_observation'}
    if next_sample is not None:
        actual = next_sample['requests_per_min'] >= 500 or next_sample['failed_auth'] >= 50
        verification.update({'actual_threshold_breach': actual, 'forecast_warning': warning,
                             'warning_correct': warning == actual,
                             'absolute_error': {k: round(abs(analysis['forecast']['metrics'][k]['predicted_next']-next_sample[k]), 3) for k in ('requests_per_min','failed_auth')}})
    result = {'detection': analysis['detection'], 'forecast': analysis['forecast'],
              'assessment': assessment, 'decision': {'action': action, 'type': 'monitoring_or_escalation',
              'rationale': rationale, 'policy_authorized': allowed, 'policy_reason': reason,
              'executed_disruptive_recovery': False}, 'verification': verification,
              'learning': {'method': 'append_only_forecast_outcome_history', 'updated': next_sample is not None and persist,
                           'does_not_change_safety_policy': True},
              'limitation': 'Telemetry is supplied by caller. No live monitoring or automated infrastructure mitigation.'}
    if persist:
        with sqlite3.connect(str(db_path)) as con:
            cur = con.execute('INSERT INTO forecast_cycles (warning, breach, correct, details) VALUES (?,?,?,?)',
                              (int(warning), None if next_sample is None else int(actual),
                               None if next_sample is None else int(warning == actual), json.dumps(result)))
            result['cycle_id'] = cur.lastrowid
    return result


def metrics(db_path):
    init_db(db_path)
    with sqlite3.connect(str(db_path)) as con:
        rows = con.execute('SELECT warning,breach,correct FROM forecast_cycles WHERE breach IS NOT NULL').fetchall()
        total = con.execute('SELECT COUNT(*) FROM forecast_cycles').fetchone()[0]
    tp = sum(w and b for w,b,_ in rows)
    fp = sum(w and not b for w,b,_ in rows)
    fn = sum(not w and b for w,b,_ in rows)
    tn = sum(not w and not b for w,b,_ in rows)
    return {'cycles': total, 'verified_cycles': len(rows), 'confusion_matrix': {'tp':tp,'fp':fp,'fn':fn,'tn':tn},
            'accuracy': (tp+tn)/len(rows) if rows else None,
            'precision': tp/(tp+fp) if tp+fp else None,
            'recall': tp/(tp+fn) if tp+fn else None,
            'limitation': 'Only caller-supplied observations; not an independent held-out benchmark.'}
