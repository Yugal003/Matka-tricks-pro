from typing import List, Dict, Any, Optional
from src.config import CUT_NUMBERS, get_jodi_family
from src.storage.database import MatkaDatabase
import pandas as pd


class LineSchemeAnalyzer:
    """
    Detects cross-line Family Jodi schemes from weekly Matka chart grids.

    The classic Triangle Scheme:
      Point A  (anchor day, e.g. Wed)   → drops its family into a later week's day
      Point B  (step-2 week)            → drops its family into the current week
      Point C  (step-3 week)            → drops its family into the current week
      Target   (current / latest week)  → verified results that belong to A/B/C families
    """

    def __init__(self, db: Optional[MatkaDatabase] = None):
        self.db = db or MatkaDatabase()

    # ------------------------------------------------------------------
    @staticmethod
    def are_family(j1: str, j2: str) -> bool:
        if not j1 or not j2 or len(j1) != 2 or len(j2) != 2:
            return False
        if not j1.isdigit() or not j2.isdigit():
            return False
        return j2 in get_jodi_family(j1)

    # ------------------------------------------------------------------
    def get_weekly_grid(self, market: str, weeks: int = 16) -> List[Dict[str, Any]]:
        """Returns rows grouped week-by-week in chronological order."""
        df = self.db.get_market_results(market, limit=weeks * 7)
        if df.empty:
            return []

        df_sorted = df.sort_values("id", ascending=True)
        grid: List[Dict[str, Any]] = []

        for date_range, group in df_sorted.groupby("date_range", sort=False):
            row: Dict[str, Any] = {"date_range": date_range, "days": {}}
            for _, r in group.iterrows():
                d = r["day_of_week"]
                row["days"][d] = {
                    "open_panna": str(r["open_panna"]),
                    "jodi": str(r["jodi"]),
                    "close_panna": str(r["close_panna"]),
                    "is_red": int(r["is_red_jodi"]),
                }
            grid.append(row)

        return grid

    # ------------------------------------------------------------------
    def detect_active_schemes(self, market: str) -> List[Dict[str, Any]]:
        """
        Scans the chart grid and finds the best triangle cross-line pattern.

        Algorithm:
          For each candidate anchor week W_a and day D_a:
            Look ahead 2-6 weeks for a jodi (W_b, D_b) whose digits / cut
            connect to the target week's declared jodis.
          Returns the top match with Point A, B, C and target projections.
        """
        grid = self.get_weekly_grid(market, weeks=18)
        n = len(grid)
        if n < 5:
            return []

        target_week = grid[-1]
        target_date = target_week.get("date_range", "")

        # Gather declared jodis in the target (current) week
        target_jodis: Dict[str, str] = {}
        for day, data in target_week.get("days", {}).items():
            j = data.get("jodi", "")
            if j and not j.startswith("*") and j != "**":
                target_jodis[day] = j

        # ----- Search for anchor nodes that family-match target jodis ------
        best_scheme: Optional[Dict[str, Any]] = None
        best_score = -1

        candidate_days_a = ["Wed", "Thu", "Mon", "Tue", "Fri", "Sat"]
        candidate_days_b = ["Thu", "Fri", "Tue", "Wed", "Mon", "Sat"]
        candidate_days_c = ["Sat", "Fri", "Mon", "Tue", "Wed", "Thu"]

        for step_a in range(2, min(10, n - 1)):
            w_a = grid[-(step_a + 1)]
            dr_a = w_a.get("date_range", "")

            for d_a in candidate_days_a:
                jodi_a = w_a.get("days", {}).get(d_a, {}).get("jodi", "")
                if not jodi_a or jodi_a.startswith("*"):
                    continue
                fam_a = set(get_jodi_family(jodi_a))

                # Look for point B (between A and current week)
                for step_b in range(1, step_a):
                    w_b = grid[-(step_b + 1)]
                    dr_b = w_b.get("date_range", "")
                    if dr_b == dr_a:
                        continue

                    for d_b in candidate_days_b:
                        jodi_b = w_b.get("days", {}).get(d_b, {}).get("jodi", "")
                        if not jodi_b or jodi_b.startswith("*"):
                            continue
                        fam_b = set(get_jodi_family(jodi_b))

                        # Look for point C (between B and current week OR same as B week)
                        for step_c in range(1, step_b + 1):
                            w_c = grid[-(step_c + 1)] if step_c > 0 else w_b
                            dr_c = w_c.get("date_range", "")
                            if dr_c == dr_a or dr_c == target_date:
                                continue

                            for d_c in candidate_days_c:
                                if dr_c == dr_b and d_c == d_b:
                                    continue
                                jodi_c = w_c.get("days", {}).get(d_c, {}).get("jodi", "")
                                if not jodi_c or jodi_c.startswith("*"):
                                    continue
                                fam_c = set(get_jodi_family(jodi_c))

                                # Score: how many target jodis land in A∪B∪C families?
                                score = 0
                                projections: Dict[str, Any] = {}
                                for t_day, t_jodi in target_jodis.items():
                                    for src, fam, base in [
                                        ("Point A", fam_a, jodi_a),
                                        ("Point B", fam_b, jodi_b),
                                        ("Point C", fam_c, jodi_c),
                                    ]:
                                        if t_jodi in fam:
                                            score += 1
                                            projections[t_day] = {
                                                "source": src,
                                                "base_jodi": base,
                                                "predicted_family": sorted(fam),
                                                "matched_jodi": t_jodi,
                                            }
                                            break

                                if score > best_score:
                                    best_score = score
                                    best_scheme = {
                                        "name": f"Triangle Cross-Line Scheme (A={dr_a}/{d_a}, B={dr_b}/{d_b}, C={dr_c}/{d_c})",
                                        "market": market,
                                        "point_a": {
                                            "date_range": dr_a,
                                            "day": d_a,
                                            "jodi": jodi_a,
                                            "family": sorted(fam_a),
                                            "target_drop_day": d_c,
                                        },
                                        "point_b": {
                                            "date_range": dr_b,
                                            "day": d_b,
                                            "jodi": jodi_b,
                                            "family": sorted(fam_b),
                                            "target_drop_day": d_a,
                                        },
                                        "point_c": {
                                            "date_range": dr_c,
                                            "day": d_c,
                                            "jodi": jodi_c,
                                            "family": sorted(fam_c),
                                            "target_drop_day": d_b,
                                        },
                                        "target_projections": projections,
                                        "match_score": score,
                                    }

        # If no family match found (target week has no declared jodis yet),
        # fall back to the top-frequency cross-pattern heuristic.
        if not best_scheme:
            best_scheme = self._heuristic_scheme(grid, market)

        return [best_scheme] if best_scheme else []

    # ------------------------------------------------------------------
    def _heuristic_scheme(self, grid: List[Dict[str, Any]], market: str) -> Dict[str, Any]:
        """Fallback: pick three highest-frequency nodes and project families."""
        n = len(grid)
        pt_a = self._pick_node(grid, -(min(9, n - 1)), "Wed")
        pt_b = self._pick_node(grid, -(min(5, n - 1)), "Thu")
        pt_c = self._pick_node(grid, -(min(2, n - 1)), "Sat")

        fa, fb, fc = (
            get_jodi_family(pt_a[2]),
            get_jodi_family(pt_b[2]),
            get_jodi_family(pt_c[2]),
        )
        proj = {}
        for day in ["Mon", "Tue", "Wed", "Thu", "Fri"]:
            proj[day] = {"source": "Point B", "base_jodi": pt_b[2], "predicted_family": fb}

        return {
            "name": "Heuristic Cross-Line Scheme",
            "market": market,
            "point_a": {"date_range": pt_a[0], "day": pt_a[1], "jodi": pt_a[2], "family": fa, "target_drop_day": "Fri"},
            "point_b": {"date_range": pt_b[0], "day": pt_b[1], "jodi": pt_b[2], "family": fb, "target_drop_day": "Tue"},
            "point_c": {"date_range": pt_c[0], "day": pt_c[1], "jodi": pt_c[2], "family": fc, "target_drop_day": "Wed"},
            "target_projections": proj,
            "match_score": 0,
        }

    @staticmethod
    def _pick_node(grid: List[Dict[str, Any]], idx: int, preferred_day: str):
        w = grid[idx]
        dr = w.get("date_range", "")
        days_try = [preferred_day, "Wed", "Thu", "Fri", "Tue", "Mon", "Sat"]
        for d in days_try:
            j = w.get("days", {}).get(d, {}).get("jodi", "")
            if j and not j.startswith("*"):
                return (dr, d, j)
        return (dr, preferred_day, "78")
