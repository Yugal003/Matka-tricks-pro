import re
from typing import Dict, Any, List
from src.storage.database import MatkaDatabase
from src.storage.vector_store import MatkaKnowledgeStore
from src.engine.statistics import MatkaStatistics
from src.engine.guessing import MatkaGuessingEngine
from src.config import POPULAR_MARKETS

class HybridRetriever:
    def __init__(self):
        self.db = MatkaDatabase()
        self.knowledge = MatkaKnowledgeStore()
        self.stats = MatkaStatistics(self.db)
        self.guessing = MatkaGuessingEngine(self.stats)

    def detect_market(self, query: str) -> str:
        """Detects mentioned market from user query."""
        query_upper = query.upper()
        for m in POPULAR_MARKETS:
            if m["name"] in query_upper or m["slug"] in query.lower():
                return m["name"]
        
        # Additional aliases
        if "KALYAN" in query_upper:
            return "KALYAN"
        elif "MILAN" in query_upper:
            return "MILAN DAY"
        elif "RAJDHANI" in query_upper:
            return "RAJDHANI NIGHT"
        elif "TIME" in query_upper:
            return "TIME BAZAR"
        elif "SRIDEVI" in query_upper:
            return "SRIDEVI"
        elif "MAIN" in query_upper:
            return "MAIN BAZAR"
            
        return "KALYAN"  # Default reference market

    def retrieve_context(self, user_query: str) -> Dict[str, Any]:
        """Combines structured numerical facts, guessing rules, and semantic context."""
        market = self.detect_market(user_query)
        
        # 1. Semantic Knowledge & Rules Search
        rules_context = self.knowledge.search(user_query, top_k=3)
        
        # 2. Historical Stats & Numerical Analysis
        stats_summary = self.stats.get_market_summary(market)
        
        # 3. Live/Latest Market Result
        live_df = self.db.execute_custom_query("SELECT * FROM live_status WHERE UPPER(market) = UPPER(?)", (market,))
        latest_live = live_df.to_dict(orient="records")[0] if not live_df.empty else {}

        # 4. Algorithmic Guesses
        guess_output = self.guessing.generate_guesses(market)

        # 5. Extract specific queries (e.g. if user asks for specific Jodi occurrences)
        specific_matches = []
        numbers_found = re.findall(r"\b\d{2}\b", user_query)
        if numbers_found:
            target_jodi = numbers_found[0]
            jodi_df = self.db.execute_custom_query(
                "SELECT date_range, day_of_week, open_panna, jodi, close_panna FROM historical_results WHERE UPPER(market) = UPPER(?) AND jodi = ? LIMIT 5",
                (market, target_jodi)
            )
            specific_matches = jodi_df.to_dict(orient="records")

        return {
            "query": user_query,
            "target_market": market,
            "latest_result": latest_live,
            "statistical_summary": stats_summary,
            "algorithmic_guesses": guess_output,
            "relevant_rules": rules_context,
            "specific_jodi_history": specific_matches
        }
