import os
import sqlite3
import json
from pathlib import Path
from flask import Flask, jsonify, render_template, request
from sanad.engine import Engine
from sanad.scenarios import SCENARIOS
from sanad.intelligence import memory_summary, analyze
from sanad.closed_loop import cycle, metrics
from sanad.mentor_cycle import run as mentor_run
app=Flask(__name__)
app.config['JSON_SORT_KEYS']=False
engine=Engine(os.getenv('SANAD_DB',str(Path(__file__).parent/'sanad.db')))
@app.get('/')
def index(): return render_template('dashboard.html')
@app.get('/api/scenarios')
def scenarios(): return jsonify({k:{'name':v['name'],'description':v['log']} for k,v in SCENARIOS.items()})
@app.post('/api/run')
def run():
    payload=request.get_json(silent=True) or {}
    if not isinstance(payload,dict) or payload.get('scenario') not in SCENARIOS: return jsonify({'error':'Select a valid scenario'}),400
    return jsonify(engine.run(payload['scenario']))
@app.get('/api/history')
def history(): return jsonify(engine.history())
@app.get('/api/history/<int:incident_id>')
def history_detail(incident_id):
    with sqlite3.connect(engine.db_path) as con:
        row=con.execute('SELECT details FROM incidents WHERE id=?',(incident_id,)).fetchone()
    if not row:
        return jsonify({'error':'Incident not found'}),404
    return jsonify(json.loads(row[0]))
@app.get('/api/health')
def health(): return jsonify({'status':'ok','mode':'local-sandbox','ollama_enabled':os.getenv('SANAD_USE_OLLAMA','0')=='1'})
@app.get('/api/demo-health')
def demo_health():
    state=engine.sandbox.health()
    return jsonify(state), (200 if state['ok'] else 503)

@app.get('/api/intelligence/memory')
def intelligence_memory():
    return jsonify(memory_summary(engine.db_path))

@app.post('/api/intelligence/analyze')
def intelligence_analyze():
    payload=request.get_json(silent=True)
    if not isinstance(payload,dict):
        return jsonify({'error':'JSON object required'}),400
    if len(json.dumps(payload))>100000:
        return jsonify({'error':'Payload too large'}),413
    return jsonify(analyze(payload))

@app.post('/api/intelligence/cycle')
def intelligence_cycle():
    payload=request.get_json(silent=True)
    try:
        if len(json.dumps(payload))>100000: return jsonify({'error':'Payload too large'}),413
        return jsonify(cycle(payload, engine.db_path))
    except (ValueError, TypeError, KeyError) as exc:
        return jsonify({'error':str(exc)}),400

@app.get('/api/intelligence/cycle/metrics')
def intelligence_cycle_metrics():
    return jsonify(metrics(engine.db_path))

@app.post('/api/intelligence/mentor-cycle')
def mentor_cycle():
    payload=request.get_json(silent=True)
    try:
        if len(json.dumps(payload))>100000: return jsonify({'error':'Payload too large'}),413
        return jsonify(mentor_run(payload,engine.db_path))
    except (ValueError,TypeError,KeyError) as exc:
        return jsonify({'error':str(exc)}),400

if __name__=='__main__': app.run(host='127.0.0.1',port=int(os.getenv('PORT','5000')),debug=False,threaded=True)
