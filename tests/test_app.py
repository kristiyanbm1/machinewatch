import json
import sqlite3

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.dummy import DummyRegressor

from machinewatch.app import create_app
from machinewatch.database import connect, save_run
from machinewatch.features import SENSORS, FEATURES, make_features, model_input
from machinewatch.train import scores, warning_summary


@pytest.fixture
def project(tmp_path):
    frame = pd.DataFrame([{'machine_id': 'train-001', 'split': 'test', 'cycle': c,
                           'actual_rul': 12 - c, **{sensor: float(c) for sensor in SENSORS}}
                          for c in range(1, 13)])
    model = DummyRegressor(strategy='constant', constant=25)
    model.fit(model_input(make_features(frame)), frame.actual_rul)
    report = {'run_id': 'test-run', 'created_at': '2026-01-01', 'selected_model': 'dummy'}
    save_run(tmp_path / 'data' / 'machinewatch.db', frame, [25] * len(frame), report)
    (tmp_path / 'artifacts').mkdir()
    joblib.dump({'model': model, 'features': FEATURES, 'run_id': 'test-run'}, tmp_path / 'artifacts' / 'test-run.joblib')
    return tmp_path


@pytest.fixture
def client(project):
    return create_app(project).test_client()


def test_history_and_health(client):
    assert client.get('/').status_code == 200
    assert client.get('/static/app.js').status_code == 200
    assert client.get('/api/health').json['run_id'] == 'test-run'
    assert len(client.get('/api/machines').json) == 1
    history = client.get('/api/machines/train-001').json['history']
    assert [r['cycle'] for r in history] == list(range(1, 13))
    assert history[-1]['actual_rul'] == 0
    assert client.get('/api/machines/not-found').status_code == 404


def test_actual_inference(client):
    readings = [{'cycle': c, **{s: float(c) for s in SENSORS}} for c in range(4, 14)]
    response = client.post('/api/predict', json={'readings': readings})
    assert response.status_code == 200
    assert response.json['predicted_rul'] == 25
    assert response.json['warning'] is True
    assert response.json['cycle'] == 13


@pytest.mark.parametrize('payload', [None, {}, {'readings': []}, {'readings': [{'cycle': 1}]},
    {'readings': [{'cycle': 2, **{s: 1 for s in SENSORS}}]},
    {'readings': [{'cycle': True, **{s: 1 for s in SENSORS}}]},
    {'readings': [{'cycle': 1, **{s: '1' for s in SENSORS}}]},
    {'readings': [{'cycle': 1, **{s: 1 for s in SENSORS}, 'actual_rul': 10}]},
])
def test_bad_prediction_requests(client, payload):
    assert client.post('/api/predict', json=payload).status_code == 400


def test_nonfinite_values_rejected(client):
    payload = {'readings': [{'cycle': 1, **{s: float('nan') for s in SENSORS}}]}
    assert client.post('/api/predict', data=json.dumps(payload), content_type='application/json').status_code == 400


def test_database_constraints_and_rollback(project):
    path = project / 'data' / 'machinewatch.db'
    with pytest.raises(sqlite3.IntegrityError):
        with connect(path) as db:
            db.execute("INSERT INTO machines VALUES ('rolled-back', 'test', 10)")
            db.execute("INSERT INTO predictions VALUES ('test-run', 'unknown', 1, 25, 1)")
    with connect(path) as db:
        assert db.execute("SELECT * FROM machines WHERE machine_id='rolled-back'").fetchone() is None


def test_warning_metrics_distinguish_false_and_missed_alerts():
    frame = pd.DataFrame({'machine_id': ['a'] * 4 + ['b'] * 4, 'cycle': [1, 2, 3, 4] * 2,
                          'actual_rul': [40, 20, 10, 0] * 2})
    result = warning_summary(frame, np.array([25, 25, 10, 0, 50, 45, 40, 0]))
    assert result['engines_without_timely_warning'] == 1
    assert result['engines_with_early_false_warning'] == 1
    assert result['median_timely_warning_cycles'] == 20
    result = scores([40, 20], np.array([40, 40]))
    assert result['warning_recall'] == 0
