"""
Matka Tricks Engine
====================
Implements all tricks from dpbossking.in/satta-matka-tricks-zone/

Each trick defines:
  name         : display name
  description  : plain English rule  
  check(week)  : function → True/False if trick passes for a given week's data
  check_market : scans full grid and returns pass-rate + recent streak
"""
from typing import List, Dict, Any, Optional, Tuple
from src.storage.database import MatkaDatabase


DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

# Cut digit pairs: 0↔5, 1↔6, 2↔7, 3↔8, 4↔9
CUT = {0:5,1:6,2:7,3:8,4:9, 5:0,6:1,7:2,8:3,9:4}


def _jodi(week: Dict, day: str) -> Optional[str]:
    """Return jodi string for a day, or None if missing."""
    cell = week.get("days", {}).get(day, {})
    j = cell.get("jodi", "")
    return j if (j and j.isdigit() and len(j) == 2) else None


def _open_digit(week: Dict, day: str) -> Optional[int]:
    j = _jodi(week, day)
    return int(j[0]) if j else None


def _close_digit(week: Dict, day: str) -> Optional[int]:
    j = _jodi(week, day)
    return int(j[1]) if j else None


def _all_digits(week: Dict) -> List[int]:
    """Return all open+close digits present in a week."""
    digits = []
    for d in DAY_ORDER:
        j = _jodi(week, d)
        if j:
            digits.extend([int(j[0]), int(j[1])])
    return digits


def _is_red_jodi(j: str) -> bool:
    if not j or not j.isdigit() or len(j) != 2:
        return False
    a, b = int(j[0]), int(j[1])
    return a == b or CUT[a] == b


# ============================================================
# TRICK DEFINITIONS
# ============================================================

TRICKS: List[Dict[str, Any]] = []



def trick(name: str, desc: str, category: str = "General",
          marathi_name: str = "", marathi_desc: str = ""):
    """Decorator to register a trick checker function."""
    def decorator(fn):
        TRICKS.append({
            "name": name,
            "marathi_name": marathi_name or name,
            "description": desc,
            "marathi_desc": marathi_desc or desc,
            "category": category,
            "check": fn,
        })
        return fn
    return decorator


# ---- 1. Mon-Tue Same Jodi -----------------------------------------
@trick(
    "Mon-Tue Same Jodi",
    "Rule: Monday and Tuesday Jodi of the same week must be identical "
    "(same 2-digit number). Tracks how often Mon==Tue jodi.",
    "Jodi Repeat",
    marathi_name="सोम-मंगळ एकसारखी जोडी",
    marathi_desc="नियम: आठवड्यात सोमवार आणि मंगळवारची जोडी एकसारखी असते. "
                 "किती आठवड्यात सोम==मंगळ जोडी येते ते मोजतो.",
)
def _mon_tue_same(week: Dict) -> Optional[bool]:
    m = _jodi(week, "Mon")
    t = _jodi(week, "Tue")
    if m is None or t is None:
        return None
    return m == t


# ---- 2. Red Jodi Week (Supplementary Red) -------------------------
@trick(
    "Supplementary Red (Week Has Red Jodi)",
    "Rule: Any week where at least one Red Jodi (double-digit like 00,11..99 "
    "or cut-pair like 05,50,16,61,27,72,38,83,49,94) appears. "
    "Tracks frequency of Red Jodi occurrence per week.",
    "Red Jodi"
)
def _supp_red(week: Dict) -> Optional[bool]:
    has_data = False
    for d in DAY_ORDER:
        j = _jodi(week, d)
        if j:
            has_data = True
            if _is_red_jodi(j):
                return True
    return False if has_data else None


# ---- 3. Weekly Close-Line (Same Close Digit Mon-Sat) ---------------
@trick(
    "Close Line Dekho (Close Digit Repeats in Week)",
    "Rule: Within a week, at least 3 days share the same Close (units) digit. "
    "E.g., Mon=23, Wed=43, Fri=73 — all close on 3. Tracks pass rate.",
    "Close Line"
)
def _close_line(week: Dict) -> Optional[bool]:
    from collections import Counter
    closes = []
    for d in DAY_ORDER:
        j = _jodi(week, d)
        if j:
            closes.append(int(j[1]))
    if len(closes) < 3:
        return None
    freq = Counter(closes)
    return max(freq.values()) >= 3


