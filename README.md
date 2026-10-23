# MachineWatch

A small predictive-maintenance app built with Python, SQLite and scikit-learn.
It estimates how many operating cycles an engine has left, then shows the estimate
alongside recorded sensor readings in a local dashboard.

The question is simple: **can recent sensor trends give a useful warning before failure?**

This version uses NASA's C-MAPSS FD001 dataset. The engines and sensor readings
come from a simulation, not a live factory or aircraft. A cycle is a unit of
operation in the dataset; it is not an hour or a day.

## Run it

On macOS/Linux, `./start.command` handles setup and starts the app. The manual
commands below do the same thing and make each step explicit.

Use **Python 3.13**. Run these commands from this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m machinewatch prepare
python -m machinewatch serve
```

On Windows, activate with `.venv\Scripts\activate` instead.

Open **http://127.0.0.1:8000** in your browser. Stop the server with `Ctrl+C`.
If that port is busy, use `python -m machinewatch serve --port 8001`.

The first preparation downloads about 12 MB, trains three small models and saves
the database, model and reports. Internet access is needed for the download and
package installation. The app then runs locally without an API key or paid service.

If the NASA download is temporarily unavailable, download `CMAPSSData.zip` from
the [NASA dataset page](https://data.nasa.gov/dataset/cmapss-jet-engine-simulated-data), then run:

```bash
python -m machinewatch prepare --archive /path/to/CMAPSSData.zip
```

An existing prepared copy can go straight to `python -m machinewatch serve`.
Preparation can be repeated; earlier training runs remain in the database.

## Try the demo

1. Select a held-out engine. These engines were not used for fitting or selection.
2. Click **Play history**, or move the cycle slider.
3. Watch the predicted number of remaining cycles change.
4. Enable **Show actual remaining life** to compare the estimate with the outcome.
5. Compare the three models in the table below the charts.

A warning appears when the estimate is **30 cycles or fewer**. This is a fixed
rule on a regression prediction, not a failure probability. The dashboard replays
saved predictions; the API can also calculate a fresh prediction from sensor history.

![Held-out engine example](reports/example-engine.png)

[Dashboard screenshot](reports/dashboard.jpg)

## What is inside

- **Data pipeline:** checks file shape, cycle order, missing values and duplicate readings.
- **Features:** the current sensor values, trailing 10-cycle averages and 5-cycle changes.
- **Models:** a training-label median, ridge regression and a random forest.
- **SQL database:** engines, readings, training runs and per-cycle predictions.
- **Flask API:** stored history, model results and a prediction endpoint.
- **Dashboard:** engine selection, replay controls, sensor charts and model comparison.
- **Tests:** future-data leakage, engine separation, labels, input validation and SQL constraints.

## How the experiment works

The 100 complete engine histories are divided into 60 training engines, 20
validation engines and 20 test engines using seed 42. All readings from an engine
stay together. Separately, the official test file supplies another 100 truncated
histories and their true remaining-life labels.

For a complete history, the target is:

```text
remaining cycles = final recorded cycle - current cycle
```

For an official test history, the supplied remaining-life value is added to that
formula. Labels are used for training and evaluation only. Engine identity, final
cycle and remaining life are excluded from the feature input.

The model with the lowest validation mean absolute error (MAE) is selected.
Models are not refitted on validation data. Test results do not choose the model.
The report includes full-history test metrics and a separate evaluation at the
last recorded cycle of each official test engine.

Read the [actual experiment results](reports/results.md) for errors, warning
precision/recall and missed warnings. The complete numbers and split IDs are in
[metrics.json](reports/metrics.json).

## Test it

```bash
python -m pytest -q
```

The direct dependencies are pinned in `requirements.txt`. `requirements-lock.txt`
records all package versions from the tested Python 3.13 environment. For the
closest reproduction, install with `pip install -r requirements-lock.txt`.

Tests use small artificial fixtures and do not download NASA data. The GitHub
Actions workflow runs the same tests when you upload the project.

## Project structure

| File | Responsibility |
| --- | --- |
| `machinewatch/data.py` | Download, validation, splits and labels |
| `machinewatch/features.py` | Current and past-only sensor features |
| `machinewatch/train.py` | Fit, compare and evaluate models |
| `machinewatch/schema.sql` | Database tables and relationships |
| `machinewatch/database.py` | Save experiment history |
| `machinewatch/app.py` | HTTP API |
| `machinewatch/static/` | Plain HTML, CSS and JavaScript dashboard |
| `machinewatch/__main__.py` | The `prepare` and `serve` commands |

Documentation: [technical overview](docs/walkthrough.md),
[SQL examples](docs/queries.sql), and [API reference](docs/api.md).

## Limits

- FD001 has one operating condition and one simulated fault mode. Results do not
  show that the model would work on a different machine or real sensor data.
- Healthy engines can look similar despite having different lifetimes. Early-life
  remaining-life estimates can therefore be quite inaccurate.
- A warning threshold of 30 cycles is a demonstration choice, not an optimized
  maintenance policy. Predictions have no calibrated confidence interval.
- Cycles within one engine are correlated. Per-cycle metrics are not thousands
  of independent trials, and longer histories receive more weight.
- The app is a local prototype. It does not connect to equipment, schedule
  maintenance, stream live readings or provide production authentication.
- Training artifacts use joblib. Only load the files generated by your own local run.

## Data and attribution

A. Saxena and K. Goebel (2008), *Turbofan Engine Degradation Simulation Data Set*,
NASA Ames Prognostics Data Repository.

- [NASA repository and citation](https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/)
- [Dataset description and download](https://data.nasa.gov/dataset/cmapss-jet-engine-simulated-data)
- [Data notes](docs/data.md)

The NASA catalog lists the license as unspecified. Raw data and trained artifacts
are excluded from the source archive and Git tracking; preparation downloads the
data from the original source. No separate license for the dataset is claimed here.

## Uploading to GitHub

Upload the source files, tests, docs and reports. Keep `data/`, `artifacts/`, `.venv/`
and Python caches out of the repository; `.gitignore` already lists them.
