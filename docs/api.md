# Local API

Start with `python -m machinewatch serve`. The default address is
`http://127.0.0.1:8000`.

| Method | Path | Response |
| --- | --- | --- |
| GET | `/api/health` | Status, model name and run ID |
| GET | `/api/summary` | Full evaluation report |
| GET | `/api/machines` | Held-out full-history engines |
| GET | `/api/machines/<machine_id>` | Sensor history and stored predictions |
| POST | `/api/predict` | Fresh prediction for the last submitted cycle |

## Send a real example from the local database

Run this Python snippet from the project directory while the server is running:

```python
import json
import sqlite3
from urllib.request import Request, urlopen
from machinewatch.features import SENSORS

with sqlite3.connect('data/machinewatch.db') as db:
    db.row_factory = sqlite3.Row
    machine = db.execute("SELECT MIN(machine_id) FROM machines WHERE split='test'").fetchone()[0]
    columns = ', '.join(['cycle'] + SENSORS)
    rows = db.execute(
        f'SELECT {columns} FROM readings WHERE machine_id=? AND cycle<=10 ORDER BY cycle',
        (machine,),
    ).fetchall()
    payload = {'readings': [dict(row) for row in rows]}

request = Request(
    'http://127.0.0.1:8000/api/predict',
    data=json.dumps(payload).encode(),
    headers={'Content-Type': 'application/json'},
)
with urlopen(request) as response:
    print(json.load(response))
```

Each reading needs `cycle` and these channels:
`sensor_2`, `sensor_3`, `sensor_4`, `sensor_7`, `sensor_8`, `sensor_9`,
`sensor_11`, `sensor_12`, `sensor_13`, `sensor_14`, `sensor_15`, `sensor_17`,
`sensor_20`, `sensor_21`.

Send 10–1000 consecutive readings in ascending order for one engine. A shorter
history is accepted only if it starts at cycle 1. Extra fields, gaps, nonfinite
numbers and strings are rejected with HTTP 400. Requests above 1 MB get HTTP 413.

The response contains `cycle`, `predicted_rul`, `warning`, `run_id` and
`inference_ms`. Inference time includes feature preparation but not network time.
Predictions submitted through this endpoint are not written into the experiment
history. The database retains the reproducible offline experiment only.

Keep the server local. The built-in Flask server is intended for this demo;
a public deployment would need a separate production and authentication design.
