# Technical overview

## 1. Data format

One row describes one engine at one operating cycle. It has an engine number,
a cycle number, three operating settings and 21 sensor values. We keep 14 varying
sensor channels for this FD001 experiment. The dashboard uses channel numbers
instead of inventing physical units or interpreting them as real-world limits.

An engine ending at cycle 180 has 20 cycles left when it reaches cycle 160. That
20 is the training label. We know it because the historical experiment has ended.
A running machine would not give us that number.

## 2. Engine-based splits

Consecutive readings from the same engine look similar. If cycle 160 is in the
training set and cycle 161 is in the test set, the test is partly checking whether
the model remembers that engine. Holding out whole engines asks a better question:
can it make useful estimates on an engine it has not seen?

The split is 60/20/20 engines. Training fits the models; validation selects one;
test measures the selected approach. An additional official test set checks one
last-cycle prediction per engine. It is reported separately because it answers a
different question from full-life replay.

## 3. Sensor features

A single reading can be noisy. A trailing average summarizes the last ten readings.
A five-cycle change shows whether a sensor is moving up or down.

At cycle 20, a mean uses cycles 11 through 20, never 21. At the beginning of an
engine history, it uses the readings available so far. For a five-cycle change
with fewer than five past readings, we compare against that engine's first reading.

There are 43 features: cycle number plus 14 current values, 14 averages and 14
changes. `model_input()` uses an explicit list, so a new label column cannot
accidentally become a feature. The tests check this behavior.

## 4. Models

**Median baseline:** always predicts the median remaining life in the training
rows. It ignores sensors. If a complicated model cannot beat this, something is wrong.

**Ridge regression:** fits a weighted sum of the features. Ridge discourages very
large weights. StandardScaler puts features on comparable scales and learns its
means and scales from training data only, through a scikit-learn Pipeline.

**Random forest:** trains many decision trees and averages their predictions.
Each tree uses different samples and makes a sequence of splits on feature values.
The trees have limited depth and a minimum leaf size to reduce overfitting.

## 5. Evaluation

MAE is the average absolute difference between the prediction and the known
remaining life. An MAE of 20 cycles does **not** mean every prediction is within
20 cycles. RMSE gives more weight to large errors.

A warning means predicted remaining life is at most 30 cycles. Precision asks
how many flagged cycles really had at most 30 left. Recall asks how many cycles
in that region were flagged. A model that never warns gets zero warning recall.

We also summarize each held-out engine: did it get a warning with 1–30 cycles
left, and did it get any false warnings earlier than that? The median useful
warning time excludes missed engines, so it must be read alongside the missed count.
One warning is enough in this version; requiring several consecutive warnings
would be a sensible next experiment.

## 6. Database

`machines` contains one row per engine and its split. `readings` contains the
sensor history. `runs` records which model was selected and how it performed.
`predictions` links a model run to each engine/cycle estimate.

The pair `(machine_id, cycle)` identifies a reading. A foreign key stops a
prediction from referring to a reading that does not exist. Saving happens in a
transaction so a failed write does not leave half a training run in the database.

The dashboard gets its history using a JOIN, not by retraining a model every time
a page opens. `docs/queries.sql` contains aggregates, joins and
a rolling SQL window calculation.

## 7. Prediction requests

The browser uses GET requests to fetch stored results. Separately, POST
`/api/predict` accepts consecutive sensor readings, validates them, calculates
the same features used during training and predicts for the last row.

A request needs ten recent readings, or a shorter history that starts at cycle 1.
That ensures rolling features match the offline pipeline. A test compares prefix
features with features calculated from a full history to detect future-data leakage.

The server measures prediction processing time and returns it with the result.
It binds to localhost and has no debug console enabled. It is deliberately a
small local app, not a deployment platform.
