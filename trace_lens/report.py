"""Offline SVG and HTML rendering. All data labels are escaped."""
import html
import json
from pathlib import Path


def esc(value):
    return html.escape(str(value), quote=True)


def plot_svg(name, x_name, points):
    valid = [(x, y) for x, y in points if x is not None and y is not None]
    opening = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 280" '
               'role="img" aria-label="' + esc(name) + '"><rect width="900" height="280" fill="#102329"/>')
    if not valid:
        return opening + '<text x="40" y="140" fill="#edf4ee">No usable samples</text></svg>'
    xs, ys = zip(*valid)
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    # Normalize first so subtracting opposite-sign large values cannot overflow.
    def pos(v, low, high, start, span):
        scale = max(abs(low), abs(high)) or 1
        extent = high / scale - low / scale
        return start + (0.5 if extent == 0 else (v / scale - low / scale) / extent) * span
    paths, current, dots = [], [], []
    for x, y in points + [(None, None)]:
        if x is None or y is None:
            if current:
                paths.append(' '.join(current))
            current = []
        else:
            px, py = pos(x, xmin, xmax, 75, 790), pos(y, ymin, ymax, 225, -165)
            current.append(('M' if not current else 'L') + f'{px:.3f},{py:.3f}')
            dots.append(f'<circle cx="{px:.3f}" cy="{py:.3f}" r="2" fill="#edc763"/>')
    content = ''.join(f'<path d="{p}" fill="none" stroke="#62dfc4" stroke-width="2"/>' for p in paths)
    content += ''.join(dots)
    content += f'<text x="24" y="30" fill="#edf4ee" font-size="18">{esc(name)}</text>'
    content += f'<text x="75" y="260" fill="#b5ccc6">{esc(x_name)}: {xmin:.5g} → {xmax:.5g}</text>'
    content += f'<text x="450" y="260" fill="#b5ccc6">value: {ymin:.5g} → {ymax:.5g}</text>'
    return opening + content + '</svg>'


def write_report(directory, result, traces):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    cards = []
    for index, (name, points) in enumerate(traces.items(), 1):
        svg = plot_svg(name, result['x_column'], points)
        (directory / f'trace-{index:03d}.svg').write_text(svg, encoding='utf-8')
        cells = ''.join(f'<li><b>{esc(key)}</b> {esc(value)}</li>' for key, value in result['columns'][name].items())
        cards.append(f'<section><h2>{esc(name)}</h2>{svg}<ul>{cells}</ul></section>')
    issues = ''.join(f'<li>Line {esc(d["line"])} · {esc(d["column"])} · {esc(d["reason"])}</li>' for d in result['diagnostics'])
    document = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Trace Lens · Signal notebook</title>
<style>body{background:#f3f1e7;color:#102329;font:16px system-ui;margin:auto;max-width:1040px;padding:32px}header{border-bottom:3px solid #102329;padding:20px 0}small{letter-spacing:3px}h1{font-size:52px;margin:8px 0}section{background:white;border:1px solid #ced9cf;border-radius:16px;padding:24px;margin:24px 0}svg{width:100%;border-radius:10px}ul{display:flex;flex-wrap:wrap;gap:12px 24px;padding:0;list-style:none}b{display:block;font-size:12px;text-transform:uppercase}details ul{display:block}details li{margin:8px 0}</style>
<header><small>◉ TRACE LENS / SIGNAL NOTEBOOK</small><h1>Make every trace count.</h1>Offline numeric inspection · population standard deviation</header>'''
    document += f'<p>Source: {esc(result["source"])} · Rows: {result["total_rows"]}</p>'
    document += f'<p>Baseline interval (inclusive): {esc(result["baseline_interval"])}</p>'
    document += ''.join(cards) + f'<details open><summary>Diagnostics ({len(result["diagnostics"])})</summary><ul>{issues or "<li>No issues found.</li>"}</ul></details>'
    document += '<footer>Trace Lens · Local data, clear signals. Missing samples break the line; input order is preserved.</footer></html>'
    (directory / 'report.html').write_text(document, encoding='utf-8')
    (directory / 'stats.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
