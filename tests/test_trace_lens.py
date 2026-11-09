import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from trace_lens.core import read_csv, summarize, analyze
from trace_lens.report import plot_svg, write_report


class TraceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def data(self, text, columns=None):
        path = self.root / 'input.csv'
        path.write_text(text, encoding='utf-8')
        return read_csv(path, 't', columns)

    def test_stats(self):
        s = summarize([1, 2, 3])
        self.assertEqual((s['count'], s['min'], s['max'], s['mean']), (3, 1, 3, 2))
        self.assertAlmostEqual(s['std'], math.sqrt(2 / 3))
        self.assertAlmostEqual(s['rms'], math.sqrt(14 / 3))

    def test_empty_stats(self):
        self.assertEqual(summarize([])['mean'], None)

    def test_constant(self):
        self.assertEqual(summarize([4, 4])['std'], 0)

    def test_extreme_values(self):
        s = summarize([-1e308, 1e308])
        self.assertEqual(s['mean'], 0)
        self.assertEqual(s['rms'], 1e308)
        self.assertEqual(s['std'], 1e308)

    def test_missing_invalid_and_nonfinite(self):
        data = self.data('t,a\n0,\n1,no\n2,nan\n3,inf\n4,2\n')
        self.assertEqual([d['reason'] for d in data.diagnostics], ['missing', 'invalid', 'nonfinite', 'nonfinite'])
        result, _ = analyze(data)
        self.assertEqual(result['columns']['a']['count'], 1)
        self.assertEqual(result['columns']['a']['excluded'], 4)

    def test_bad_x_excludes_entire_row(self):
        result, _ = analyze(self.data('t,a\n?,100\n1,2\n'))
        self.assertEqual(result['columns']['a']['mean'], 2)
        self.assertEqual(result['diagnostics'][1]['reason'], 'row_excluded')

    def test_baseline_inclusive(self):
        result, traces = analyze(self.data('t,a\n0,2\n1,4\n2,8\n'), (0, 1))
        self.assertEqual(result['columns']['a']['baseline_offset'], 3)
        self.assertEqual(traces['a'], [(0, -1), (1, 1), (2, 5)])

    def test_baseline_invalid_empty_overflow(self):
        for interval in [(2, 1), (0, float('inf')), (10, 11)]:
            with self.assertRaises(ValueError):
                analyze(self.data('t,a\n0,2\n'), interval)
        with self.assertRaisesRegex(ValueError, 'overflow'):
            analyze(self.data('t,a\n0,-1e308\n1,1e308\n'), (0, 0))

    def test_duplicate_header(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.data('t,a,a\n0,1,2\n')

    def test_ragged_rows(self):
        with self.assertRaisesRegex(ValueError, 'Line 2'):
            self.data('t,a\n0\n')

    def test_unknown_and_invalid_selection(self):
        for names in [['absent'], ['a', 'a'], ['t']]:
            with self.assertRaises(ValueError):
                self.data('t,a\n0,1\n', names)

    def test_empty_input(self):
        for text in ['', 't,a\n', 't,\n0,1\n']:
            with self.assertRaises(ValueError):
                self.data(text)

    def test_unsorted_x(self):
        data = self.data('t,a\n2,1\n1,2\n')
        self.assertEqual(data.diagnostics[0]['reason'], 'unsorted_x')

    def test_svg_escaping_gap_and_singleton(self):
        svg = plot_svg('<script>', 'x&y', [(0, 1), (1, None), (2, 3)])
        self.assertNotIn('<script>', svg)
        self.assertIn('&lt;script&gt;', svg)
        self.assertEqual(svg.count('<path'), 2)
        self.assertIn('<circle', plot_svg('a', 't', [(1, 1)]))

    def test_svg_extreme_ranges(self):
        svg = plot_svg('a', 't', [(-1e308, -1e308), (1e308, 1e308)])
        self.assertNotIn('nan', svg)
        self.assertNotIn('inf', svg)
        self.assertIn('M75.000,225.000 L865.000,60.000', svg)

    def test_report_offline_escaped_json_and_existing_dir(self):
        result, traces = analyze(self.data('t,<script>\n0,1\n'))
        out = self.root / 'report'
        write_report(out, result, traces)
        html = (out / 'report.html').read_text()
        self.assertNotIn('<script>', html)
        self.assertNotIn('src="http', html)
        self.assertEqual(json.loads((out / 'stats.json').read_text())['total_rows'], 1)
        with self.assertRaises(FileExistsError):
            write_report(out, result, traces)

    def test_cli_smoke_and_deterministic_sample(self):
        def cli(*args):
            return subprocess.run([sys.executable, '-m', 'trace_lens', *map(str, args)], capture_output=True, text=True)
        a, b, out = self.root / 'a.csv', self.root / 'b.csv', self.root / 'out'
        self.assertEqual(cli('sample', a).returncode, 0)
        self.assertEqual(cli('sample', b).returncode, 0)
        self.assertEqual(a.read_bytes(), b.read_bytes())
        run = cli('report', a, '--x', 'time_s', '--baseline', '0', '1', '--out', out)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn('missing', run.stderr)
        self.assertTrue((out / 'report.html').exists())
        self.assertEqual(cli('report', a, '--x', 'bad', '--out', self.root / 'bad').returncode, 2)
        self.assertEqual(cli('sample', a).returncode, 2)


if __name__ == '__main__':
    unittest.main()
