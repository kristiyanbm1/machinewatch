import numpy as np
import pandas as pd
import pytest
from machinewatch.data import COLUMNS, read_readings, load_dataset


def write_file(path, engines=5):
    rows = [[engine, cycle] + [1.0] * 24 for engine in range(1, engines + 1) for cycle in range(1, 4)]
    pd.DataFrame(rows).to_csv(path, header=False, index=False, sep=' ')


def test_labels_for_full_and_truncated_histories(tmp_path):
    write_file(tmp_path / 'train_FD001.txt')
    write_file(tmp_path / 'test_FD001.txt')
    (tmp_path / 'RUL_FD001.txt').write_text('10\n20\n30\n40\n50\n')
    frame = load_dataset(tmp_path)
    assert frame[frame.machine_id == 'train-001'].actual_rul.tolist() == [2, 1, 0]
    assert frame[frame.machine_id == 'official-001'].actual_rul.tolist() == [12, 11, 10]
    assert set(frame[frame.split == 'official'].machine_id).isdisjoint(set(frame[frame.split != 'official'].machine_id))


@pytest.mark.parametrize('kind', ['duplicate', 'gap', 'nonfinite', 'fractional', 'negative'])
def test_invalid_data_is_rejected(tmp_path, kind):
    path = tmp_path / 'readings.txt'
    write_file(path)
    frame = pd.read_csv(path, sep=r'\s+', header=None)
    if kind == 'duplicate': frame = pd.concat([frame, frame.iloc[[0]]])
    if kind == 'gap': frame = frame.drop(1)
    if kind == 'nonfinite': frame.loc[0, 2] = np.inf
    if kind == 'fractional': frame[0] = frame[0].astype(float); frame.loc[0, 0] = 1.5
    if kind == 'negative': frame.loc[0, 1] = -1
    frame.to_csv(path, header=False, index=False, sep=' ')
    with pytest.raises(ValueError): read_readings(path)


def test_modified_cached_file_is_rejected(tmp_path):
    from machinewatch.data import verify_files
    (tmp_path / 'train_FD001.txt').write_text('changed data')
    with pytest.raises(ValueError, match='differs from the verified'):
        verify_files(tmp_path)