# ---- 4. Fix Day Figure (Open digit same on same day each week) -----
@trick(
    "Fix Day Figure (Same Open/Close Digit Same Day Consecutive Weeks)",
    "Rule: A digit (0-9) appears as Open on the SAME day for 2+ consecutive weeks. "
    "Tracks how often any digit is 'fixed' on its day for 2 consecutive weeks.",
    "Fix Day"
)
def _fix_day_figure(week: Dict, prev_week: Optional[Dict] = None) -> Optional[bool]:
    if prev_week is None:
        return None
    for d in DAY_ORDER:
        cur = _open_digit(week, d)
        prv = _open_digit(prev_week, d)
        if cur is not None and prv is not None and cur == prv:
            return True
    return False


# ---- 5. Weekly Calculation (Sum of all jodis % 10 = same digit) ---
@trick(
    "Weekly Calculation (Sum Rule)",
    "Rule: Add all Jodi numbers of the week. The units digit of the total "
    "matches the Open digit of the following Monday. Tracks this pattern.",
    "Calculation"
)
def _weekly_calc(week: Dict, next_week: Optional[Dict] = None) -> Optional[bool]:
    if next_week is None:
        return None
    total = 0
    count = 0
    for d in DAY_ORDER:
        j = _jodi(week, d)
        if j:
            total += int(j)
            count += 1
    if count < 3:
        return None
    predicted_digit = total % 10
    next_mon_open = _open_digit(next_week, "Mon")
    if next_mon_open is None:
        return None
    return predicted_digit == next_mon_open


# ---- 6. Single Bracket Scheme (Open+Close digit sum) ---------------
@trick(
    "Single Bracket Scheme (Jodi digit sum bracket)",
    "Rule: Sum the two digits of any Jodi. The result (0-18) falls into a bracket. "
    "Same bracket number appears the following week. Pass = same bracket sum±1 next Mon.",
    "Bracket"
)
def _single_bracket(week: Dict, next_week: Optional[Dict] = None) -> Optional[bool]:
    if next_week is None:
        return None
    brackets_this = set()
    for d in DAY_ORDER:
        j = _jodi(week, d)
        if j:
            s = int(j[0]) + int(j[1])
            brackets_this.add(s % 10)  # units of sum
    next_mon = _jodi(next_week, "Mon")
    if not next_mon or not brackets_this:
        return None
    nm_sum = (int(next_mon[0]) + int(next_mon[1])) % 10
    return nm_sum in brackets_this


# ---- 7. Band-Week Gine (Consecutive digits in a week) --------------
@trick(
    "Band Week Gine (Consecutive Digit Sequence)",
    "Rule: Within a week, Open digits of consecutive days form a "
    "sequential pattern (e.g., 1,2,3 or 7,8,9). Tracks how often "
    "3+ consecutive open digits appear within the same week.",
    "Sequence"
)
def _band_week(week: Dict) -> Optional[bool]:
    opens = []
    for d in DAY_ORDER:
        o = _open_digit(week, d)
        if o is not None:
            opens.append(o)
    if len(opens) < 3:
        return None
    # Check any 3 consecutive values in sorted opens
    s = sorted(set(opens))
    for i in range(len(s) - 2):
        if s[i+1] == s[i]+1 and s[i+2] == s[i]+2:
            return True
    return False


# ---- 8. Line Ka Order (Ascending/Descending Jodi sequence) ---------
@trick(
    "Line Ka Order (Jodi Ascending/Descending in Week)",
    "Rule: Jodis within a week are in ascending or descending order "
    "Mon→Sat (at least 4 days). E.g., 12,23,34,45 = ascending line.",
    "Line Order"
)
def _line_order(week: Dict) -> Optional[bool]:
    jodis = []
    for d in DAY_ORDER:
        j = _jodi(week, d)
        if j:
            jodis.append(int(j))
    if len(jodis) < 4:
        return None
    asc = all(jodis[i] <= jodis[i+1] for i in range(len(jodis)-1))
    desc = all(jodis[i] >= jodis[i+1] for i in range(len(jodis)-1))
    return asc or desc


