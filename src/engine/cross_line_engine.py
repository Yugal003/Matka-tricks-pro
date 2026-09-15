"""
Cross Line / Line Dekho Matching Engine
========================================
Implements the exact Cross Line / Table Line Trick from Satta Matka:

Rule:
- Take current vertical or diagonal sequence of past K weeks (e.g. 3, 4, or 5 weeks).
- Scan full historical charts for ANY matching Cross Line (diagonal, vertical, horizontal, or reverse cross).
- A historical line matches if past Jodis match the current Jodis either EXACTLY or in the SAME FAMILY JODI.
- The next Jodi in that historical line (H_{K+1}) is projected as the winning Jodi (and its 8 family members) for the current target day.
- Fallback Rule: If the cross line fails, a RED JODI (double or cut pair) is expected.
"""

from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from src.config import get_jodi_family, CUT_NUMBERS
from src.storage.database import MatkaDatabase

DAY_COLS = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5}
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

RED_JODIS = {
    # Double digits
    "00", "11", "22", "33", "44", "55", "66", "77", "88", "99",
    # Half-cut / Cut pairs
    "05", "50", "16", "61", "27", "72", "38", "83", "49", "94"
}

def is_red_jodi(jodi: str) -> bool:
    if not jodi or len(jodi) != 2 or not jodi.isdigit():
        return False
    return jodi in RED_JODIS

def are_family(j1: str, j2: str) -> bool:
    if not j1 or not j2 or len(j1) != 2 or len(j2) != 2:
        return False
    if not j1.isdigit() or not j2.isdigit():
        return False
    return j2 in get_jodi_family(j1)


