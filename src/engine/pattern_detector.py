"""
Family Jodi Repeat Pattern Detector
=====================================
Detects ALL historical instances where Jodi X appears on date D1,
and a family member of X appears again N weeks later on date D2.

User-confirmed examples (Kalyan):
  21 (20/07/22 Wed) → family repeat on 16/09/22 (~8 weeks)
  51 (19/04/23 Wed) → family repeat on 16/06/23 (~8 weeks)
  Prediction: 78 (22/07/26 Wed) → family on 18/09/26 (~8 weeks)
"""
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from src.config import get_jodi_family
from src.storage.database import MatkaDatabase


GAP_COLORS = {
    3:  "#bb86fc",   # violet
    4:  "#00d2ff",   # cyan
    5:  "#00ff99",   # mint
    6:  "#ffcc00",   # yellow
    7:  "#ff9933",   # orange
    8:  "#ff007f",   # hot-pink (main — confirmed by user)
    9:  "#ff4444",   # red
    10: "#cc44ff",   # purple
    11: "#44aaff",   # blue
    12: "#aaffaa",   # light-green
    13: "#ffaaaa",   # light-red
    14: "#aaaaff",   # light-blue
}

DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


class FamilyRepeatPatternDetector:
    """
    Scans a market's full weekly grid and finds every pair:
        (seed_jodi @ week W, repeat_jodi @ week W+gap)
    where repeat_jodi is in the family of seed_jodi.

    Provides:
    - All detected historical pattern instances
    - Hit-rate statistics per gap length
    - Active predictions for upcoming weeks
    """

    def __init__(self, db: Optional[MatkaDatabase] = None):
        self.db = db or MatkaDatabase()

    # ------------------------------------------------------------------
    #  DATA LOADING
    # ------------------------------------------------------------------
    def get_full_grid(self, market: str, max_weeks: int = 250) -> List[Dict[str, Any]]:
        """Returns the full weekly grid for a market (chronological order)."""
        df = self.db.get_market_results(market, limit=max_weeks * 7)
        if df.empty:
            return []

        df_sorted = df.sort_values("id", ascending=True)
        grid: List[Dict[str, Any]] = []

        for date_range, group in df_sorted.groupby("date_range", sort=False):
            row: Dict[str, Any] = {"date_range": date_range, "days": {}}
            for _, r in group.iterrows():
                d = r["day_of_week"]
                row["days"][d] = {
                    "jodi": str(r["jodi"]),
                    "open_panna": str(r["open_panna"]),
                    "close_panna": str(r["close_panna"]),
                    "is_red": int(r["is_red_jodi"]),
                }
            grid.append(row)

        return grid

    # ------------------------------------------------------------------
    #  PATTERN SCANNING
    # ------------------------------------------------------------------
    def scan_all_patterns(
        self,
        market: str,
        gap_range: Tuple[int, int] = (3, 14),
        same_day_bonus: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Scan entire history for every (seed → family repeat) pair.

        Returns list of dicts:
        {
          seed_date, seed_day, seed_jodi,
          repeat_date, repeat_day, repeat_jodi,
          gap_weeks, same_day, is_same_jodi
        }
        """
        grid = self.get_full_grid(market)
        n = len(grid)
        patterns: List[Dict[str, Any]] = []

        for w_idx in range(n):
            week = grid[w_idx]
            seed_date = week.get("date_range", "")

            for seed_day in DAY_ORDER:
                cell = week.get("days", {}).get(seed_day, {})
                seed_jodi = cell.get("jodi", "")
                if not seed_jodi or seed_jodi.startswith("*") or not seed_jodi.isdigit():
                    continue

                family = set(get_jodi_family(seed_jodi))

                for gap in range(gap_range[0], gap_range[1] + 1):
                    future_idx = w_idx + gap
                    if future_idx >= n:
                        break

                    future_week = grid[future_idx]
                    repeat_date = future_week.get("date_range", "")

                    for repeat_day in DAY_ORDER:
                        future_cell = future_week.get("days", {}).get(repeat_day, {})
                        repeat_jodi = future_cell.get("jodi", "")
                        if not repeat_jodi or repeat_jodi.startswith("*") or not repeat_jodi.isdigit():
                            continue

                        if repeat_jodi in family:
                            patterns.append({
                                "seed_date": seed_date,
                                "seed_day": seed_day,
                                "seed_jodi": seed_jodi,
                                "repeat_date": repeat_date,
                                "repeat_day": repeat_day,
                                "repeat_jodi": repeat_jodi,
                                "gap_weeks": gap,
                                "same_day": (seed_day == repeat_day),
                                "is_same_jodi": (seed_jodi == repeat_jodi),
                                "family": sorted(family),
                                "color": GAP_COLORS.get(gap, "#ffffff"),
                            })

        return patterns

    # ------------------------------------------------------------------
    #  STATISTICS
    # ------------------------------------------------------------------
    def get_gap_frequency_stats(self, market: str) -> Dict[int, Dict[str, Any]]:
        """
        Returns per-gap hit statistics:
        { gap_weeks: { 'hits': N, 'opportunities': M, 'hit_rate': pct } }
        """
        grid = self.get_full_grid(market)
        n = len(grid)

        # Count opportunities and hits
        hits: Dict[int, int] = defaultdict(int)
        opportunities: Dict[int, int] = defaultdict(int)

        for w_idx in range(n):
            week = grid[w_idx]
            for seed_day in DAY_ORDER:
                cell = week.get("days", {}).get(seed_day, {})
                seed_jodi = cell.get("jodi", "")
                if not seed_jodi or seed_jodi.startswith("*") or not seed_jodi.isdigit():
                    continue
                family = set(get_jodi_family(seed_jodi))

                for gap in range(3, 15):
                    future_idx = w_idx + gap
                    if future_idx >= n:
                        continue
                    opportunities[gap] += 1

                    future_week = grid[future_idx]
                    for repeat_day in DAY_ORDER:
                        repeat_cell = future_week.get("days", {}).get(repeat_day, {})
                        repeat_jodi = repeat_cell.get("jodi", "")
                        if repeat_jodi in family:
                            hits[gap] += 1
                            break  # count only first hit per week

        stats = {}
        for gap in range(3, 15):
            opp = opportunities.get(gap, 0)
            h = hits.get(gap, 0)
            stats[gap] = {
                "hits": h,
                "opportunities": opp,
                "hit_rate": round(h / opp * 100, 1) if opp > 0 else 0,
                "color": GAP_COLORS.get(gap, "#ffffff"),
            }
        return stats

    # ------------------------------------------------------------------
    #  RECENT-CHART PATTERN MATCHES (for visualizer)
    # ------------------------------------------------------------------
    def get_patterns_for_grid(
        self,
        market: str,
        display_grid: List[Dict[str, Any]],
        gap_filter: Optional[List[int]] = None,
    ) -> List[Dict[str, Any]]:
        """
        For the given display_grid (recent N weeks only), return
        all detected pattern instances that are VISIBLE within this grid.

        Each returned item has:
          seed_row, seed_col  (0-indexed row and col within display_grid)
          repeat_row, repeat_col
          + the usual seed/repeat jodi metadata
        """
        date_to_row = {w.get("date_range", ""): i for i, w in enumerate(display_grid)}
        day_to_col = {d: i for i, d in enumerate(DAY_ORDER)}

        all_patterns = self.scan_all_patterns(market)

        if gap_filter:
            all_patterns = [p for p in all_patterns if p["gap_weeks"] in gap_filter]

        visible: List[Dict[str, Any]] = []
        for p in all_patterns:
            s_row = date_to_row.get(p["seed_date"])
            r_row = date_to_row.get(p["repeat_date"])
            if s_row is None or r_row is None:
                continue
            s_col = day_to_col.get(p["seed_day"])
            r_col = day_to_col.get(p["repeat_day"])
            if s_col is None or r_col is None:
                continue

            visible.append({
                **p,
                "seed_row": s_row,
                "seed_col": s_col,
                "repeat_row": r_row,
                "repeat_col": r_col,
            })

        return visible

    # ------------------------------------------------------------------
    #  ACTIVE PREDICTIONS (for upcoming weeks)
    # ------------------------------------------------------------------
    def get_active_predictions(
        self,
        market: str,
        top_n: int = 15,
        preferred_gap: int = 8,
    ) -> List[Dict[str, Any]]:
        """
        For each recent jodi (within last `preferred_gap` weeks),
        project its family onto the upcoming/current week.

        Returns list of prediction dicts sorted by confidence.
        """
        full_grid = self.get_full_grid(market)
        if len(full_grid) < preferred_gap + 1:
            return []

        # Get hit-rate stats to determine confidence per gap
        stats = self.get_gap_frequency_stats(market)

        predictions: List[Dict[str, Any]] = []
        target_week = full_grid[-1]
        target_date = target_week.get("date_range", "")

        # Scan last preferred_gap+2 weeks for seeds
        scan_start = max(0, len(full_grid) - preferred_gap - 2)
        for w_idx in range(scan_start, len(full_grid) - 1):
            week = full_grid[w_idx]
            seed_date = week.get("date_range", "")
            gap = len(full_grid) - 1 - w_idx  # distance to target week

            if gap < 3 or gap > 14:
                continue

            gap_stat = stats.get(gap, {})
            hit_rate = gap_stat.get("hit_rate", 0)

            for seed_day in DAY_ORDER:
                cell = week.get("days", {}).get(seed_day, {})
                seed_jodi = cell.get("jodi", "")
                if not seed_jodi or seed_jodi.startswith("*") or not seed_jodi.isdigit():
                    continue

                family = sorted(get_jodi_family(seed_jodi))

                # Check if any family member already dropped in target week
                drops = []
                for d in DAY_ORDER:
                    tc = target_week.get("days", {}).get(d, {})
                    tj = tc.get("jodi", "")
                    if tj in family:
                        drops.append({"day": d, "jodi": tj})

                predictions.append({
                    "seed_date": seed_date,
                    "seed_day": seed_day,
                    "seed_jodi": seed_jodi,
                    "gap_weeks": gap,
                    "family": family,
                    "target_date": target_date,
                    "confidence": hit_rate,
                    "drops_found": drops,
                    "is_confirmed": len(drops) > 0,
                    "color": GAP_COLORS.get(gap, "#ffffff"),
                })

        # Sort: confirmed first, then by hit rate
        predictions.sort(key=lambda x: (x["is_confirmed"], x["confidence"]), reverse=True)
        return predictions[:top_n]

    # ------------------------------------------------------------------
    #  RAG CONTEXT BUILDER
    # ------------------------------------------------------------------
    def build_rag_context(self, market: str) -> str:
        """Build a text summary of all detected patterns for RAG/AI use."""
        stats = self.get_gap_frequency_stats(market)
        predictions = self.get_active_predictions(market)

        lines = [
            f"=== Family Repeat Pattern Analysis: {market} ===",
            "",
            "GAP STATISTICS (how often a family member appears N weeks later):",
        ]
        for gap in range(3, 15):
            s = stats[gap]
            lines.append(
                f"  {gap}-week gap: {s['hits']} hits / {s['opportunities']} chances = {s['hit_rate']}% hit rate"
            )

        lines += ["", "ACTIVE PREDICTIONS FOR CURRENT WEEK:"]
        for p in predictions[:8]:
            status = "✅ CONFIRMED" if p["is_confirmed"] else "⏳ PENDING"
            drops = ", ".join(f"{d['day']}:{d['jodi']}" for d in p["drops_found"]) or "Not yet declared"
            lines.append(
                f"  [{status}] {p['seed_jodi']} ({p['seed_day']} {p['seed_date']}) "
                f"→ {p['gap_weeks']}-week gap → "
                f"Family: [{', '.join(p['family'])}] | "
                f"Confidence: {p['confidence']}% | Drops: {drops}"
            )

        return "\n".join(lines)
