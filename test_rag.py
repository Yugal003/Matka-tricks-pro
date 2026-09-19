import os
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath("."))

from src.storage.database import MatkaDatabase
from src.engine.statistics import MatkaStatistics
from src.engine.guessing import MatkaGuessingEngine
from src.agent.rag_agent import DpBossRAGAgent

def test_pipeline():
    print("=== Testing DpBoss RAG Pipeline ===")
    
    # 1. Database
    db = MatkaDatabase()
    live_df = db.get_all_live_results()
    print(f"[+] Total live markets recorded: {len(live_df)}")
    
    kalyan_df = db.get_market_results("KALYAN", limit=500)
    print(f"[+] Kalyan historical records in DB: {len(kalyan_df)}")
    assert len(kalyan_df) > 0, "Kalyan historical records should be present"
    
    # 2. Statistics
    stats = MatkaStatistics(db)
    summary = stats.get_market_summary("KALYAN")
    print(f"[+] Kalyan Hot Digits: {summary.get('hot_digits')}")
    print(f"[+] Kalyan Cold Digits: {summary.get('cold_digits')}")
    print(f"[+] Kalyan Top Jodis: {summary.get('top_jodis')}")
    
    # 3. Guessing Engine
    guessing = MatkaGuessingEngine(stats)
    guesses = guessing.generate_guesses("KALYAN", day_of_week="Mon")
    print(f"[+] Generated OTC Digits: {guesses['otc_digits']}")
    print(f"[+] Generated Strong Jodis: {guesses['strong_jodis']}")
    print(f"[+] Recommended Panas: {list(guesses['panna_charts'].keys())}")
    
    # 4. RAG Agent
    agent = DpBossRAGAgent()
    query = "Analyze Kalyan chart and give OTC guessing for Monday"
    response = agent.generate_response(query)
    print(f"[+] RAG Agent Provider: {response['provider']}")
    print(f"[+] Response Snippet:\n{response['text'][:300]}...")
    
    print("\n✅ All tests passed successfully!")

if __name__ == "__main__":
    test_pipeline()
