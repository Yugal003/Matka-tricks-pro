import unittest
import math
from src.config import get_jodi_family, CUT_NUMBERS, POPULAR_MARKETS
from src.storage.database import MatkaDatabase
from src.engine.family_triangle_engine import FamilyTriangleEngine, render_family_triangle_panel_html
from src.engine.date_figure_engine import DateFigureEngine
from src.engine.cross_line_engine import CrossLineEngine
from src.engine.patti_analyzer import PattiAnalyzerEngine
from src.engine.tricks_engine import TrickAnalyzer, TRICKS

class TestConfigAndMath(unittest.TestCase):
    def test_cut_numbers(self):
        for d in range(10):
            cut = CUT_NUMBERS[d]
            self.assertEqual((cut - d) % 5, 0)
            self.assertEqual(CUT_NUMBERS[cut], d)

    def test_jodi_family_generation(self):
        fam_22 = set(get_jodi_family('22'))
        self.assertIn('22', fam_22)
        self.assertIn('27', fam_22)
        self.assertIn('72', fam_22)
        self.assertIn('77', fam_22)

        fam_14 = set(get_jodi_family('14'))
        self.assertEqual(len(fam_14), 8)
        self.assertIn('14', fam_14)
        self.assertIn('69', fam_14)
        self.assertIn('41', fam_14)

    def test_database_records(self):
        db = MatkaDatabase()
        for m in ['KALYAN', 'MILAN DAY', 'MAIN BAZAR', 'MILAN NIGHT']:
            df = db.get_market_results(m, limit=15)
            self.assertFalse(df.empty, f'Market {m} should have data')
            self.assertIn('jodi', df.columns)
            self.assertIn('open_panna', df.columns)
            self.assertIn('close_panna', df.columns)

class TestFamilyTriangleEngine(unittest.TestCase):
    def setUp(self):
        self.engine = FamilyTriangleEngine()

    def test_snippet_row_counts(self):
        for rows in [2, 3, 4, 5, 6]:
            snip = self.engine.get_snippet('KALYAN', rows_count=rows)
            self.assertEqual(len(snip), rows, f'Snippet should contain {rows} rows')

    def test_triangle_geometry_and_families(self):
        snip = self.engine.get_snippet('KALYAN', rows_count=5)
        res = self.engine.find_all_triangles(snip, target_day='Mon')
        
        for tri in res['completed']:
            nA, nB, nC = tri['nodes']
            area2 = (nB['c'] - nA['c']) * (nC['r'] - nA['r']) - (nB['r'] - nA['r']) * (nC['c'] - nA['c'])
            self.assertNotEqual(area2, 0, 'Completed triangle cannot be collinear')
            self.assertGreater(tri['area'], 0)
            fam = set(tri['family'])
            for j in tri['jodis']:
                self.assertIn(j, fam)
                
        for p_tri in res['projected']:
            self.assertIn('target_node', p_tri)
            self.assertEqual(p_tri['target_node']['jodi'], '??')
            self.assertEqual(len(p_tri['known_jodis']), 2)
            self.assertGreater(len(p_tri['predicted_family']), 0)

    def test_svg_rendering(self):
        snip = self.engine.get_snippet('KALYAN', rows_count=4)
        res = self.engine.find_all_triangles(snip, target_day='Mon')
        all_tri = res['completed'] + res['projected']
        html = render_family_triangle_panel_html(snip, all_tri, active_idx=0 if all_tri else None, title='Test Triangle')
        self.assertIn('<svg', html)
        self.assertIn('<table', html)