# ---- 9. Jodi Ka Jodbhav (Sum of consecutive day jodis = next jodi) -
@trick(
    "Jodi Ka Jodbhav (Digit Sum of Two Jodis → Next Jodi)",
    "Rule: (Open_day1 + Open_day2) mod 10 = Open of day3. "
    "Tracks how often 3 consecutive days follow this addition pattern.",
    "Jodbhav"
)
def _jodbhav(week: Dict) -> Optional[bool]:
    days_present = [d for d in DAY_ORDER if _jodi(week, d)]
    if len(days_present) < 3:
        return None
    hits = 0
    checks = 0
    for i in range(len(days_present) - 2):
        d1, d2, d3 = days_present[i], days_present[i+1], days_present[i+2]
        o1 = _open_digit(week, d1)
        o2 = _open_digit(week, d2)
        o3 = _open_digit(week, d3)
        if o1 is not None and o2 is not None and o3 is not None:
            if (o1 + o2) % 10 == o3:
                hits += 1
            checks += 1
    if checks == 0:
        return None
    return hits >= 1


# ---- 10. Cross Line Dekho (Open of day N = Close of day N+2) --------
@trick(
    "Cross Line Dekho (Open of Day = Close 2 Days Later)",
    "Rule: Open digit of Monday = Close digit of Wednesday (cross-diagonal). "
    "Same for Tue→Thu, Wed→Fri, Thu→Sat. Tracks cross-line matches.",
    "Cross Line"
)
def _cross_line(week: Dict) -> Optional[bool]:
    pairs = [("Mon","Wed"), ("Tue","Thu"), ("Wed","Fri"), ("Thu","Sat")]
    hits = 0
    checks = 0
    for d1, d2 in pairs:
        o = _open_digit(week, d1)
        c = _close_digit(week, d2)
        if o is not None and c is not None:
            checks += 1
            if o == c:
                hits += 1
    if checks == 0:
        return None
    return hits >= 2


# ---- 11. Achuk Sangam Scheme (Open of Mon = Close of Sat same week) -
@trick(
    "Achuk Sangam Scheme (Mon Open = Sat Close)",
    "Rule: Open digit of Monday equals Close digit of Saturday in the same week. "
    "This 'sangam' (union) is considered a strong signal.",
    "Sangam"
)
def _achuk_sangam(week: Dict) -> Optional[bool]:
    mon_open = _open_digit(week, "Mon")
    sat_close = _close_digit(week, "Sat")
    if mon_open is None or sat_close is None:
        return None
    return mon_open == sat_close


# ---- 12. Fix Figure Kalyan (Digit 1 appears every week on Wed) ------
@trick(
    "Fix Figure Kalyan (Most Frequent Open Digit = Week's Dominant Figure)",
    "Rule: One digit (0-9) appears as Open digit on 3+ days in the same week. "
    "That digit is the 'fix figure' of the week. Tracks how often there's a dominant digit.",
    "Fix Figure"
)
def _fix_figure(week: Dict) -> Optional[bool]:
    from collections import Counter
    opens = [_open_digit(week, d) for d in DAY_ORDER]
    opens = [o for o in opens if o is not None]
    if len(opens) < 3:
        return None
    freq = Counter(opens)
    return max(freq.values()) >= 3


# ---- 13. Milan Day Jodi se Milan Night me Achuk Ank ------------------
@trick(
    "Milan Day Jodi se Milan Night me Achuk Ank",
    "Rule: When MILAN DAY has Jodi 22, MILAN NIGHT on the same day must have figure 9 or 7 (or Jodi 97). "
    "When MILAN DAY has Jodi 27, 72, or 77, MILAN NIGHT must have figure 2, 7, 4, or 9.",
    "Milan Day/Night",
    marathi_name="मिलन डे जोडीवरून मिलन नाईट अचूक अंक",
    marathi_desc="नियम: जेव्हा मिलन डे मध्ये 22 जोडी येते, तेव्हा त्याच दिवशी मिलन नाईट मध्ये 9 किंवा 7 हा अंक (किंवा 97 जोडी) येतो. "
                 "तसेच जर मिलन डे मध्ये 27, 72 किंवा 77 जोडी आली, तर मिलन नाईट मध्ये 2, 7, 4 किंवा 9 यापैकी अचूक अंक येतो."
)
def _milan_day_to_night(week: Dict, night_map: Optional[Dict] = None) -> Optional[bool]:
    if not night_map:
        return None
    dr = week.get("date_range", "")
    start_date = dr.split()[0] if " to " in dr else dr
    
    triggers = {
        "22": [9, 7],
        "27": [2, 7, 4, 9],
        "72": [2, 7, 4, 9],
        "77": [2, 7, 4, 9]
    }
    
    found_trigger = False
    all_passed = True
    
    for d in DAY_ORDER:
        j_day = _jodi(week, d)
        if j_day in triggers:
            j_night = night_map.get((start_date, d))
            if j_night and j_night.isdigit() and len(j_night) == 2:
                found_trigger = True
                target_figs = triggers[j_day]
                n_o, n_c = int(j_night[0]), int(j_night[1])
                is_hit = (n_o in target_figs) or (n_c in target_figs) or (j_day == "22" and j_night == "97")
                if not is_hit:
                    all_passed = False
    
    if not found_trigger:
        return None
    return all_passed


