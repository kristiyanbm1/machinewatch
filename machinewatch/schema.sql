PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS machines (
    machine_id TEXT PRIMARY KEY,
    split TEXT NOT NULL CHECK (split IN ('train','validation','test','official')),
    cycles INTEGER NOT NULL CHECK (cycles > 0)
);
CREATE TABLE IF NOT EXISTS readings (
    machine_id TEXT NOT NULL REFERENCES machines(machine_id),
    cycle INTEGER NOT NULL,
    sensor_2 REAL, sensor_3 REAL, sensor_4 REAL, sensor_7 REAL,
    sensor_8 REAL, sensor_9 REAL, sensor_11 REAL, sensor_12 REAL,
    sensor_13 REAL, sensor_14 REAL, sensor_15 REAL, sensor_17 REAL,
    sensor_20 REAL, sensor_21 REAL,
    actual_rul REAL NOT NULL CHECK (actual_rul >= 0),
    PRIMARY KEY (machine_id, cycle)
);
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    model_name TEXT NOT NULL,
    report_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS predictions (
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    machine_id TEXT NOT NULL,
    cycle INTEGER NOT NULL,
    predicted_rul REAL NOT NULL CHECK (predicted_rul >= 0),
    warning INTEGER NOT NULL CHECK (warning IN (0,1)),
    PRIMARY KEY (run_id, machine_id, cycle),
    FOREIGN KEY (machine_id, cycle) REFERENCES readings(machine_id, cycle)
);
