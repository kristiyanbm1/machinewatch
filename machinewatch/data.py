"""Download and validate the FD001 part of NASA's C-MAPSS dataset."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile
import ssl

import certifi

import numpy as np
import pandas as pd

SOURCE = 'https://data.nasa.gov/docs/legacy/CMAPSSData.zip'
COLUMNS = ['engine', 'cycle'] + [f'setting_{i}' for i in range(1, 4)] + [f'sensor_{i}' for i in range(1, 22)]
FILES = ['train_FD001.txt', 'test_FD001.txt', 'RUL_FD001.txt']
FILE_HASHES = {
    'train_FD001.txt': '963b5e22825b34d8b21c69e1aeb4af3e647050eb672ee8834ba4b5d91d2de0f8',
    'test_FD001.txt': '3cda7109ce17bafb5443f2ac926cfcf88154b941b8c4cf95eb55d1ddd6f52851',
    'RUL_FD001.txt': 'a19c8ec94931949d0485bdc35118206e9c81c4547b422efb9cf86f4ceddbceca',
}


def verify_files(folder):
    for name, expected in FILE_HASHES.items():
        if sha256((Path(folder) / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f'{name} differs from the verified NASA FD001 file. Download a fresh archive.')



def download(folder, archive=None):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    if archive:
        content = Path(archive).read_bytes()
    else:
        print('Downloading NASA C-MAPSS data (about 12 MB)...', flush=True)
        context = ssl.create_default_context(cafile=certifi.where())
        with urlopen(SOURCE, timeout=120, context=context) as response:
            content = response.read()
    with ZipFile(BytesIO(content)) as zipped:
        # Read only the three expected files, never arbitrary archive paths.
        for name in FILES:
            matches = [p for p in zipped.namelist() if Path(p).name == name]
            if len(matches) != 1:
                raise ValueError(f'Archive must contain exactly one {name}')
            (folder / name).write_bytes(zipped.read(matches[0]))
    digest = sha256(content).hexdigest()
    (folder / 'archive.sha256').write_text(digest + '\n')
    return digest


def read_readings(path):
    frame = pd.read_csv(path, sep=r'\s+', header=None)
    if frame.shape[1] != len(COLUMNS):
        raise ValueError('Expected 26 columns: engine, cycle, 3 settings, 21 sensors')
    frame.columns = COLUMNS
    if frame.empty or not np.isfinite(frame.to_numpy(dtype=float)).all():
        raise ValueError('Readings must be nonempty, numeric and finite')
    for column in ['engine', 'cycle']:
        if (frame[column] < 1).any() or (frame[column] % 1 != 0).any():
            raise ValueError('Engine and cycle numbers must be positive integers')
        frame[column] = frame[column].astype(int)
    if frame.duplicated(['engine', 'cycle']).any():
        raise ValueError('Duplicate engine/cycle pair')
    frame = frame.sort_values(['engine', 'cycle']).reset_index(drop=True)
    for _, group in frame.groupby('engine'):
        if group['cycle'].tolist() != list(range(1, len(group) + 1)):
            raise ValueError('Each engine must have consecutive cycles starting at 1')
    return frame


def split_engines(engines, seed=42):
    ids = np.array(sorted(set(engines)), dtype=int)
    if len(ids) < 5:
        raise ValueError('At least five engines are needed for separate data splits')
    np.random.default_rng(seed).shuffle(ids)
    train_end, validation_end = int(.6 * len(ids)), int(.8 * len(ids))
    return {int(engine): split for split, group in [
        ('train', ids[:train_end]), ('validation', ids[train_end:validation_end]),
        ('test', ids[validation_end:])
    ] for engine in group}


def load_dataset(folder):
    folder = Path(folder)
    train = read_readings(folder / FILES[0])
    official = read_readings(folder / FILES[1])
    rul = pd.read_csv(folder / FILES[2], sep=r'\s+', header=None).to_numpy().ravel()
    expected = list(range(1, official.engine.nunique() + 1))
    if sorted(official.engine.unique()) != expected or len(rul) != len(expected):
        raise ValueError('Official test engine IDs must match the RUL file')
    if not np.isfinite(rul).all() or (rul < 0).any() or (rul % 1 != 0).any():
        raise ValueError('Remaining-life labels must be nonnegative integers')
    splits = split_engines(train.engine)
    tables = []
    for source, frame in [('train', train), ('official', official)]:
        frame = frame.copy()
        frame['machine_id'] = frame.engine.map(lambda value: f'{source}-{value:03d}')
        frame['split'] = frame.engine.map(splits) if source == 'train' else 'official'
        final_cycle = frame.groupby('engine').cycle.transform('max')
        extra = frame.engine.map(dict(zip(expected, rul))) if source == 'official' else 0
        frame['actual_rul'] = final_cycle + extra - frame.cycle
        tables.append(frame)
    return pd.concat(tables, ignore_index=True)
