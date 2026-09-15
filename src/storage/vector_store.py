import json
import math
import re
from typing import List, Dict, Any, Tuple
from pathlib import Path
from src.config import KNOWLEDGE_PATH

DEFAULT_KNOWLEDGE = [
    {
        "id": "term-single-ank",
        "category": "terminology",
        "title": "Single Ank (Digit)",
        "content": "A Single Ank is any single digit from 0 to 9. In Matka games (like Kalyan, Milan, Rajdhani), guessing Open Ank or Close Ank refers to predicting this single winning digit."
    },
    {
        "id": "term-jodi",
        "category": "terminology",
        "title": "Jodi",
        "content": "A Jodi is a two-digit combination from 00 to 99 formed by joining the Open Ank (first digit) and Close Ank (second digit). For example, if Open is 3 and Close is 8, the Jodi is 38."
    },
    {
        "id": "term-patti-panna",
        "category": "terminology",
        "title": "Panna / Patti / Panel (220 Patti Chart)",
        "content": "A Panna or Patti is a 3-digit number. The sum of the 3 digits modulo 10 gives the Single Ank. Single Patti (SP) has 3 distinct digits (e.g., 125 -> sum 8). Double Patti (DP) has 2 repeating digits (e.g., 550 -> sum 0). Triple Patti (TP) has all 3 identical digits (e.g., 777 -> sum 1). There are 220 valid standard Patti combinations."
    },
    {
        "id": "term-cut-numbers",
        "category": "rules",
        "title": "Cut Number Formula",
        "content": "Cut number is the complementary or opposite digit defined as (Digit + 5) mod 10. Cut pairs: 0-5, 1-6, 2-7, 3-8, 4-9. When a predicted Ank misses, it frequently lands on its Cut number."
    },
    {
        "id": "term-jodi-family",
        "category": "rules",
        "title": "Family Jodi Rule",
        "content": "A Jodi Family consists of 8 complementary combinations created using the direct digits, reverse digits, and their cut numbers. For Jodi 24, its family members are 24, 29, 74, 79, 42, 47, 92, 97. If a pattern indicates a Jodi, playing the full Family Jodi is standard risk mitigation."
    },
    {
        "id": "term-red-jodi",
        "category": "terminology",
        "title": "Red Jodi and Half Red",
        "content": "Red Jodi occurs when both digits belong to the same number family or are identical (e.g., 00, 11, 22, 33, 44, 55, 66, 77, 88, 99) or when one digit is the cut of the other (05, 50, 16, 61, 27, 72, 38, 83, 49, 94)."
    },
    {
        "id": "trick-cross-line",
        "category": "tricks",
        "title": "Cross Line Weekly Trick",
        "content": "In cross-line calculation, the Open digit of the previous week Monday is added to the Close digit of Saturday. The resulting unit digit and its Cut number form the strong Open To Close (OTC) anchor for the current week."
    },
    {
        "id": "trick-difference-total",
        "category": "tricks",
        "title": "Jodi Total & Difference Method",
        "content": "Analyzing the difference between Open and Close digits over the last 10 draws helps identify recurring gaps (e.g., difference of 3 or 5) and repeating Jodi sum totals (e.g., total 10 or total 7)."
    },
    {
        "id": "trick-dhanvarsha",
        "category": "tricks",
        "title": "Dhanvarsha Daily Fix Open To Close",
        "content": "Dhanvarsha calculation generates 4 OTC (Open to Close) digits per market each day along with 4 supporting Panna and 8 Jodi pairs. If Open fails, the remaining OTC digits are strong contenders for Close."
    }
]

class MatkaKnowledgeStore:
    def __init__(self, storage_file: Path = KNOWLEDGE_PATH):
        self.storage_file = storage_file
        self.docs = []
        self.load()

    def load(self):
        if self.storage_file.exists():
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    self.docs = json.load(f)
            except Exception:
                self.docs = DEFAULT_KNOWLEDGE
        else:
            self.docs = DEFAULT_KNOWLEDGE
            self.save()

    def save(self):
        with open(self.storage_file, "w", encoding="utf-8") as f:
            json.dump(self.docs, f, indent=2, ensure_ascii=False)

    def add_document(self, doc_id: str, title: str, content: str, category: str = "general"):
        self.docs.append({
            "id": doc_id,
            "title": title,
            "content": content,
            "category": category
        })
        self.save()

    def search(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """BM25-style term frequency semantic relevance search."""
        if not self.docs:
            return []
            
        tokens = set(re.findall(r"\w+", query.lower()))
        if not tokens:
            return self.docs[:top_k]
            
        scored = []
        for doc in self.docs:
            text = f"{doc.get('title', '')} {doc.get('content', '')} {doc.get('category', '')}".lower()
            doc_words = re.findall(r"\w+", text)
            score = 0.0
            for t in tokens:
                count = doc_words.count(t)
                if count > 0:
                    score += (1.0 + math.log(count)) * (1.5 if t in doc.get("title", "").lower() else 1.0)
            
            scored.append((score, doc))
            
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k] if item[0] > 0] or self.docs[:top_k]
