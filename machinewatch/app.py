"""Small local API. The browser reads saved history; POST /api/predict runs the model."""
import json
from pathlib import Path
import sqlite3
import time

from flask import Flask, jsonify, request
import joblib
import numpy as np
import pandas as pd

from .database import connect, latest_run
from .features import SENSORS, make_features, model_input


def create_app(project):
    project = Path(project)
    app = Flask(__name__, static_url_path='/static')
    app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024
    database = project / 'data' / 'machinewatch.db'
    with connect(database) as db:
        run = latest_run(db)
    # Only load model files created locally by the training command.
    bundle = joblib.load(project / 'artifacts' / f'{run["run_id"]}.joblib')
    report = json.loads(run['report_json'])

    @app.get('/')
    def index():
        return app.send_static_file('index.html')

    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'run_id': run['run_id'], 'model': run['model_name']}

    @app.get('/api/summary')
    def summary():
        return report

    @app.get('/api/machines')
    def machines():
        with connect(database) as db:
            rows = db.execute("SELECT * FROM machines WHERE split='test' ORDER BY machine_id").fetchall()
        return jsonify([dict(row) for row in rows])

    @app.get('/api/machines/<machine_id>')
    def history(machine_id):
        with connect(database) as db:
            machine = db.execute("SELECT * FROM machines WHERE machine_id=? AND split='test'", (machine_id,)).fetchone()
            if machine is None:
                return {'error': 'Held-out machine not found'}, 404
            rows = db.execute('''SELECT r.cycle, r.sensor_4, r.sensor_11, r.actual_rul,
                                        p.predicted_rul, p.warning
                                 FROM readings r JOIN predictions p
                                 ON r.machine_id=p.machine_id AND r.cycle=p.cycle
                                 WHERE r.machine_id=? AND p.run_id=? ORDER BY r.cycle''',
                              (machine_id, run['run_id'])).fetchall()
        return {'machine': dict(machine), 'history': [dict(row) for row in rows]}

    @app.post('/api/predict')
    def predict():
        payload = request.get_json(silent=True)
        rows = payload.get('readings') if isinstance(payload, dict) else None
        if not isinstance(rows, list) or not 1 <= len(rows) <= 1000:
            return {'error': 'Send readings: a list of 1–1000 consecutive readings for one engine.'}, 400
        required = ['cycle'] + SENSORS
        if any(not isinstance(row, dict) or set(row) != set(required) for row in rows):
            return {'error': f'Each reading must contain exactly: {", ".join(required)}'}, 400
        if any(isinstance(row[key], bool) or not isinstance(row[key], (int, float)) for row in rows for key in required):
            return {'error': 'All readings must be numbers, not strings or booleans.'}, 400
        frame = pd.DataFrame(rows)
        if not np.isfinite(frame.to_numpy(dtype=float)).all():
            return {'error': 'Readings must be finite numbers.'}, 400
        cycles = frame.cycle.to_numpy()
        if cycles[0] < 1 or (cycles % 1 != 0).any() or not (np.diff(cycles) == 1).all():
            return {'error': 'Cycles must be positive consecutive integers in ascending order.'}, 400
        # Ten readings reproduce the rolling features. Short histories only make
        # sense at the beginning of an engine's life, where fewer readings exist.
        if len(frame) < 10 and cycles[0] != 1:
            return {'error': 'Provide at least 10 readings, or a history starting at cycle 1.'}, 400
        frame['machine_id'] = 'request'
        started = time.perf_counter()
        features = model_input(make_features(frame).tail(1))
        remaining = max(0, float(bundle['model'].predict(features)[0]))
        return {'cycle': int(cycles[-1]), 'predicted_rul': round(remaining, 2),
                'warning': remaining <= 30, 'run_id': run['run_id'],
                'inference_ms': round((time.perf_counter() - started) * 1000, 2)}

    @app.errorhandler(413)
    def too_large(error):
        return {'error': 'Request exceeds the 1 MB limit.'}, 413

    @app.errorhandler(sqlite3.Error)
    def database_error(error):
        app.logger.error('Database request failed: %s', error)
        return {'error': 'Could not read the local database.'}, 503

    return app
