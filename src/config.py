import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "matka_records.db"
VECTOR_DIR = DATA_DIR / "vector_db"
KNOWLEDGE_PATH = DATA_DIR / "knowledge_base.json"

DATA_DIR.mkdir(exist_ok=True)
VECTOR_DIR.mkdir(exist_ok=True)

# Target Website
BASE_URL = "https://dpboss.tax"

# Key Markets
POPULAR_MARKETS = [
    {"name": "KALYAN", "slug": "kalyan", "open_time": "04:35 PM", "close_time": "06:35 PM"},
    {"name": "MILAN DAY", "slug": "milan-day", "open_time": "03:00 PM", "close_time": "05:00 PM"},
    {"name": "MILAN NIGHT", "slug": "milan-night", "open_time": "09:10 PM", "close_time": "11:10 PM"},
    {"name": "MAIN BAZAR", "slug": "main-bazar", "open_time": "10:00 PM", "close_time": "12:10 AM"},
    {"name": "TIME BAZAR", "slug": "time-bazar", "open_time": "01:00 PM", "close_time": "02:00 PM"},
    {"name": "SRIDEVI", "slug": "sridevi", "open_time": "11:35 AM", "close_time": "12:35 PM"},
    {"name": "SRIDEVI NIGHT", "slug": "sridevi-night", "open_time": "07:15 PM", "close_time": "08:15 PM"},
    {"name": "KALYAN NIGHT", "slug": "kalyan-night", "open_time": "09:40 PM", "close_time": "11:40 PM"},
    {"name": "MADHUR MORNING", "slug": "madhur-morning", "open_time": "11:30 AM", "close_time": "12:30 PM"},
    {"name": "MADHUR DAY", "slug": "madhur-day", "open_time": "01:30 PM", "close_time": "02:30 PM"},
    {"name": "MADHUR NIGHT", "slug": "madhur-night", "open_time": "08:30 PM", "close_time": "10:30 PM"},
    {"name": "RAJDHANI DAY", "slug": "rajdhani-day", "open_time": "03:00 PM", "close_time": "05:00 PM"},
    {"name": "RAJDHANI NIGHT", "slug": "rajdhani-night", "open_time": "09:35 PM", "close_time": "11:45 PM"},
    {"name": "SUPREME DAY", "slug": "supreme-day", "open_time": "03:35 PM", "close_time": "05:35 PM"},
    {"name": "SUPREME NIGHT", "slug": "supreme-night", "open_time": "08:45 PM", "close_time": "10:45 PM"},
]

# Cut Digits Map (Opposite Number in Matka Rules)
CUT_NUMBERS = {
    0: 5, 1: 6, 2: 7, 3: 8, 4: 9,
    5: 0, 6: 1, 7: 2, 8: 3, 9: 4
}

# Jodi Family Calculation Rules
# Family of Jodi XY = [XY, Cut(X)Y, XCut(Y), Cut(X)Cut(Y), YX, Cut(Y)X, YCut(X), Cut(Y)Cut(X)]
def get_jodi_family(jodi_str: str) -> list[str]:
    if len(jodi_str) != 2 or not jodi_str.isdigit():
        return [jodi_str]
    d1, d2 = int(jodi_str[0]), int(jodi_str[1])
    c1, c2 = CUT_NUMBERS[d1], CUT_NUMBERS[d2]
    
    variations = {
        f"{d1}{d2}", f"{c1}{d2}", f"{d1}{c2}", f"{c1}{c2}",
        f"{d2}{d1}", f"{c2}{d1}", f"{d2}{c1}", f"{c2}{c1}"
    }
    return sorted(list(variations))
