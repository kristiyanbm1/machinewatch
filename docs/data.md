# Dataset notes

Source: NASA C-MAPSS FD001, from
https://data.nasa.gov/docs/legacy/CMAPSSData.zip

The source describes simulated turbofan degradation with one operating condition
and one fault mode (high-pressure compressor degradation). It has 100 full
training histories and 100 truncated test histories. There are 21 sensor columns;
the total of 26 includes engine ID, cycle and three operating settings.

Files used:

- `train_FD001.txt`: full histories ending at failure.
- `test_FD001.txt`: histories ending before failure.
- `RUL_FD001.txt`: remaining cycles after the last observed test cycle, in engine-ID order.

The internal `train`, `validation` and `test` groups all come from the full-history
file. The prefix `official-` refers only to the separate NASA test file. Prefixes
prevent collisions between engine 1 in the two files.

The full archive hash is recorded in the result report. Before training, all three
raw files are checked against the SHA-256 hashes of the verified NASA download.
This prevents modified cached data from being mixed with older database readings. The downloader extracts
only the three named files. Raw data is not included in the source ZIP. The NASA
catalog says “License not specified”; this project does not relabel it as MIT or
CC0. NASA asks users to acknowledge the repository and dataset donors.

Citation: A. Saxena and K. Goebel (2008), “Turbofan Engine Degradation Simulation
Data Set”, NASA Ames Prognostics Data Repository.

Reference: A. Saxena, K. Goebel, D. Simon and N. Eklund, “Damage Propagation Modeling
for Aircraft Engine Run-to-Failure Simulation”, PHM08, Denver, 2008.

Sources checked for this project:

- https://data.nasa.gov/dataset/cmapss-jet-engine-simulated-data
- https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/

The model's performance is evidence about this particular simulated dataset.
It is not evidence that it can predict the failure of a physical engine or motor.
