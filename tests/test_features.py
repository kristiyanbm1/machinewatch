import pandas as pd
from pandas.testing import assert_frame_equal

from machinewatch.features import SENSORS, FEATURES, make_features, model_input
from machinewatch.data import split_engines


def history():
    return pd.DataFrame([{'machine_id': machine, 'cycle': cycle,
                          **{sensor: offset + cycle for sensor in SENSORS}}
                         for machine, offset in [('a', 0), ('b', 100)] for cycle in range(1, 16)])


def test_future_readings_cannot_change_past_features():
    frame = history()
    full = make_features(frame)
    prefix = make_features(frame[frame.cycle <= 10])
    assert_frame_equal(full[full.cycle <= 10], prefix)
    changed = frame.copy()
    changed.loc[changed.cycle > 10, SENSORS] = 99999
    assert_frame_equal(full[full.cycle <= 10], make_features(changed).query('cycle <= 10'))


def test_rolling_features_stay_within_each_engine():
    frame = make_features(history())
    first_b = frame[(frame.machine_id == 'b') & (frame.cycle == 1)].iloc[0]
    assert first_b.sensor_2_mean10 == 101
    assert first_b.sensor_2_change5 == 0
    tenth_a = frame[(frame.machine_id == 'a') & (frame.cycle == 10)].iloc[0]
    assert tenth_a.sensor_2_mean10 == 5.5
    assert tenth_a.sensor_2_change5 == 5


def test_labels_and_ids_are_excluded():
    frame = make_features(history().assign(actual_rul=55, split='test'))
    assert model_input(frame).columns.tolist() == FEATURES
    assert not {'actual_rul', 'machine_id', 'split'} & set(FEATURES)


def test_split_is_deterministic_disjoint_and_engine_based():
    mapping = split_engines(range(1, 101))
    assert mapping == split_engines(list(range(100, 0, -1)) * 3)
    assert [list(mapping.values()).count(s) for s in ['train', 'validation', 'test']] == [60, 20, 20]
    assert set(mapping) == set(range(1, 101))


def test_ten_reading_request_matches_full_history_features():
    frame = history()
    full = make_features(frame[frame.machine_id == 'a'])
    recent = make_features(frame[(frame.machine_id == 'a') & (frame.cycle >= 6)])
    assert_frame_equal(model_input(full.tail(1)), model_input(recent.tail(1)))
