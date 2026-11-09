import argparse
import csv
import math
import sys
from pathlib import Path
from .core import read_csv, analyze
from .report import write_report


def main(argv=None):
    parser = argparse.ArgumentParser(description='Trace Lens: offline CSV signal notebook')
    commands = parser.add_subparsers(dest='command', required=True)
    sample = commands.add_parser('sample', help='Write deterministic sample CSV (new file only)')
    sample.add_argument('path', type=Path)
    report = commands.add_parser('report', help='Analyze CSV and create a new report directory')
    report.add_argument('csv', type=Path)
    report.add_argument('--x', required=True, help='Numeric x/time column')
    report.add_argument('--columns', nargs='+', help='Signal columns; default: all except x')
    report.add_argument('--baseline', nargs=2, type=float, metavar=('START', 'END'))
    report.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'sample':
            with args.path.open('x', newline='', encoding='utf-8') as stream:
                writer = csv.writer(stream)
                writer.writerow(['time_s', 'sensor_a', 'sensor_b'])
                for i in range(101):
                    t = i / 10
                    writer.writerow([f'{t:.1f}', '' if i == 33 else f'{2 + math.sin(t):.6f}',
                                     'invalid' if i == 65 else f'{0.2*t + math.cos(t):.6f}'])
            print(f'Sample: {args.path}')
        else:
            result, traces = analyze(read_csv(args.csv, args.x, args.columns), args.baseline)
            write_report(args.out, result, traces)
            for issue in result['diagnostics']:
                print(f'warning: line={issue["line"]} column={issue["column"]!r} {issue["reason"]}', file=sys.stderr)
            print(f'Report: {args.out / "report.html"}')
        return 0
    except (OSError, ValueError, csv.Error) as error:
        print(f'error: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
