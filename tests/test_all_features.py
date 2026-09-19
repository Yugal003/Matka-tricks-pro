import unittest
import math
from src.config import get_jodi_family, CUT_NUMBERS, POPULAR_MARKETS
from src.storage.database import MatkaDatabase
from src.engine.family_triangle_engine import FamilyTriangleEngine, render_family_triangle_panel_html
from src.engine.date_figure_engine import DateFigureEngine
from src.engine.cross_line_engine import CrossLineEngine
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
        res = eng.find_all_sequence_triangles(snip, target_day='Tue')
        self.assertIn('completed', res)
        self.assertIn('projected', res)
        all_seq = res['completed'] + res['projected']
        html = render_family_sequence_triangle_panel_html(snip, all_seq, active_idx=0 if all_seq else None)
        self.assertIn('<svg', html)
        self.assertIn('<table', html)

        # Test overlay all mode (active_idx=None)
        overlay_html = render_family_sequence_triangle_panel_html(snip, res['projected'], active_idx=None)
        self.assertIn('<svg', overlay_html)
        self.assertIn('<polygon', overlay_html)

    def test_triangle_palettes_import_and_usage(self):
        """Verify TRIANGLE_PALETTES is importable and valid"""
        from src.engine.family_triangle_engine import TRIANGLE_PALETTES
        self.assertIsInstance(TRIANGLE_PALETTES, list)
        self.assertGreater(len(TRIANGLE_PALETTES), 5)
        for p in TRIANGLE_PALETTES:
            self.assertIn('stroke', p)
            self.assertIn('fill', p)
            self.assertIn('glow', p)

    def test_sunday_support_and_constants(self):
        """Verify Sunday is supported across all engines"""
        from src.engine.family_triangle_engine import DAY_ORDER as FT_DAYS, DAY_COLS as FT_COLS, DAY_MARATHI as FT_MAR
        from src.engine.family_sequence_triangle_engine import DAY_ORDER as FST_DAYS, DAY_COLS as FST_COLS, DAY_MARATHI as FST_MAR
        from src.engine.cross_line_visualizer import DAY_ORDER as CL_DAYS, DAY_COLS as CL_COLS, DAY_MARATHI as CL_MAR
        from src.engine.cross_line_engine import DAY_NAMES as CLE_DAYS, DAY_COLS as CLE_COLS

        for days in [FT_DAYS, FST_DAYS, CL_DAYS, CLE_DAYS]:
            self.assertIn("Sun", days)
            self.assertEqual(len(days), 7)

        for cols in [FT_COLS, FST_COLS, CL_COLS, CLE_COLS]:
            self.assertEqual(cols["Sun"], 6)

        for mar in [FT_MAR, FST_MAR]:
            self.assertEqual(mar["Sun"], "रविवार")

    def test_week_transition_and_past_row_integrity(self):
        """
        Verify that when target_day is already declared in current row,
        the engine advances to the new week (21/09/2026 to ...), and the
        previous week (14/09/2026 to 19/09/2026) becomes a valid past row (< target_r).
        """
        from src.engine.family_triangle_engine import FamilyTriangleEngine
        from src.engine.family_sequence_triangle_engine import FamilySequenceTriangleEngine

        ft_eng = FamilyTriangleEngine()
        # In Kalyan, 14/09/2026 already has Mon = '00'
        snip = ft_eng.get_snippet('KALYAN', rows_count=5, target_day='Mon')
        self.assertGreaterEqual(len(snip), 2)
        target_row = snip[-1]
        past_week_row = snip[-2]

        # The new week is appended as the target row
        self.assertIn('21/09/2026', target_row['date_range'])
        # The 14/09 row is strictly before the target row
        self.assertIn('14/09/2026', past_week_row['date_range'])

        # Check projected triangles: all base nodes must have r < target_r (i.e. strictly from past weeks)
        res = ft_eng.find_all_triangles(snip, target_day='Mon')
        target_r = len(snip) - 1
        for t in res['projected']:
            node_A, node_B, target_node = t['nodes']
            self.assertLess(node_A['r'], target_r)
            self.assertLess(node_B['r'], target_r)
            self.assertEqual(target_node['r'], target_r)
            self.assertEqual(target_node['jodi'], '??')

        # Check sequence engine
        fst_eng = FamilySequenceTriangleEngine()
        fst_snip = fst_eng.get_snippet('KALYAN', rows_count=5, target_day='Mon')
        fst_res = fst_eng.find_all_sequence_triangles(fst_snip, target_day='Mon')
        for t in fst_res['projected']:
            node_A, node_B, target_node = t['nodes']
            self.assertLess(node_A['r'], target_r)
            self.assertLess(node_B['r'], target_r)
            self.assertEqual(target_node['r'], target_r)

    def test_supreme_markets_with_sunday(self):
        """Verify Supreme Day and Supreme Night support Sunday records"""
        from src.storage.database import MatkaDatabase
        from src.engine.cross_line_engine import CrossLineEngine
        db = MatkaDatabase()
        df_sd = db.get_market_results('SUPREME DAY', limit=20)
        self.assertFalse(df_sd.empty)
        # Check that Sunday is present in records
        days = df_sd['day_of_week'].unique()
        self.assertIn('Sun', days)

        cl_eng = CrossLineEngine(db)
        grid = cl_eng.get_grid('SUPREME DAY', max_weeks=10)
        self.assertGreater(len(grid), 0)

if __name__ == '__main__':
    unittest.main()


