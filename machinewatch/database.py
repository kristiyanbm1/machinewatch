"""SQLite is the source for dashboard history and saved model runs."""
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
from .features import SENSORS


@contextmanager
def connect(path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    try:
        with db:
            yield db
    finally:
        db.close()


def save_run(path, frame, predictions, report):
    if len(frame) != len(predictions):
        raise ValueError('Each reading needs exactly one prediction')
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as db:
        db.executescript(Path(__file__).with_name('schema.sql').read_text())
        # The input dataset is fixed. Reruns retain earlier model results.
        for machine_id, group in frame.groupby('machine_id'):
            db.execute('INSERT OR IGNORE INTO machines VALUES (?,?,?)',
                       (machine_id, group['split'].iloc[0], int(group.cycle.max())))
        columns = ['machine_id', 'cycle'] + SENSORS + ['actual_rul']
        placeholders = ','.join('?' for _ in columns)
        db.executemany(f'INSERT OR IGNORE INTO readings VALUES ({placeholders})',
                       frame[columns].itertuples(index=False, name=None))
        db.execute('INSERT INTO runs VALUES (?,?,?,?)',
                   (report['run_id'], report['created_at'], report['selected_model'], json.dumps(report)))
        records = [(report['run_id'], row.machine_id, int(row.cycle), float(value), int(value <= 30))
                   for row, value in zip(frame.itertuples(), predictions)]
        db.executemany('INSERT INTO predictions VALUES (?,?,?,?,?)', records)


def latest_run(db):
    row = db.execute('SELECT * FROM runs ORDER BY created_at DESC, rowid DESC LIMIT 1').fetchone()
    if row is None:
        raise ValueError('No trained model. Run python -m machinewatch prepare first.')
    return dict(row)