# ---- 14. Sardarji Ke Figure (Cut digit of Mon Open = Thu Close) -----
@trick(
    "Sardarji Ke Figure (Cut of Mon Open = Thu Close)",
    "Rule: The cut complement of Monday's Open digit equals Thursday's Close digit. "
    "Cut pairs: 0↔5, 1↔6, 2↔7, 3↔8, 4↔9.",
    "Cut Digit"
)
def _sardarji(week: Dict) -> Optional[bool]:
    mon_open = _open_digit(week, "Mon")
    thu_close = _close_digit(week, "Thu")
    if mon_open is None or thu_close is None:
        return None
    return CUT[mon_open] == thu_close


# ---- 15. Daily Figure Trick I (Previous day close = current day open) 
@trick(
    "Daily Figure Trick I (Yesterday Close = Today Open)",
    "Rule: Close digit of the previous day equals Open digit of the current day. "
    "E.g., Mon close=3 → Tue open=3. Tracks consecutive day carry-over.",
    "Daily Figure"
)
def _daily_fig1(week: Dict) -> Optional[bool]:
    hits = 0
    checks = 0
    for i in range(len(DAY_ORDER) - 1):
        d1, d2 = DAY_ORDER[i], DAY_ORDER[i+1]
        c1 = _close_digit(week, d1)
        o2 = _open_digit(week, d2)
        if c1 is not None and o2 is not None:
            checks += 1
            if c1 == o2:
                hits += 1
    if checks == 0:
        return None
    return hits >= 2


# ---- 16. Daily Figure Trick II (Cut of previous close = current open)
@trick(
    "Daily Figure Trick II (Cut of Yesterday Close = Today Open)",
    "Rule: Cut complement of previous day's Close = current day's Open. "
    "E.g., Mon close=3 → Tue open=8 (since 3↔8). Tracks cut carry-over.",
    "Daily Figure"
)
def _daily_fig2(week: Dict) -> Optional[bool]:
    hits = 0
    checks = 0
    for i in range(len(DAY_ORDER) - 1):
        d1, d2 = DAY_ORDER[i], DAY_ORDER[i+1]
        c1 = _close_digit(week, d1)
        o2 = _open_digit(week, d2)
        if c1 is not None and o2 is not None:
            checks += 1
            if CUT[c1] == o2:
                hits += 1
    if checks == 0:
        return None
    return hits >= 2


# ---- 17. Daily Figure Trick III (Previous open = current close) -----
@trick(
    "Daily Figure Trick III (Yesterday Open = Today Close)",
    "Rule: Open digit of previous day equals Close digit of current day. "
    "E.g., Mon open=5 → Tue close=5.",
    "Daily Figure"
)
def _daily_fig3(week: Dict) -> Optional[bool]:
    hits = 0
    checks = 0
    for i in range(len(DAY_ORDER) - 1):
        d1, d2 = DAY_ORDER[i], DAY_ORDER[i+1]
        o1 = _open_digit(week, d1)
        c2 = _close_digit(week, d2)
        if o1 is not None and c2 is not None:
            checks += 1
            if o1 == c2:
                hits += 1
    if checks == 0:
        return None
    return hits >= 2


# ---- 18. Raise Karke Khele I (Add 1 to previous Jodi to get next) --
@trick(
    "Raise Karke Khele I (Jodi +1 each day)",
    "Rule: Each day's jodi = previous day's jodi + 1 (mod 100). "
    "E.g., Mon=23 → Tue=24 → Wed=25. Tracks ascending +1 sequences.",
    "Raise Series"
)
def _raise1(week: Dict) -> Optional[bool]:
    hits = 0
    checks = 0
    for i in range(len(DAY_ORDER) - 1):
        d1, d2 = DAY_ORDER[i], DAY_ORDER[i+1]
        j1 = _jodi(week, d1)
        j2 = _jodi(week, d2)
        if j1 is not None and j2 is not None:
            checks += 1
            if (int(j1) + 1) % 100 == int(j2):
                hits += 1
    if checks == 0:
        return None
    return hits >= 2


