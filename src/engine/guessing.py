import random
from typing import Dict, Any, List
from src.config import CUT_NUMBERS, get_jodi_family
from src.engine.statistics import MatkaStatistics

# Standard 220 Patti Lookup by Digit Sum
STANDARD_PANAS = {
    0: ["127", "136", "145", "190", "235", "280", "370", "460", "550", "555", "118", "226", "334", "442", "677", "899"],
    1: ["128", "137", "146", "236", "245", "290", "380", "470", "560", "678", "119", "227", "335", "443", "551", "669"],
    2: ["129", "138", "147", "156", "237", "246", "345", "390", "480", "570", "679", "110", "228", "336", "444", "552"],
    3: ["120", "139", "148", "157", "238", "247", "256", "346", "490", "580", "670", "689", "111", "229", "337", "445"],
    4: ["130", "149", "158", "167", "239", "248", "257", "347", "356", "590", "680", "789", "112", "220", "338", "446"],
    5: ["140", "159", "168", "230", "249", "258", "267", "348", "357", "456", "690", "780", "113", "221", "339", "447"],
    6: ["150", "169", "178", "240", "259", "268", "349", "358", "367", "457", "790", "890", "114", "222", "330", "448"],
    7: ["160", "179", "250", "269", "278", "340", "359", "368", "458", "467", "890", "115", "223", "331", "449", "557"],
    8: ["170", "189", "260", "279", "350", "369", "378", "459", "468", "567", "116", "224", "332", "440", "558", "666"],
    9: ["180", "199", "270", "289", "360", "379", "388", "450", "469", "478", "568", "117", "225", "333", "441", "559"],
}

class MatkaGuessingEngine:
    def __init__(self, stats_engine: MatkaStatistics = None):
        self.stats = stats_engine or MatkaStatistics()

    def generate_guesses(self, market: str, day_of_week: str = "Mon") -> Dict[str, Any]:
        """Generates statistical guessing calculations for a given market."""
        summary = self.stats.get_market_summary(market)
        
        # 1. Determine Strong OTC (Open To Close) 4 digits
        hot_digits = summary.get("hot_digits", [1, 6, 2, 7])
        if len(hot_digits) < 4:
            hot_digits = [1, 6, 2, 7]
            
        # Top 2 primary + their Cut digits make standard 4-digit OTC
        d1 = hot_digits[0]
        d2 = hot_digits[1] if len(hot_digits) > 1 else (d1 + 3) % 10
        c1 = CUT_NUMBERS[d1]
        c2 = CUT_NUMBERS[d2]
        
        otc_digits = sorted(list({d1, c1, d2, c2}))
        while len(otc_digits) < 4:
            for extra in range(10):
                if extra not in otc_digits:
                    otc_digits.append(extra)
                    if len(otc_digits) == 4:
                        break

        # 2. Strong Jodi Combinations (8 pairs)
        primary_jodis = []
        for i in range(len(otc_digits)):
            for j in range(len(otc_digits)):
                if i != j:
                    primary_jodis.append(f"{otc_digits[i]}{otc_digits[j]}")
        
        # Select top 8 jodis
        selected_jodis = primary_jodis[:8]

        # 3. Panna / Patti recommendations (3 panna per OTC digit)
        recommended_panas = {}
        for d in otc_digits:
            available = STANDARD_PANAS.get(d, ["123", "456", "789"])
            recommended_panas[d] = available[:3]

        # 4. Support / Family Jodis
        lead_jodi = selected_jodis[0] if selected_jodis else "16"
        family_jodis = get_jodi_family(lead_jodi)

        return {
            "market": market,
            "target_day": day_of_week,
            "otc_digits": otc_digits,
            "single_ank_tips": [f"{d} (Cut: {CUT_NUMBERS[d]})" for d in otc_digits],
            "strong_jodis": selected_jodis,
            "family_jodi_group": {
                "base_jodi": lead_jodi,
                "family": family_jodis
            },
            "panna_charts": recommended_panas,
            "confidence_factors": {
                "historical_records_analyzed": summary.get("total_records", 0),
                "top_frequent_total_sum": list(summary.get("total_sum_freq", {7: 1}).keys())[0] if summary.get("total_sum_freq") else 7,
                "red_jodi_probability": f"{summary.get('red_jodi_pct', 15.0)}%"
            }
        }
