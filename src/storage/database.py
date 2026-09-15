import sqlite3
import pandas as pd
from typing import List, Dict, Any, Optional
from pathlib import Path
from src.config import DB_PATH, CUT_NUMBERS

class MatkaDatabase:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = str(db_path)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Historical results table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS historical_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market TEXT NOT NULL,
                date_range TEXT,
                day_of_week TEXT,
                open_panna TEXT,
                jodi TEXT NOT NULL,
                close_panna TEXT,
                open_digit INTEGER,
                close_digit INTEGER,
                jodi_total INTEGER,
                is_red_jodi INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Unique index to prevent duplicate records
            cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_market_date_day 
            ON historical_results(market, date_range, day_of_week, jodi)
            """)
            
            # Live market status
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS live_status (
                market TEXT PRIMARY KEY,
                raw_result TEXT,
                open_panna TEXT,
                jodi TEXT,
                close_panna TEXT,
                timing TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Daily Free Guessing / Tips
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS free_game_tips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market TEXT NOT NULL,
                fix_ank TEXT,
                recommended_panas TEXT,
                recommended_jodis TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Knowledge documents for RAG
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_docs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                title TEXT,
                content TEXT
            )
            """)
            
            conn.commit()

    def save_historical_records(self, records: List[Dict[str, Any]]) -> int:
        """Batch inserts historical records, calculating digits and jodi attributes."""
        inserted = 0
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for r in records:
                jodi = str(r.get("jodi", "")).strip()
                if not jodi or len(jodi) != 2 or not jodi.isdigit():
                    continue
                
                open_d = int(jodi[0])
                close_d = int(jodi[1])
                jodi_total = (open_d + close_d) % 10
                
                # Check red jodi (double digits or cut pairs: 05, 50, 16, 61, etc.)
                is_red = 1 if (open_d == close_d or CUT_NUMBERS.get(open_d) == close_d) else 0
                
                try:
                    cursor.execute("""
                    INSERT OR IGNORE INTO historical_results 
                    (market, date_range, day_of_week, open_panna, jodi, close_panna, open_digit, close_digit, jodi_total, is_red_jodi)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        r.get("market"),
                        r.get("date_range"),
                        r.get("day_of_week"),
                        r.get("open_panna", ""),
                        jodi,
                        r.get("close_panna", ""),
                        open_d,
                        close_d,
                        jodi_total,
                        is_red
                    ))
                    if cursor.rowcount > 0:
                        inserted += 1
                except Exception:
                    pass
            conn.commit()
        return inserted

    def save_live_results(self, live_list: List[Dict[str, Any]]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for item in live_list:
                cursor.execute("""
                INSERT INTO live_status (market, raw_result, open_panna, jodi, close_panna, timing, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(market) DO UPDATE SET
                    raw_result=excluded.raw_result,
                    open_panna=excluded.open_panna,
                    jodi=excluded.jodi,
                    close_panna=excluded.close_panna,
                    timing=excluded.timing,
                    updated_at=CURRENT_TIMESTAMP
                """, (
                    item.get("market"),
                    item.get("raw_result"),
                    item.get("open_panna"),
                    item.get("jodi"),
                    item.get("close_panna"),
                    item.get("timing")
                ))
            conn.commit()

    def get_market_results(self, market: str, limit: int = 100) -> pd.DataFrame:
        query = "SELECT * FROM historical_results WHERE UPPER(market) = UPPER(?) ORDER BY id DESC LIMIT ?"
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn, params=(market, limit))

    def get_all_live_results(self) -> pd.DataFrame:
        query = "SELECT * FROM live_status ORDER BY market ASC"
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn)

    def execute_custom_query(self, sql: str, params: tuple = ()) -> pd.DataFrame:
        with self.get_connection() as conn:
            return pd.read_sql_query(sql, conn, params=params)