class TestDateFigureEngine(unittest.TestCase):
    def setUp(self):
        self.engine = DateFigureEngine()

    def test_rule_6_figures(self):
        info = self.engine.get_figures_for_date(5)
        figs = info['fix_figures']
        self.assertEqual(len(figs), 6)
        self.assertIn(5, figs)
        self.assertIn(0, figs)
        self.assertIn(1, figs)
        self.assertIn(6, figs)
        self.assertIn(4, figs)
        self.assertIn(9, figs)

    def test_weekly_analysis(self):
        weeks = self.engine.analyze_market_weeks('KALYAN', limit_weeks=10)
        self.assertIsInstance(weeks, list)
        self.assertGreater(len(weeks), 0)
        first_week = weeks[0]
        self.assertIn('date_range', first_week)
        self.assertIn('days', first_week)
        self.assertIn('pass_rate', first_week)

class TestCrossLineEngine(unittest.TestCase):
    def setUp(self):
        self.engine = CrossLineEngine()

    def test_find_cross_lines(self):
        matches = self.engine.find_cross_line_matches('KALYAN', target_day='Mon', min_length=3, max_length=5)
        self.assertIsInstance(matches, list)
        if matches:
            m = matches[0]
            self.assertIn('predicted_jodi', m)
            self.assertIn('predicted_family', m)
            self.assertIn('confidence', m)

class TestPattiAnalyzer(unittest.TestCase):
    def setUp(self):
        self.engine = PattiAnalyzerEngine()

    def test_patti_analysis(self):
        res = self.engine.analyze_patti('KALYAN', '779')
        self.assertIn('patti', res)
        self.assertEqual(res['patti'], '779')
        self.assertIn('total_hits', res)
        self.assertIn('day_distribution', res)
        self.assertIn('gaps', res)
        self.assertIn('avg_gap_games', res)

class TestTricksEngine(unittest.TestCase):
    def setUp(self):
        self.analyzer = TrickAnalyzer()

    def test_22_tricks_evaluation(self):
        res = self.analyzer.analyze_all('KALYAN')
        self.assertIsInstance(res, list)
        self.assertGreater(len(res), 15)
        top = res[0]
        self.assertIn('trick_name', top)
        self.assertIn('pass_rate', top)
        self.assertIn('total_weeks', top)

    def test_4_markets_repeat_scheme(self):
        weeks = self.analyzer.get_4markets_recent_analysis(limit=8)
        self.assertIsInstance(weeks, list)
        self.assertGreater(len(weeks), 0)
        w = weeks[0]
        self.assertIn('mon', w)
        self.assertIn('tue', w)
        self.assertIn('is_pass', w)

class TestFamilySequenceTriangleEngine(unittest.TestCase):
    def test_81_and_23_sequence_prediction(self):
        """Verify user's exact example: 81 and 23 predict 33 family and 30 family"""
        from src.engine.family_sequence_triangle_engine import find_family_pair_sequence, FamilySequenceTriangleEngine, render_family_sequence_triangle_panel_html
        seqs = find_family_pair_sequence('81', '23')
        self.assertGreater(len(seqs), 0)
        
        # Check that 33 family (forward) and 30 family (backward) are predicted
        all_fwd = []
        all_bwd = []
        for s in seqs:
            all_fwd.extend(s['fwd_family'])
            all_bwd.extend(s['bwd_family'])
            
        self.assertIn('33', set(all_fwd))
        self.assertIn('38', set(all_fwd))
        self.assertIn('30', set(all_bwd))
        self.assertIn('58', set(all_bwd))

    def test_sequence_triangle_engine_kalyan(self):
        """Verify sequence engine scans Kalyan chart and generates valid SVG HTML"""
        from src.engine.family_sequence_triangle_engine import FamilySequenceTriangleEngine, render_family_sequence_triangle_panel_html
        eng = FamilySequenceTriangleEngine()
        snip = eng.get_snippet('KALYAN', rows_count=4)
        res = eng.find_all_sequence_triangles(snip, target_day='Mon')
        self.assertIn('completed', res)
        self.assertIn('projected', res)
        all_seq = res['completed'] + res['projected']
        html = render_family_sequence_triangle_panel_html(snip, all_seq, active_idx=0 if all_seq else None)
        self.assertIn('<svg', html)
        self.assertIn('<table', html)

if __name__ == '__main__':
    unittest.main()
