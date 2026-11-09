"""Numeric CSV parsing and deterministic, finite statistics."""
import csv
import math
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Dataset:
    x_name: str
    names: list
    rows: list
    diagnostics: list
    source: str


def read_csv(path, x, columns=None):
    diagnostics, rows = [], []
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.reader(stream, strict=True)
        header = next(reader, None)
        if not header or any(not name.strip() for name in header):
            raise ValueError('CSV must have nonempty column names')
        if len(set(header)) != len(header):
            raise ValueError('Duplicate column names are not supported')
        if x not in header:
            raise ValueError(f'Unknown x column: {x}')
        names = list(columns) if columns else [name for name in header if name != x]
        if not names or len(set(names)) != len(names) or x in names:
            raise ValueError('Choose distinct signal columns, excluding x')
        if any(name not in header for name in names):
            raise ValueError('Unknown signal column')
        indices = [header.index(name) for name in [x] + names]
        for row in reader:
            line = reader.line_num
            if len(row) != len(header):
                raise ValueError(f'Line {line}: expected {len(header)} cells, got {len(row)}')
            values = []
            for name, index in zip([x] + names, indices):
                raw = row[index].strip()
                value, reason = None, None
                if not raw:
                    reason = 'missing'
                else:
                    try:
                        value = float(raw)
                        if not math.isfinite(value):
                            value, reason = None, 'nonfinite'
                    except ValueError:
                        reason = 'invalid'
                if reason:
                    diagnostics.append({'line': line, 'column': name, 'reason': reason})
                values.append(value)
            if values[0] is None:
                diagnostics.append({'line': line, 'column': x, 'reason': 'row_excluded'})
            rows.append(values)
    if not rows:
        raise ValueError('CSV has no data rows')
    valid_x = [row[0] for row in rows if row[0] is not None]
    if any(b < a for a, b in zip(valid_x, valid_x[1:])):
        diagnostics.append({'line': None, 'column': x, 'reason': 'unsorted_x'})
    return Dataset(x, names, rows, diagnostics, str(path))


def summarize(values):
    """Population std (ddof=0). Scaling avoids intermediate sum-of-squares overflow."""
    if not values:
        return dict(count=0, min=None, max=None, mean=None, std=None, rms=None)
    scale = max(abs(v) for v in values) or 1.0
    normalized = [v / scale for v in values]
    mean = math.fsum(normalized) / len(values)
    std = math.sqrt(math.fsum((v - mean) ** 2 for v in normalized) / len(values))
    rms = math.sqrt(math.fsum(v * v for v in normalized) / len(values))
    return dict(count=len(values), min=min(values), max=max(values),
                mean=mean * scale, std=std * scale, rms=rms * scale)


def analyze(data, baseline=None):
    if baseline is not None:
        start, stop = baseline
        if not all(math.isfinite(v) for v in baseline) or start > stop:
            raise ValueError('Baseline must be a finite ordered interval')
    traces, stats = {}, {}
    for index, name in enumerate(data.names, 1):
        offset = 0.0
        if baseline is not None:
            base = [row[index] for row in data.rows if row[0] is not None
                    and baseline[0] <= row[0] <= baseline[1] and row[index] is not None]
            if not base:
                raise ValueError(f'No usable baseline samples for {name}')
            offset = summarize(base)['mean']
        points = [(row[0], None if row[index] is None else row[index] - offset)
                  if row[0] is not None else (None, None) for row in data.rows]
        if any(y is not None and not math.isfinite(y) for _, y in points):
            raise ValueError(f'Baseline subtraction overflow for {name}')
        values = [y for x, y in points if x is not None and y is not None]
        traces[name] = points
        stats[name] = dict(summarize(values), baseline_offset=offset,
                           excluded=len(data.rows) - len(values))
    return {'source': data.source, 'x_column': data.x_name,
            'baseline_interval': baseline, 'std_definition': 'population (ddof=0)',
            'total_rows': len(data.rows), 'columns': stats,
            'diagnostics': data.diagnostics}, traces
