import re
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class DpBossParser:
    @staticmethod
    def parse_live_results(html_content: str) -> List[Dict[str, Any]]:
        """Parses current market results and timings from home page HTML."""
        soup = BeautifulSoup(html_content, "html.parser")
        results = []
        
        # Look for result cards inside .tkt-val containers
        for card in soup.select(".tkt-val > div"):
            h4 = card.find("h4")
            span = card.find("span")
            p_time = card.find("p")
            
            if not h4 or not span:
                continue
                
            market_name = h4.get_text(strip=True)
            raw_result = span.get_text(strip=True)
            timing = p_time.get_text(strip=True) if p_time else ""
            
            # Format usually: 570-29-126 or 350-8 or ***-**-***
            open_panna = ""
            jodi = ""
            close_panna = ""
            
            parts = raw_result.split("-")
            if len(parts) == 3:
                open_panna = parts[0].strip()
                jodi = parts[1].strip()
                close_panna = parts[2].strip()
            elif len(parts) == 2:
                open_panna = parts[0].strip()
                jodi = parts[1].strip()
                
            results.append({
                "market": market_name,
                "raw_result": raw_result,
                "open_panna": open_panna,
                "jodi": jodi,
                "close_panna": close_panna,
                "timing": timing
            })
            
        return results

    @staticmethod
    def parse_free_game_zone(html_content: str) -> List[Dict[str, Any]]:
        """Parses daily free guessing predictions and tips."""
        soup = BeautifulSoup(html_content, "html.parser")
        guesses = []
        
        for item in soup.select(".oc-3a-69"):
            market_elem = item.find("p", class_="g5a1")
            lines = item.find_all("p", class_="l9w2v")
            
            if not market_elem or not lines:
                continue
                
            market_name = market_elem.get_text(strip=True).replace("↪", "").strip()
            
            fix_ank = lines[0].get_text(strip=True) if len(lines) > 0 else ""
            panas = lines[1].get_text(strip=True) if len(lines) > 1 else ""
            jodis = lines[2].get_text(strip=True) if len(lines) > 2 else ""
            
            guesses.append({
                "market": market_name,
                "fix_ank": fix_ank,
                "recommended_panas": [p.strip() for p in panas.split("-") if p.strip() and p.strip() != "***"],
                "recommended_jodis": [j.strip() for j in jodis.split("-") if j.strip() and j.strip() != "**"]
            })
            
        return guesses

    @staticmethod
    def parse_weekly_tricks(html_content: str) -> Dict[str, Any]:
        """Parses weekly Patti, Line Open/Close and Jodi charts."""
        soup = BeautifulSoup(html_content, "html.parser")
        tricks = {"weekly_patti": [], "weekly_line": [], "weekly_jodi": []}
        
        for div in soup.select(".sun-col > div"):
            h4 = div.find("h4")
            if not h4:
                continue
            title = h4.get_text(strip=True)
            paragraphs = [p.get_text(strip=True) for p in div.find_all("p") if p.get_text(strip=True)]
            
            if "Patti Or Penal Chart" in title:
                tricks["weekly_patti"] = paragraphs
            elif "Line Open" in title:
                tricks["weekly_line"] = paragraphs
            elif "Jodi Chart" in title:
                tricks["weekly_jodi"] = paragraphs
                
        return tricks

    @staticmethod
    def parse_panel_chart(html_content: str, market_name: str) -> List[Dict[str, Any]]:
        """Parses historical panel chart records table from panel-chart-record/*.php."""
        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table", class_=lambda c: c and ("panel-chart" in c or "chart-table" in c))
        if not table:
            # Fallback to any table with tr/td
            table = soup.find("table")
            
        if not table:
            return []

        rows = []
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        
        for tr in table.find_all("tr"):
            tds = tr.find_all("td")
            if not tds or len(tds) < 4:
                continue
                
            date_range = tds[0].get_text(" ", strip=True)
            
            # Each day has 3 cells: Open Pana, Jodi, Close Pana
            idx = 1
            day_idx = 0
            while idx + 2 < len(tds) and day_idx < len(days):
                open_panna_raw = tds[idx].get_text("", strip=True)
                jodi_raw = tds[idx+1].get_text("", strip=True)
                close_panna_raw = tds[idx+2].get_text("", strip=True)
                
                # Clean up values (remove newlines / asterisks)
                open_panna = open_panna_raw.replace(" ", "").replace("\n", "")
                jodi = jodi_raw.replace(" ", "").replace("\n", "")
                close_panna = close_panna_raw.replace(" ", "").replace("\n", "")
                
                if jodi and jodi != "**" and not jodi.startswith("*"):
                    rows.append({
                        "market": market_name,
                        "date_range": date_range,
                        "day_of_week": days[day_idx],
                        "open_panna": open_panna if open_panna != "***" else "",
                        "jodi": jodi,
                        "close_panna": close_panna if close_panna != "***" else ""
                    })
                
                idx += 3
                day_idx += 1
                
        return rows
