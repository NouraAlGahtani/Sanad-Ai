"""Conservative, explainable detection/forecasting and outcome memory.
No model training claims: forecasting uses an auditable linear trend heuristic.
"""
import json
import sqlite3
from statistics import mean


def analyze(event, history=None):
    history = history or []
    series = event.get('telemetry') or []
    if not isinstance(series, list):
        series = []
    valid = [x for x in series if isinstance(x, dict) and isinstance(x.get('failed_auth', 0), (int, float)) and isinstance(x.get('requests_per_min', 0), (int, float))]
    reasons = []
    if event.get('unauthorized_changes'):
        reasons.append('unauthorized configuration change')
    if event.get('failed_auth', 0) >= 50:
        reasons.append('authentication failures exceed safety threshold')
    if event.get('requests_per_min', 0) >= 500:
        reasons.append('request volume exceeds safety threshold')
    if not event.get('healthy', True):
        reasons.append('service health check failed')
    if not event.get('config_ok', True):
        reasons.append('configuration check failed')
    if not event.get('worker_running', True):
        reasons.append('worker health check failed')
    detection = {'detected': bool(reasons), 'signals': reasons, 'method': 'explainable_threshold_checks'}
    forecast = {'available': False, 'method': 'linear_trend_heuristic', 'warning': 'At least three telemetry samples required; not a trained predictive model'}
    if len(valid) >= 3:
        last = valid[-3:]
        # Forecast one observation interval ahead. This is a trend extrapolation, not a probability.
        forecasts = {}
        for key, threshold in [('failed_auth', 50), ('requests_per_min', 500)]:
            values = [float(x.get(key, 0)) for x in last]
            slope = (values[-1] - values[0]) / 2.0
            next_value = max(0, values[-1] + slope)
            forecasts[key] = {'latest': values[-1], 'predicted_next': round(next_value, 2), 'threshold': threshold, 'warning': next_value >= threshold, 'trend': 'rising' if slope > 0 else 'flat_or_falling'}
        forecast = {'available': True, 'method': 'linear_trend_heuristic', 'horizon': 'next_sample', 'metrics': forecasts, 'early_warning': any(v['warning'] for v in forecasts.values()), 'warning': 'Heuristic projection; no calibrated probability or learned time-series model'}
    similar = [r for r in history if r.get('classification') == event.get('classification_hint')]
    return {'detection': detection, 'forecast': forecast, 'memory_context': {'matched_prior_incidents': len(similar)}}


def memory_summary(db_path, classification=None):
    with sqlite3.connect(str(db_path)) as con:
        con.row_factory = sqlite3.Row
        if classification:
            rows = con.execute('SELECT classification, status, executed, details FROM incidents WHERE classification=? ORDER BY id DESC LIMIT 100', (classification,)).fetchall()
        else:
            rows = con.execute('SELECT classification, status, executed, details FROM incidents ORDER BY id DESC LIMIT 100').fetchall()
    stats = {}
    for row in rows:
        key = row['classification']
        group = stats.setdefault(key, {'observed': 0, 'recovered': 0, 'escalated': 0, 'actions': {}})
        group['observed'] += 1
        if row['status'] == 'recovered':
            group['recovered'] += 1
        if 'escalated' in row['status']:
            group['escalated'] += 1
        action = row['executed']
        a = group['actions'].setdefault(action, {'observed': 0, 'recovered': 0})
        a['observed'] += 1
        a['recovered'] += int(row['status'] == 'recovered')
    return {'source': 'local_sandbox_incident_history', 'sample_size': len(rows), 'by_classification': stats, 'limitation': 'Descriptive memory only. Does not update safety rules or establish causal efficacy.'}


def recommend_from_memory(db_path, classification, state, *, minimum_examples=2):
    """Outcome-based advisory, never an execution authorization.

    Uses only prior completed incidents; recommendations remain subject to
    current-state guards and the independent deterministic policy.
    """
    from .agent import ALLOWED_ACTIONS
    from .security import authorize
    assessment = {'classification': classification, 'risk': 'low', 'signals': []}
    if classification not in ('service_fault', 'configuration_fault', 'worker_queue_failure'):
        return {'available': False, 'reason': 'Uncertain/security cases cannot be learned into automatic recovery', 'candidates': []}
    with sqlite3.connect(str(db_path)) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute('SELECT executed,status,details FROM incidents WHERE classification=? ORDER BY id DESC LIMIT 100', (classification,)).fetchall()
    counts = {}
    for row in rows:
        if row['status'] not in ('recovered', 'retry_limit_escalated'):
            continue
        try:
            record = json.loads(row['details'])
            steps = record.get('trace', [])
        except (ValueError, TypeError):
            continue
        # Only score single-action recoveries: multi-step sequences cannot be
        # attributed to one action without misleading causal conclusions.
        if len(steps) != 1:
            continue
        action = steps[0].get('action')
        if action not in ALLOWED_ACTIONS or action in ('no_action', 'preserve_and_escalate'):
            continue
        entry = counts.setdefault(action, {'observed': 0, 'successful': 0})
        entry['observed'] += 1
        entry['successful'] += int(row['status'] == 'recovered' and record.get('health_after', {}).get('ok') is True)
    candidates = []
    for action, stats in counts.items():
        allowed, _ = authorize(state, assessment, action)
        candidates.append({'action': action, **stats, 'observed_success_rate': round(stats['successful']/stats['observed'], 3), 'currently_authorized': allowed})
    candidates.sort(key=lambda x: (-x['observed_success_rate'], -x['observed'], x['action']))
    eligible = [x for x in candidates if x['currently_authorized'] and x['observed'] >= minimum_examples]
    return {'available': bool(eligible), 'recommended_action': eligible[0]['action'] if eligible else None,
            'candidates': candidates, 'minimum_examples': minimum_examples,
            'reason': 'Historical single-step recovery outcomes; advisory only, not proof of causation or permission to execute'}
