import argparse
from pathlib import Path
import sys
from zipfile import BadZipFile


def main():
    parser = argparse.ArgumentParser(description='MachineWatch: a small predictive maintenance project')
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parent.parent,
                        help='Directory for data, artifacts and reports')
    commands = parser.add_subparsers(dest='command', required=True)
    prepare = commands.add_parser('prepare', help='Download data, train models and save the results')
    prepare.add_argument('--archive', type=Path, help='Use an already downloaded NASA CMAPSSData.zip')
    serve = commands.add_parser('serve', help='Open the local dashboard server')
    serve.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            from .data import download, load_dataset, verify_files
            from .train import train
            raw = args.project / 'data' / 'raw'
            if args.archive or not all((raw / name).exists() for name in ['train_FD001.txt', 'test_FD001.txt', 'RUL_FD001.txt', 'archive.sha256']):
                digest = download(raw, args.archive)
            else:
                digest = (raw / 'archive.sha256').read_text().strip()
                print('Using the existing local dataset.')
            verify_files(raw)
            report = train(load_dataset(raw), args.project, digest)
            print(f'Done. Selected model: {report["selected_model"]}')
            print(f'Results: {args.project / "reports" / "results.md"}')
            print('Start the dashboard: python -m machinewatch serve')
        else:
            if not 1 <= args.port <= 65535:
                parser.error('Port must be between 1 and 65535')
            if not (args.project / 'data' / 'machinewatch.db').exists():
                parser.error('Run python -m machinewatch prepare first.')
            from .app import create_app
            create_app(args.project).run(host='127.0.0.1', port=args.port, debug=False)
    except (OSError, ValueError, BadZipFile) as error:
        print(f'Could not complete the command: {error}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
