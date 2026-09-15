"""
Patti / Panna Frequency, Cycle Gap & Pattern Detection Engine
============================================================
Analyzes:
1. Frequency of any 3-digit Patti (e.g. '779') in Open, Close, or Both.
2. Cycle Interval / Gap (how many days / games between appearances).
3. Overdue Status (days/games elapsed since last appearance vs average cycle).
4. Pattern Detection (Day-of-week preference, Open vs Close bias, associated Jodis).
5. All 220 standard Matka Pattis ranking table.
"""

from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict, Counter
import pandas as pd
from src.storage.database import MatkaDatabase
from src.config import POPULAR_MARKETS, CUT_NUMBERS

# Generate all 220 standard Matka Pattis
def generate_all_220_pattis() -> List[Dict[str, Any]]:
    pattis = []
    digits = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0]
    
    # 1. Single Pattis (SP) - 120
    for i in range(len(digits)):
        for j in range(i + 1, len(digits)):
            for k in range(j + 1, len(digits)):
                d1, d2, d3 = digits[i], digits[j], digits[k]
                p_str = f"{d1}{d2}{d3}"
                ank = (d1 + d2 + d3) % 10
                pattis.append({
                    "patti": p_str,
                    "ank": ank,
                    "type": "SP",
                    "type_name": "Single Patti (SP)"
                })
                
    # 2. Double Pattis (DP) - 90
    for i in range(len(digits)):
        for j in range(len(digits)):
            if i != j:
                d1, d2 = digits[i], digits[j]
                triplet = sorted([d1, d1, d2], key=lambda x: 10 if x == 0 else x)
                p_str = f"{triplet[0]}{triplet[1]}{triplet[2]}"
                ank = (d1 + d1 + d2) % 10
                pattis.append({
                    "patti": p_str,
                    "ank": ank,
                    "type": "DP",
                    "type_name": "Double Patti (DP)"
                })
                
    # 3. Triple Pattis (TP) - 10
    for d in digits:
        p_str = f"{d}{d}{d}"
        ank = (d * 3) % 10
        pattis.append({
            "patti": p_str,
            "ank": ank,
            "type": "TP",
            "type_name": "Triple Patti (TP)"
        })
        
    unique_pattis = {}
    for p in pattis:
        if p["patti"] not in unique_pattis:
            unique_pattis[p["patti"]] = p
            
    sorted_list = sorted(unique_pattis.values(), key=lambda x: (x["ank"], x["type"], x["patti"]))
    return sorted_list

ALL_220_PATTIS = generate_all_220_pattis()
PATTI_DICT = {p["patti"]: p for p in ALL_220_PATTIS}