# ---- 19. Raise Karke Khele II (Add 11 to previous Jodi) -----------
@trick(
    "Raise Karke Khele II (Jodi +11 each day)",
    "Rule: Each day's jodi = previous day's jodi + 11 (mod 100). "
    "E.g., Mon=12 → Tue=23 → Wed=34. Tracks ascending +11 diagonal sequences.",
    "Raise Series"
)
def _raise11(week: Dict) -> Optional[bool]:
    hits = 0
    checks = 0
    for i in range(len(DAY_ORDER) - 1):
        d1, d2 = DAY_ORDER[i], DAY_ORDER[i+1]
        j1 = _jodi(week, d1)
        j2 = _jodi(week, d2)
        if j1 is not None and j2 is not None:
            checks += 1
            if (int(j1) + 11) % 100 == int(j2):
                hits += 1
    if checks == 0:
        return None
    return hits >= 2


# ---- 20. Daily Figure Trick IV (Reverse of jodi = next day jodi) ---
@trick(
    "Daily Figure Trick IV (Reverse Jodi Next Day)",
    "Rule: Reverse of current day's Jodi = next day's Jodi. "
    "E.g., Mon=23 → Tue=32. Tracks day-to-day jodi reversals.",
    "Daily Figure"
)
def _daily_fig4(week: Dict) -> Optional[bool]:
    hits = 0
    checks = 0
    for i in range(len(DAY_ORDER) - 1):
        d1, d2 = DAY_ORDER[i], DAY_ORDER[i+1]
        j1 = _jodi(week, d1)
        j2 = _jodi(week, d2)
        if j1 and j2:
            checks += 1
            if j1[::-1] == j2:
                hits += 1
    if checks == 0:
        return None
    return hits >= 2


# ---- 21. Daily Figure Trick V (Sum of open+close = next day open) --
@trick(
    "Daily Figure Trick V (Open+Close Sum Digit = Next Open)",
    "Rule: (Open + Close) mod 10 of current day = Open digit of next day. "
    "E.g., Mon jodi=23 → 2+3=5 → Tue open=5.",
    "Daily Figure"
)
def _daily_fig5(week: Dict) -> Optional[bool]:
    hits = 0
    checks = 0
    for i in range(len(DAY_ORDER) - 1):
        d1, d2 = DAY_ORDER[i], DAY_ORDER[i+1]
        j1 = _jodi(week, d1)
        o2 = _open_digit(week, d2)
        if j1 and o2 is not None:
            s = (int(j1[0]) + int(j1[1])) % 10
            checks += 1
            if s == o2:
                hits += 1
    if checks == 0:
        return None
    return hits >= 2


# ---- 22. 4-Markets (MD-KA-MN-MAIN) Mon-Tue Jodi / Bracket Group Repeat ----
@trick(
    "4-Markets (MD-KA-MN-MAIN) Mon-Tue Jodi Repeat",
    "Rule: Across 4 key markets (Milan Day, Kalyan, Milan Night, Main Bazar), Monday's Jodi or its 8-Jodi Family Bracket Group repeats on Tuesday among these 4 games.",
    "Cross Market / 4-Markets",
    marathi_name="४ मार्केट्स (MD, KA, MN, MAIN) सोम-मंगळ जोडी रिपीट",
    marathi_desc="नियम: मिलन डे (MD), कल्याण (KA), मिलन नाईट (MN) आणि मेन बाजार (MAIN) या ४ प्रमुख बाजारांमध्ये सोमवारची जोडी किंवा तिचा ८-फॅमिली ब्रॅकेट ग्रुप मंगळवारी याच ४ बाजारांमध्ये रिपीट होतो."
)
def _four_markets_mon_tue_repeat(week: Dict, four_markets_map: Optional[Dict] = None) -> Optional[bool]:
    if not four_markets_map:
        return None
    dr = week.get("date_range", "")
    start_date = dr.split()[0] if " to " in dr else dr
    
    mon_jodis = []
    tue_jodis = []
    
    for m in ["MILAN DAY", "KALYAN", "MILAN NIGHT", "MAIN BAZAR"]:
        jm = four_markets_map.get((m, start_date, "Mon"))
        if jm and jm.isdigit() and len(jm) == 2:
            mon_jodis.append(jm)
        jt = four_markets_map.get((m, start_date, "Tue"))
        if jt and jt.isdigit() and len(jt) == 2:
            tue_jodis.append(jt)
            
    if len(mon_jodis) < 2 or len(tue_jodis) < 2:
        return None
        
    from src.config import get_jodi_family
    
    for j1 in mon_jodis:
        fam1 = set(get_jodi_family(j1))
        for j2 in tue_jodis:
            if j2 in fam1:
                return True
    return False


