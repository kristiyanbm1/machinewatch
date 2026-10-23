"""Features available at the current cycle. Future readings are never used."""
import pandas as pd

# These channels vary in FD001; the others are constant or nearly constant.
SENSORS = [f'sensor_{i}' for i in [2, 3, 4, 7, 8, 9, 11, 12, 13, 14, 15, 17, 20, 21]]
FEATURES = ['cycle'] + SENSORS + [f'{s}_mean10' for s in SENSORS] + [f'{s}_change5' for s in SENSORS]


def make_features(readings):
    frame = readings.sort_values(['machine_id', 'cycle']).copy()
    groups = frame.groupby('machine_id', sort=False)
    for sensor in SENSORS:
        frame[f'{sensor}_mean10'] = groups[sensor].transform(
            lambda values: values.rolling(10, min_periods=1).mean())
        # At the start of a history, compare with its first available reading.
        previous = groups[sensor].shift(5).fillna(groups[sensor].transform('first'))
        frame[f'{sensor}_change5'] = frame[sensor] - previous
    return frame


def model_input(frame):
    """An explicit allowlist keeps labels and engine identities out of the model."""
    return frame[FEATURES]