class CrossLineEngine:
    def __init__(self, db: Optional[MatkaDatabase] = None):
        self.db = db or MatkaDatabase()

    def get_grid(self, market: str, max_weeks: int = 300) -> List[Dict[str, Any]]:
        """Returns chronological weekly grid [W0, W1, ... W_latest]"""
        df = self.db.get_market_results(market, limit=max_weeks * 7)
        if df.empty:
            return []
        df_sorted = df.sort_values("id", ascending=True)
        grid = []
        for dr, group in df_sorted.groupby("date_range", sort=False):
            row = {"date_range": dr, "days": {}, "grid_row": len(grid)}
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

    def get_cell_jodi(self, grid: List[Dict[str, Any]], r: int, c: int) -> Optional[str]:
        if r < 0 or r >= len(grid) or c < 0 or c >= 6:
            return None
        day = DAY_NAMES[c]
        cell = grid[r].get("days", {}).get(day, {})
        j = cell.get("jodi", "")
        if j and j.isdigit() and len(j) == 2:
            return j
        return None

    def find_cross_line_matches(
        self,
        market: str,
        target_day: str = "Mon",
        min_length: int = 3,
        max_length: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Finds all historical cross-line matches that predict the target day of current week.
        
        Directions checked in historical chart:
        - Down-Right Diagonal (dr=+1, dc=+1)
        - Down-Left Diagonal  (dr=+1, dc=-1)
        - Up-Right Diagonal   (dr=-1, dc=+1)
        - Up-Left Diagonal    (dr=-1, dc=-1)
        - Vertical Column     (dr=+1, dc=0)
        - Step-2 Cross        (dr=+2, dc=+1) / (dr=+2, dc=-1)
        """
        grid = self.get_grid(market)
        n = len(grid)
        if n < min_length + 2:
            return []

        target_col = DAY_COLS.get(target_day, 0)
        target_row = n - 1 # Current week
        
        # Directions to test for the current sequence (usually vertical column on same day, or diagonal ending at target)
        current_directions = [
            ("Vertical (Same Day)", 1, 0),
            ("Diagonal Down-Right", 1, 1),
            ("Diagonal Down-Left", 1, -1),
        ]

        historical_directions = [
            ("Cross Down-Right ↘", 1, 1),
            ("Cross Down-Left ↙", 1, -1),
            ("Cross Up-Right ↗", -1, 1),
            ("Cross Up-Left ↖", -1, -1),
            ("Vertical Column ↓", 1, 0),
            ("Step-2 Cross ↘", 2, 1),
            ("Step-2 Cross ↙", 2, -1),
            ("Horizontal Row →", 0, 1),
        ]

        all_matches = []

        # 1. Build candidate current sequences ending just before target cell (target_row, target_col)
        for cur_name, cdr, cdc in current_directions:
            for k in range(min_length, max_length + 1):
                # Trace backwards k steps from target
                current_seq = []
                valid = True
                for step in range(k, 0, -1):
                    r = target_row - step * cdr
                    c = target_col - step * cdc
                    j = self.get_cell_jodi(grid, r, c)
                    if not j:
                        valid = False
                        break
                    dr_str = grid[r]["date_range"]
                    day_str = DAY_NAMES[c]
                    current_seq.append({
                        "step": k - step + 1,
                        "row": r,
                        "col": c,
                        "date_range": dr_str,
                        "day": day_str,
                        "jodi": j,
                        "family": get_jodi_family(j)
                    })

                if not valid or len(current_seq) != k:
                    continue

                # 2. Now search the ENTIRE historical grid (excluding current trailing weeks)
                # for any historical line of length k+1 that matches current_seq on first k elements
                search_max_row = target_row - k - 1
                for hr0 in range(search_max_row):
                    for hc0 in range(6):
                        for h_dir_name, hdr, hdc in historical_directions:
                            # Check if historical line of length k+1 fits in grid
                            end_hr = hr0 + k * hdr
                            end_hc = hc0 + k * hdc
                            if end_hr < 0 or end_hr >= search_max_row + 2 or end_hc < 0 or end_hc >= 6:
                                continue

                            # Check match for first k elements
                            hist_line = []
                            is_match = True
                            exact_count = 0
                            
                            for step in range(k):
                                hr = hr0 + step * hdr
                                hc = hc0 + step * hdc
                                hj = self.get_cell_jodi(grid, hr, hc)
                                if not hj:
                                    is_match = False
                                    break
                                
                                cj = current_seq[step]["jodi"]
                                if cj == hj:
                                    exact_count += 1
                                elif are_family(cj, hj):
                                    pass
                                else:
                                    is_match = False
                                    break

                                hist_line.append({
                                    "step": step + 1,
                                    "row": hr,
                                    "col": hc,
                                    "date_range": grid[hr]["date_range"],
                                    "day": DAY_NAMES[hc],
                                    "jodi": hj,
                                    "matched_with": cj,
                                    "match_type": "EXACT" if cj == hj else "FAMILY"
                                })

                            if not is_match:
                                continue

                            # Get the projected (k+1)-th element from the historical line!
                            proj_hr = hr0 + k * hdr
                            proj_hc = hc0 + k * hdc
                            proj_jodi = self.get_cell_jodi(grid, proj_hr, proj_hc)
                            if not proj_jodi:
                                continue

                            proj_family = get_jodi_family(proj_jodi)
                            proj_dr = grid[proj_hr]["date_range"]
                            proj_day = DAY_NAMES[proj_hc]

                            # Check if the target cell has already been declared in current week
                            actual_target_jodi = self.get_cell_jodi(grid, target_row, target_col)
                            is_hit = False
                            is_exact_hit = False
                            if actual_target_jodi:
                                if actual_target_jodi == proj_jodi:
                                    is_exact_hit = True
                                    is_hit = True
                                elif actual_target_jodi in proj_family:
                                    is_hit = True

                            # Calculate match confidence score
                            confidence = 75 + (k * 6) + (exact_count * 5)
                            if confidence > 99:
                                confidence = 99.9

                            all_matches.append({
                                "market": market,
                                "match_length": k,
                                "exact_matches": exact_count,
                                "confidence": confidence,
                                "current_line_type": cur_name,
                                "hist_line_type": h_dir_name,
                                "target_day": target_day,
                                "target_date_range": grid[target_row]["date_range"],
                                "current_sequence": current_seq,
                                "historical_line": hist_line,
                                "predicted_jodi": proj_jodi,
                                "predicted_family": proj_family,
                                "hist_anchor_date": proj_dr,
                                "hist_anchor_day": proj_day,
                                "actual_target_jodi": actual_target_jodi,
                                "is_hit": is_hit,
                                "is_exact_hit": is_exact_hit,
                                "red_jodi_warning": "⚠️ If Cross Line fails, RED JODI (double or cut pair) is strongly expected!"
                            })

        # Sort matches by length desc, exact_matches desc, confidence desc
        all_matches.sort(key=lambda m: (m["match_length"], m["exact_matches"], m["confidence"]), reverse=True)
        return all_matches

    def verify_known_example(self) -> Dict[str, Any]:
        """Verifies the user's cross line example."""
        matches = self.find_cross_line_matches("KALYAN", target_day="Mon", min_length=3)
        return {
            "total_matches": len(matches),
            "top_match": matches[0] if matches else None
        }
