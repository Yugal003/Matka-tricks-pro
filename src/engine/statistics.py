import pandas as pd
import numpy as np
from typing import Dict, Any, List
from src.storage.database import MatkaDatabase
from src.config import CUT_NUMBERS

class MatkaStatistics:
    def __init__(self, db: MatkaDatabase = None):
        self.db = db or MatkaDatabase()

    def get_market_summary(self, market: str) -> Dict[str, Any]:
        df = self.db.get_market_results(market, limit=300)
        if df.empty:
            return {
                "market": market,
                "total_records": 0,
                "message": "No historical records found for this market."
            }

        # Digits frequencies
        open_counts = df["open_digit"].value_counts().to_dict()
        close_counts = df["close_digit"].value_counts().to_dict()
        
        # All 0-9 digits ensured
        open_freq = {d: open_counts.get(d, 0) for d in range(10)}
        close_freq = {d: close_counts.get(d, 0) for d in range(10)}
        
        # Combined digit power (Total appearances in Open or Close)
        combined_freq = {d: open_freq[d] + close_freq[d] for d in range(10)}
        sorted_digits = sorted(combined_freq.items(), key=lambda x: x[1], reverse=True)
        hot_digits = [d[0] for d in sorted_digits[:4]]
        cold_digits = [d[0] for d in sorted_digits[-3:]]

        # Top Jodis
        jodi_counts = df["jodi"].value_counts().head(10).to_dict()

        # Jodi Totals (Sum mod 10)
        total_counts = df["jodi_total"].value_counts().to_dict()
        total_freq = {t: total_counts.get(t, 0) for t in range(10)}
        
        # Red Jodi ratio
        red_jodi_count = int(df["is_red_jodi"].sum())
        red_jodi_pct = round((red_jodi_count / len(df)) * 100, 1)

        # Day of week breakdown
        day_breakdown = {}
        for day, group in df.groupby("day_of_week"):
            day_digits = group["open_digit"].value_counts().head(3).index.tolist()
            day_breakdown[day] = day_digits

        # Recent 10 draws
        recent_draws = df[["date_range", "day_of_week", "open_panna", "jodi", "close_panna"]].head(10).to_dict(orient="records")

        return {
            "market": market,
            "total_records": len(df),
            "hot_digits": hot_digits,
            "cold_digits": cold_digits,
            "open_freq": open_freq,
            "close_freq": close_freq,
            "combined_freq": combined_freq,
            "top_jodis": jodi_counts,
            "total_sum_freq": total_freq,
            "red_jodi_count": red_jodi_count,
            "red_jodi_pct": red_jodi_pct,
            "day_breakdown": day_breakdown,
            "recent_draws": recent_draws
        }

    def get_jodi_matrix(self, market: str) -> pd.DataFrame:
        """Constructs a 10x10 frequency matrix for Open vs Close digits."""
        df = self.db.get_market_results(market, limit=500)
        matrix = pd.DataFrame(0, index=range(10), columns=range(10))
        if df.empty:
            return matrix

        for _, row in df.iterrows():
            o, c = row["open_digit"], row["close_digit"]
            if pd.notna(o) and pd.notna(c):
                matrix.loc[int(o), int(c)] += 1
        return matrix
