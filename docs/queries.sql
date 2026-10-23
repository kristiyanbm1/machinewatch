-- Open the database: sqlite3 data/machinewatch.db
-- How many engines belong to each split?
SELECT split, COUNT(*) AS engines FROM machines GROUP BY split;

-- Mean error per held-out engine for the most recent training run.
SELECT m.machine_id,
       ROUND(AVG(ABS(p.predicted_rul - r.actual_rul)), 2) AS mae_cycles
FROM machines m
JOIN readings r ON r.machine_id = m.machine_id
JOIN predictions p ON p.machine_id = r.machine_id AND p.cycle = r.cycle
WHERE m.split = 'test'
  AND p.run_id = (SELECT run_id FROM runs ORDER BY created_at DESC, rowid DESC LIMIT 1)
GROUP BY m.machine_id
ORDER BY mae_cycles DESC;

-- First warning in each held-out history (NULL means no warning).
SELECT m.machine_id, MIN(CASE WHEN p.warning = 1 THEN p.cycle END) AS first_warning_cycle
FROM machines m
JOIN predictions p ON p.machine_id = m.machine_id
WHERE m.split = 'test'
  AND p.run_id = (SELECT run_id FROM runs ORDER BY created_at DESC, rowid DESC LIMIT 1)
GROUP BY m.machine_id;

-- A trailing sensor average, expressed with a SQL window function.
SELECT machine_id, cycle, sensor_4,
       AVG(sensor_4) OVER (
           PARTITION BY machine_id ORDER BY cycle ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
       ) AS sensor_4_mean10
FROM readings
WHERE machine_id = (SELECT MIN(machine_id) FROM machines WHERE split = 'test')
ORDER BY cycle;
