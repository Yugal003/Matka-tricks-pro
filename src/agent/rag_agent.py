import os
import json
from typing import Dict, Any, Optional
from src.engine.retriever import HybridRetriever

class DpBossRAGAgent:
    def __init__(self, api_key: Optional[str] = None):
        self.retriever = HybridRetriever()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.client = None
        
        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel("gemini-1.5-flash")
            except Exception:
                self.client = None

    def format_prompt(self, context: Dict[str, Any], query: str) -> str:
        market = context.get("target_market", "KALYAN")
        live = context.get("latest_result", {})
        stats = context.get("statistical_summary", {})
        guesses = context.get("algorithmic_guesses", {})
        rules = context.get("relevant_rules", [])
        
        rules_text = "\n".join([f"- **{r.get('title')}**: {r.get('content')}" for r in rules])
        
        prompt = f"""
You are an expert analytical AI Assistant for Satta Matka chart patterns and guessing methodologies based on DPBOSS (dpboss.tax) data.
You provide clear, structured, and mathematical pattern explanations, OTC (Open to Close) predictions, Jodi families, and Patti breakdowns.

--- CONTEXT FROM DPBOSS RETRIEVAL SYSTEM ---
Target Market: {market}
Latest Live Declared Result: {live.get('raw_result', 'N/A')} (Timing: {live.get('timing', 'N/A')})

Historical Frequency Statistics (Sample Size: {stats.get('total_records', 0)} draws):
- Hot Single Digits: {stats.get('hot_digits', [])}
- Cold Single Digits: {stats.get('cold_digits', [])}
- Top Frequent Jodis: {json.dumps(stats.get('top_jodis', {}))}
- Red Jodi Ratio: {stats.get('red_jodi_pct', 0)}%

Algorithmic Pattern Guessing for {market}:
- Strong 4-Digit OTC: {guesses.get('otc_digits', [])}
- Single Ank with Cut numbers: {', '.join(guesses.get('single_ank_tips', []))}
- Recommended 8 Jodis: {', '.join(guesses.get('strong_jodis', []))}
- Family Jodi Focus: Base {guesses.get('family_jodi_group', {}).get('base_jodi')} -> Family {guesses.get('family_jodi_group', {}).get('family', [])}
- Supporting Pana / Patti combinations: {json.dumps(guesses.get('panna_charts', {}))}

Relevant Domain Rules & Formulas:
{rules_text}
------------------------------------------

User Request: {query}

Please provide a well-structured, professional, and easy-to-read response including:
1. Direct answer / Analysis to the user query.
2. Formatted Guessing Card (Single OTC, Strong Jodi, Family Jodi, and Panel/Patti).
3. The underlying logic (Cut number, frequency, and pattern sum analysis).
4. A standard analytical disclaimer about mathematical probabilities.
"""
        return prompt

    def generate_response(self, user_query: str) -> Dict[str, Any]:
        """Runs the hybrid retrieval and generates LLM answer."""
        context = self.retriever.retrieve_context(user_query)
        prompt = self.format_prompt(context, user_query)
        
        # If Gemini API client is active, use it
        if self.client:
            try:
                response = self.client.generate_content(prompt)
                ai_text = response.text
                return {
                    "text": ai_text,
                    "context": context,
                    "provider": "Gemini 1.5 Flash"
                }
            except Exception as e:
                pass
                
        # High quality built-in analytical generator fallback
        return {
            "text": self.build_analytical_response(context, user_query),
            "context": context,
            "provider": "DpBoss Rule & Statistical Engine (Direct)"
        }

    def build_analytical_response(self, context: Dict[str, Any], query: str) -> str:
        market = context.get("target_market", "KALYAN")
        live = context.get("latest_result", {})
        stats = context.get("statistical_summary", {})
        guesses = context.get("algorithmic_guesses", {})
        
        otc = guesses.get("otc_digits", [1, 6, 2, 7])
        jodis = guesses.get("strong_jodis", [])
        panas = guesses.get("panna_charts", {})
        fam = guesses.get("family_jodi_group", {})
        
        otc_str = "-".join([str(x) for x in otc])
        jodi_str = " | ".join(jodis)
        
        panna_lines = []
        for digit, plist in panas.items():
            panna_lines.append(f"• **Ank {digit}**: {', '.join(plist)}")
        panna_text = "\n".join(panna_lines)

        response = f"""### 🎯 DpBoss Guessing & Pattern Analysis for **{market}**

**Latest Market Update:** `{live.get('raw_result', 'Live Update In Progress')}` *(Time: {live.get('timing', 'Standard Schedule')})*

---

#### 📌 1. Strong Open To Close (OTC)
```
🔥 OTC FIX ANK: [ {otc_str} ]
```
- **Primary Single Digits**: `{otc[0]}` and `{otc[2] if len(otc)>2 else (otc[0]+3)%10}`
- **Cut Support Digits**: `{otc[1] if len(otc)>1 else (otc[0]+5)%10}` and `{otc[3] if len(otc)>3 else (otc[2]+5)%10}`

---

#### 🎲 2. Top Recommended Jodi Pairs (8 Jodis)
```
{jodi_str}
```
- **Key Family Jodi ({fam.get('base_jodi')})**: `{', '.join(fam.get('family', []))}`

---

#### 📜 3. Recommended Patti / Panna (220 Patti Chart)
{panna_text}

---

#### 📊 4. Historical Statistical Rationale
1. **Frequency Weight**: Single Ank `{otc[0]}` and `{otc[1]}` show the highest combined appearance frequency in the last {stats.get('total_records', 100)} recorded draws.
2. **Cut Balance**: Matching primary digits with their 5-step Cut complements provides complete Open To Close coverage.
3. **Total Jodi Sum Pattern**: Expected total sum aligns with high-probability historical buckets (Total: `{guesses.get('confidence_factors', {}).get('top_frequent_total_sum', 7)}`).

> *Note: Satta Matka is based on probability and random draws. This RAG analysis presents statistical patterns and community formula aggregations for research and tracking.*
"""
        return response