# ============================================================
# TRICK ANALYZER ENGINE
# ============================================================

class TrickAnalyzer:
    """
    Runs all tricks against historical weekly grid for any market.
    Returns pass-rate, recent streak, and per-week results.
    """

    def __init__(self, db: Optional[MatkaDatabase] = None):
        self.db = db or MatkaDatabase()

    def get_grid(self, market: str, max_weeks: int = 200) -> List[Dict[str, Any]]:
        df = self.db.get_market_results(market, limit=max_weeks * 7)
        if df.empty:
            return []
        df = df.sort_values("id", ascending=True)
        grid = []
        for dr, grp in df.groupby("date_range", sort=False):
            row = {"date_range": dr, "days": {}}
            for _, r in grp.iterrows():
                row["days"][r["day_of_week"]] = {
                    "jodi": str(r["jodi"]),
                    "open_panna": str(r["open_panna"]),
                    "close_panna": str(r["close_panna"]),
                    "is_red": int(r["is_red_jodi"]),
                }
            grid.append(row)
        return grid

    def get_milan_night_map(self) -> Dict[Tuple[str, str], str]:
        if not hasattr(self, "_milan_night_map"):
            df_night = self.db.get_market_results("MILAN NIGHT", limit=3000)
            m = {}
            for _, r in df_night.iterrows():
                dr = str(r["date_range"])
                start_date = dr.split()[0] if " to " in dr else dr
                day = str(r["day_of_week"])
                m[(start_date, day)] = str(r["jodi"])
            self._milan_night_map = m
        return self._milan_night_map

    def get_4markets_map(self) -> Dict[Tuple[str, str, str], str]:
        if not hasattr(self, "_four_markets_map"):
            m = {}
            for market in ["MILAN DAY", "KALYAN", "MILAN NIGHT", "MAIN BAZAR"]:
                df = self.db.get_market_results(market, limit=3000)
                for _, r in df.iterrows():
                    dr = str(r["date_range"])
                    start_date = dr.split()[0] if " to " in dr else dr
                    day = str(r["day_of_week"])
                    m[(market, start_date, day)] = str(r["jodi"])
            self._four_markets_map = m
        return self._four_markets_map

    def analyze_trick(
        self, trick: Dict[str, Any], grid: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Run one trick across all weeks and return stats."""
        import inspect
        fn = trick["check"]
        sig = inspect.signature(fn)
        needs_prev = "prev_week" in sig.parameters
        needs_next = "next_week" in sig.parameters
        needs_night_map = "night_map" in sig.parameters
        needs_four_markets = "four_markets_map" in sig.parameters

        results = []
        for i, week in enumerate(grid):
            kwargs = {}
            if needs_prev:
                kwargs["prev_week"] = grid[i-1] if i > 0 else None
            if needs_next:
                kwargs["next_week"] = grid[i+1] if i < len(grid)-1 else None
            if needs_night_map:
                kwargs["night_map"] = self.get_milan_night_map()
            if needs_four_markets:
                kwargs["four_markets_map"] = self.get_4markets_map()
            try:
                r = fn(week, **kwargs)
            except Exception:
                r = None
            results.append({
                "date_range": week.get("date_range", ""),
                "result": r,
            })

        valid = [r for r in results if r["result"] is not None]
        passes = [r for r in valid if r["result"] is True]
        fails  = [r for r in valid if r["result"] is False]

        pass_rate = round(len(passes) / len(valid) * 100, 1) if valid else 0.0

        # Current streak (from latest week backwards)
        streak = 0
        streak_type = "—"
        for r in reversed(results):
            if r["result"] is None:
                continue
            if streak == 0:
                streak_type = "✅ PASS" if r["result"] else "❌ FAIL"
            if (r["result"] and streak_type.startswith("✅")) or \
               (not r["result"] and streak_type.startswith("❌")):
                streak += 1
            else:
                break

        # Last 8 results for sparkline
        last8 = [r["result"] for r in results[-8:] if r["result"] is not None]

        return {
            "trick_name": trick["name"],
            "category": trick.get("category", ""),
            "description": trick["description"],
            "total_weeks": len(valid),
            "passes": len(passes),
            "fails": len(fails),
            "pass_rate": pass_rate,
            "current_streak": streak,
            "streak_type": streak_type,
            "last8": last8,
            "latest_result": results[-1]["result"] if results else None,
            "latest_date": results[-1]["date_range"] if results else "",
        }

    def analyze_all(self, market: str) -> List[Dict[str, Any]]:
        """Run ALL tricks for a market and return sorted by pass_rate desc."""
        grid = self.get_grid(market)
        if not grid:
            return []
        milan_day_grid = None
        kalyan_grid = None
        results = []
        for trick in TRICKS:
            if trick.get("category") == "Milan Day/Night" and market != "MILAN DAY":
                if milan_day_grid is None:
                    milan_day_grid = self.get_grid("MILAN DAY")
                t_grid = milan_day_grid or grid
            elif trick.get("category") == "Cross Market / 4-Markets" and market != "KALYAN":
                if kalyan_grid is None:
                    kalyan_grid = self.get_grid("KALYAN")
                t_grid = kalyan_grid or grid
            else:
                t_grid = grid
            r = self.analyze_trick(trick, t_grid)
            r["market"] = market
            results.append(r)
        results.sort(key=lambda x: x["pass_rate"], reverse=True)
        return results

    def get_4markets_recent_analysis(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Returns structured comparison of recent weeks for the 4-markets Mon-Tue trick."""
        from src.config import get_jodi_family
        m_map = self.get_4markets_map()
        grid_kalyan = self.get_grid("KALYAN", max_weeks=limit * 2)
        
        records = []
        for w in reversed(grid_kalyan):
            dr = w.get("date_range", "")
            s_date = dr.split()[0] if " to " in dr else dr
            
            mon = {
                "MD": m_map.get(("MILAN DAY", s_date, "Mon"), "--"),
                "KA": m_map.get(("KALYAN", s_date, "Mon"), "--"),
                "MN": m_map.get(("MILAN NIGHT", s_date, "Mon"), "--"),
                "MU": m_map.get(("MAIN BAZAR", s_date, "Mon"), "--"),
            }
            tue = {
                "MD": m_map.get(("MILAN DAY", s_date, "Tue"), "--"),
                "KA": m_map.get(("KALYAN", s_date, "Tue"), "--"),
                "MN": m_map.get(("MILAN NIGHT", s_date, "Tue"), "--"),
                "MU": m_map.get(("MAIN BAZAR", s_date, "Tue"), "--"),
            }
            
            # Check valid
            mon_valid = [v for v in mon.values() if v.isdigit()]
            tue_valid = [v for v in tue.values() if v.isdigit()]
            if len(mon_valid) < 2 or len(tue_valid) < 2:
                continue
                
            exact_pairs = []
            family_pairs = []
            
            for m1, j1 in mon.items():
                if not j1.isdigit():
                    continue
                f1 = set(get_jodi_family(j1))
                for m2, j2 in tue.items():
                    if not j2.isdigit():
                        continue
                    if j1 == j2:
                        exact_pairs.append(f"{m1}({j1}) ➔ {m2}({j2}) [Exact]")
                    elif j2 in f1:
                        family_pairs.append(f"{m1}({j1}) ➔ {m2}({j2}) [Family]")
                        
            is_pass = bool(exact_pairs or family_pairs)
            records.append({
                "date_range": dr,
                "mon": mon,
                "tue": tue,
                "exact_pairs": exact_pairs,
                "family_pairs": family_pairs,
                "is_pass": is_pass
            })
            if len(records) >= limit:
                break
        return records

    def analyze_all_markets(self, markets: List[str]) -> Dict[str, List[Dict]]:
        """Run all tricks for multiple markets."""
        return {m: self.analyze_all(m) for m in markets}