class PattiAnalyzerEngine:
    def __init__(self, db: Optional[MatkaDatabase] = None):
        self.db = db or MatkaDatabase()

    def get_chronological_records(self, market: str, limit: int = 5000) -> pd.DataFrame:
        df = self.db.get_market_results(market, limit=limit)
        if df.empty:
            return pd.DataFrame()
        df_sorted = df.sort_values("id", ascending=True).reset_index(drop=True)
        return df_sorted

    def normalize_patti(self, p: str) -> str:
        if not p or len(p) != 3 or not p.isdigit():
            return p
        digits = [int(d) for d in p]
        sorted_digits = sorted(digits, key=lambda x: 10 if x == 0 else x)
        return "".join(str(d) for d in sorted_digits)

    def analyze_patti(
        self,
        market: str,
        patti: str,
        position: str = "BOTH"
    ) -> Dict[str, Any]:
        norm_p = self.normalize_patti(patti)
        p_info = PATTI_DICT.get(norm_p, {
            "patti": norm_p,
            "ank": sum(int(d) for d in norm_p) % 10 if norm_p.isdigit() and len(norm_p) == 3 else 0,
            "type": "DP" if len(set(norm_p)) == 2 else ("TP" if len(set(norm_p)) == 1 else "SP"),
            "type_name": "Patti"
        })

        df = self.get_chronological_records(market)
        if df.empty:
            return {"error": f"No data found for market {market}"}

        total_games = len(df)
        appearances = []

        for idx, r in df.iterrows():
            o_panna = str(r["open_panna"]).strip()
            c_panna = str(r["close_panna"]).strip()
            jodi = str(r["jodi"]).strip()
            day = str(r["day_of_week"]).strip()
            dr = str(r["date_range"]).strip()

            hit_open = (position in ("OPEN", "BOTH")) and (self.normalize_patti(o_panna) == norm_p)
            hit_close = (position in ("CLOSE", "BOTH")) and (self.normalize_patti(c_panna) == norm_p)

            if hit_open:
                appearances.append({
                    "game_index": idx,
                    "date_range": dr,
                    "day": day,
                    "position": "OPEN",
                    "panna": o_panna,
                    "jodi": jodi,
                    "opp_panna": c_panna
                })
            if hit_close:
                appearances.append({
                    "game_index": idx,
                    "date_range": dr,
                    "day": day,
                    "position": "CLOSE",
                    "panna": c_panna,
                    "jodi": jodi,
                    "opp_panna": o_panna
                })

        total_hits = len(appearances)

        gaps = []
        for i in range(len(appearances)):
            if i == 0:
                gap = appearances[i]["game_index"]
            else:
                gap = appearances[i]["game_index"] - appearances[i - 1]["game_index"]
            appearances[i]["gap_since_prev"] = gap
            gaps.append(gap)

        if appearances:
            last_hit_idx = appearances[-1]["game_index"]
            current_overdue_games = (total_games - 1) - last_hit_idx
            latest_hit = appearances[-1]
        else:
            current_overdue_games = total_games
            latest_hit = None

        avg_gap = round(sum(gaps) / len(gaps), 1) if gaps else 0
        min_gap = min(gaps) if gaps else 0
        max_gap = max(gaps) if gaps else 0

        day_counts = Counter([a["day"] for a in appearances])
        dominant_day = day_counts.most_common(1)[0] if day_counts else ("—", 0)
        pos_counts = Counter([a["position"] for a in appearances])
        jodi_counts = Counter([a["jodi"] for a in appearances])

        is_overdue = current_overdue_games > avg_gap if avg_gap > 0 else False
        overdue_ratio = round((current_overdue_games / avg_gap) * 100, 1) if avg_gap > 0 else 0

        return {
            "market": market,
            "patti": norm_p,
            "ank": p_info["ank"],
            "type": p_info["type"],
            "type_name": p_info["type_name"],
            "position_filter": position,
            "total_games_scanned": total_games,
            "total_hits": total_hits,
            "appearances": appearances,
            "gaps": gaps,
            "avg_gap_games": avg_gap,
            "min_gap_games": min_gap,
            "max_gap_games": max_gap,
            "current_overdue_games": current_overdue_games,
            "is_overdue": is_overdue,
            "overdue_ratio": overdue_ratio,
            "latest_hit": latest_hit,
            "day_distribution": dict(day_counts),
            "dominant_day": dominant_day[0],
            "dominant_day_count": dominant_day[1],
            "position_distribution": dict(pos_counts),
            "common_jodis": jodi_counts.most_common(5)
        }

    def get_all_pattis_overview(self, market: str, patti_type: Optional[str] = None) -> List[Dict[str, Any]]:
        df = self.get_chronological_records(market)
        if df.empty:
            return []

        total_games = len(df)
        patti_hits = defaultdict(list)

        for idx, r in df.iterrows():
            o_p = self.normalize_patti(str(r["open_panna"]).strip())
            c_p = self.normalize_patti(str(r["close_panna"]).strip())
            dr = str(r["date_range"]).strip()
            day = str(r["day_of_week"]).strip()

            if o_p in PATTI_DICT:
                patti_hits[o_p].append({"idx": idx, "pos": "OPEN", "dr": dr, "day": day})
            if c_p in PATTI_DICT:
                patti_hits[c_p].append({"idx": idx, "pos": "CLOSE", "dr": dr, "day": day})

        results = []
        for p_info in ALL_220_PATTIS:
            p = p_info["patti"]
            if patti_type and patti_type != "ALL":
                if p_info["type"] != patti_type:
                    continue

            hits = patti_hits.get(p, [])
            count = len(hits)

            if hits:
                gaps = []
                for i in range(len(hits)):
                    if i == 0:
                        gaps.append(hits[i]["idx"])
                    else:
                        gaps.append(hits[i]["idx"] - hits[i - 1]["idx"])
                avg_gap = round(sum(gaps) / len(gaps), 1)
                last_hit = hits[-1]
                overdue = (total_games - 1) - last_hit["idx"]
                last_seen = f"{last_hit['dr']} ({last_hit['day']})"
            else:
                avg_gap = 0
                overdue = total_games
                last_seen = "कधीही नाही (Never)"

            is_overdue = overdue > avg_gap if avg_gap > 0 else False
            overdue_ratio = round((overdue / avg_gap) * 100, 1) if avg_gap > 0 else 0

            results.append({
                "patti": p,
                "ank": p_info["ank"],
                "type": p_info["type"],
                "type_name": p_info["type_name"],
                "total_hits": count,
                "avg_gap": avg_gap,
                "current_overdue": overdue,
                "overdue_ratio": overdue_ratio,
                "is_overdue": is_overdue,
                "last_seen": last_seen,
            })

        results.sort(key=lambda x: (x["total_hits"], -x["current_overdue"]), reverse=True)
        return results
