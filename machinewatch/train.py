"""Compare simple models using entirely separate engines for each split."""
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

import joblib
import numpy as np
import sklearn
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, precision_score, recall_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .database import save_run
from .features import make_features, model_input, FEATURES


def scores(actual, predicted):
    return {
        'mae': round(float(mean_absolute_error(actual, predicted)), 3),
        'rmse': round(float(np.sqrt(mean_squared_error(actual, predicted))), 3),
        'warning_precision': round(float(precision_score(np.asarray(actual) <= 30, predicted <= 30, zero_division=0)), 3),
        'warning_recall': round(float(recall_score(np.asarray(actual) <= 30, predicted <= 30, zero_division=0)), 3),
        'rows': len(actual),
    }


def warning_summary(frame, predicted):
    frame = frame.copy()
    frame['predicted_rul'] = predicted
    lead_times, missed, premature = [], 0, 0
    for _, engine in frame.groupby('machine_id'):
        warnings = engine[engine.predicted_rul <= 30].sort_values('cycle')
        # Count warnings before failure, not a warning first raised at failure.
        timely = warnings[(warnings.actual_rul > 0) & (warnings.actual_rul <= 30)]
        if timely.empty:
            missed += 1
        else:
            lead_times.append(int(timely.iloc[0].actual_rul))
        if (warnings.actual_rul > 30).any():
            premature += 1
    return {'engines': frame.machine_id.nunique(), 'engines_without_timely_warning': missed,
            'engines_with_early_false_warning': premature,
            'median_timely_warning_cycles': float(np.median(lead_times)) if lead_times else None}


def train(readings, output, dataset_hash):
    output = Path(output)
    artifacts = output / 'artifacts'
    reports = output / 'reports'
    artifacts.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    frame = make_features(readings).reset_index(drop=True)
    training = frame[frame.split == 'train']
    validation = frame[frame.split == 'validation']
    models = {
        'median_baseline': DummyRegressor(strategy='median'),
        'ridge': make_pipeline(StandardScaler(), Ridge(alpha=10)),
        'random_forest': RandomForestRegressor(n_estimators=100, max_depth=12,
                                               min_samples_leaf=5, random_state=42, n_jobs=2),
    }
    validation_scores = {}
    for name, model in models.items():
        print(f'Training {name}...', flush=True)
        model.fit(model_input(training), training.actual_rul)
        predicted = np.maximum(0, model.predict(model_input(validation)))
        validation_scores[name] = scores(validation.actual_rul, predicted)
    selected = min(validation_scores, key=lambda name: validation_scores[name]['mae'])
    report = {
        'run_id': uuid.uuid4().hex[:12], 'created_at': datetime.now(timezone.utc).isoformat(),
        'dataset': 'NASA C-MAPSS FD001', 'archive_sha256': dataset_hash,
        'sklearn_version': sklearn.__version__, 'seed': 42, 'warning_threshold': 30,
        'selected_model': selected, 'selection_rule': 'Lowest validation MAE; no refitting on validation data.',
        'validation': validation_scores, 'test': {}, 'official_last_cycle': {},
        'split_engines': {split: sorted(group.machine_id.unique().tolist()) for split, group in frame.groupby('split')},
        'features': FEATURES,
    }
    test = frame[frame.split == 'test']
    official = frame[frame.split == 'official'].groupby('machine_id').tail(1)
    for name, model in models.items():
        report['test'][name] = scores(test.actual_rul, np.maximum(0, model.predict(model_input(test))))
        report['official_last_cycle'][name] = scores(official.actual_rul, np.maximum(0, model.predict(model_input(official))))
    model = models[selected]
    predicted = np.maximum(0, model.predict(model_input(frame)))
    report['test_warnings'] = warning_summary(test, predicted[test.index])
    # Version each model file so a failed rerun cannot overwrite an earlier model.
    joblib.dump({'model': model, 'features': FEATURES, 'run_id': report['run_id']},
                artifacts / f'{report["run_id"]}.joblib')
    save_run(output / 'data' / 'machinewatch.db', frame, predicted, report)
    (reports / 'metrics.json').write_text(json.dumps(report, indent=2) + '\n')
    write_report(report, reports)
    plot_example(test, predicted[test.index], reports)
    return report


def write_report(report, folder):
    lines = ['# Model results', '', f'Selected model: **{report["selected_model"]}** (lowest validation MAE).', '',
             'MAE and RMSE are measured in operating cycles. Lower is better.',
             'Warning precision and recall use a fixed threshold of 30 remaining cycles.', '',
             '| Evaluation | Model | MAE | RMSE | Warning precision | Warning recall |',
             '| --- | --- | ---: | ---: | ---: | ---: |']
    for split in ['validation', 'test', 'official_last_cycle']:
        for name, values in report[split].items():
            lines.append(f'| {split} | {name} | {values["mae"]} | {values["rmse"]} | {values["warning_precision"]} | {values["warning_recall"]} |')
    lines += ['', '## How to read these numbers', '',
              '- Train, validation and test contain 60, 20 and 20 separate run-to-failure engines.',
              '- The official evaluation uses only the last observed cycle of each of 100 additional engines.',
              '- Full-history scores weight each cycle equally, so longer histories have more influence.',
              '- No target capping is used. These scores are not directly comparable to capped-RUL benchmarks.',
              '- Predictions are clipped at zero. Warning scores measure individual cycles, not independent events.',
              '- Model selection uses validation only; test results are descriptive, not tuning feedback.',
              '- This is simulated data under one operating condition. It does not establish real-machine accuracy.',
              '', '## Warnings on the 20 held-out full histories', '',
              'A timely warning is one raised while 1–30 cycles remain. A warning with more than 30 cycles remaining is counted as an early false warning.', '',
              '```json', json.dumps(report['test_warnings'], indent=2), '```', '',
              'The median warning time excludes engines without a timely warning; read it alongside the missed-engine count.', '',
              '![Example held-out engine](example-engine.png)', '',
              'The example is the alphabetically first held-out engine, chosen without inspecting its prediction error.', '',
              f'Run: `{report["run_id"]}`. Library version: scikit-learn `{report["sklearn_version"]}`.',
              f'Dataset archive SHA-256: `{report["archive_sha256"]}`.', '']
    (folder / 'results.md').write_text('\n'.join(lines))


def plot_example(test, predicted, folder):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    example = test.assign(predicted=predicted)
    example = example[example.machine_id == sorted(example.machine_id.unique())[0]]
    fig, ax = plt.subplots(figsize=(10, 4.3))
    ax.plot(example.cycle, example.actual_rul, label='Actual remaining cycles', color='#929aa5')
    ax.plot(example.cycle, example.predicted, label='Predicted remaining cycles', color='#167d74')
    ax.axhline(30, color='#b86b15', linestyle='--', label='Warning threshold')
    ax.set(title=f'Held-out engine: {example.machine_id.iloc[0]}', xlabel='Operating cycle', ylabel='Remaining cycles')
    ax.legend(frameon=False)
    ax.grid(alpha=.15)
    fig.tight_layout()
    fig.savefig(folder / 'example-engine.png', dpi=150)
    plt.close(fig)
