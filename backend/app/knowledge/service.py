from pathlib import Path
import json
import re
from collections import Counter
from math import sqrt

ROOT = Path(__file__).resolve().parents[3] / "knowledge" / "runbooks"

class KnowledgeBase:
    def __init__(self) -> None:
        self.documents: list[dict] = []
        for path in sorted(ROOT.rglob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self.documents.extend(data if isinstance(data, list) else [data])
            except (OSError, json.JSONDecodeError):
                continue

    @staticmethod
    def tokens(value: str) -> Counter:
        return Counter(re.findall(r"[a-z0-9]{3,}", value.lower()))

    def search(self, query: str, limit: int = 5) -> list[dict]:
        q = self.tokens(query)
        if not q:
            return []
        scored = []
        for doc in self.documents:
            body = " ".join([doc.get("title", ""), doc.get("category", ""), doc.get("content", ""), " ".join(doc.get("keywords", []))])
            words = self.tokens(body)
            dot = sum(q[t] * words[t] for t in q)
            norm = sqrt(sum(v*v for v in q.values()) * sum(v*v for v in words.values())) or 1
            score = dot / norm
            if score > 0:
                scored.append({"id": doc["id"], "title": doc["title"], "source": doc.get("source", doc["id"]), "category": doc.get("category", "General"), "snippet": doc.get("content", "")[:240], "score": round(score, 3)})
        return sorted(scored, key=lambda x: x["score"], reverse=True)[:limit]

kb = KnowledgeBase()
