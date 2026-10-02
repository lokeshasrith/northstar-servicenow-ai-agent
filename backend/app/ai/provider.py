from dataclasses import dataclass
import re


@dataclass
class Understanding:
    category: str
    subcategory: str
    summary: str
    confidence: float
    recommended_action: str
    signals: list[str]
    ambiguous: bool = False


class MockLLMProvider:
    """Safe local classifier. It suggests labels; policy decides whether to act."""
    rules = [
        ("Security", "Incident", ("phishing", "malware", "breach", "compromised", "ransomware"), .94),
        ("Authentication", "Account", ("password expired", "account locked", "account is locked", "cannot log in", "login failed"), .91),
        ("Network", "VPN", ("vpn", "virtual private network"), .94),
        ("Network", "DNS", ("dns", "resolve domain", "name resolution"), .90),
        ("Database", "Connectivity", ("database", "sql", "connection timeout"), .90),
        ("Software", "Email", ("outlook", "email", "mailbox"), .90),
        ("Access Management", "Permissions", ("shared drive", "access denied", "permission", "shared folder"), .87),
        ("Hardware", "Endpoint", ("laptop", "overheating", "printer", "keyboard", "monitor"), .87),
        ("Cloud", "Service", ("cloud", "portal", "website", "web app", "service unavailable"), .82),
    ]

    def analyze(self, title: str, description: str) -> Understanding:
        text = f"{title} {description}".lower()
        hits = [(c, s, terms, conf) for c, s, terms, conf in self.rules if any(t in text for t in terms)]
        uncertainty = any(x in text for x in ("not sure", "unknown error", "don't understand", "do not understand", "multiple possible", "not enough information"))
        if not hits:
            return Understanding("Other", "Unknown", "Insufficient information to confidently classify this incident.", .32, "Gather diagnostic details and route to Service Desk.", [], True)
        hit = hits[0]
        ambiguous = len(hits) > 1 and hits[1][0] != hit[0]
        confidence = min(hit[3], .58) if ambiguous or uncertainty else hit[3]
        signals = [f"Matched incident terms for {hit[0]} / {hit[1]}"]
        if len(hits) > 1:
            signals.append("Additional category signals detected; human review may be needed")
        if uncertainty:
            signals.append("Description explicitly indicates uncertainty")
        summary = re.sub(r"\s+", " ", description).strip()[:220]
        return Understanding(hit[0], hit[1], summary, confidence, f"Review the {hit[0]} / {hit[1]} troubleshooting runbook.", signals, ambiguous or uncertainty)


class OpenAIProvider:
    """Provider adapter uses structured JSON output and fails closed on provider errors."""
    def __init__(self, api_key: str, model: str):
        self.api_key, self.model = api_key, model

    def analyze(self, title: str, description: str) -> Understanding:
        import httpx
        response = httpx.post("https://api.openai.com/v1/chat/completions", headers={"Authorization": f"Bearer {self.api_key}"}, timeout=20,
          json={"model": self.model, "response_format": {"type": "json_object"}, "messages": [
            {"role":"system","content":"Classify the IT incident and return ONLY JSON with category, subcategory, summary, confidence (0..1), recommended_action, signals (list), ambiguous (boolean). Never claim an action was performed. If unclear, use category Other, confidence below 0.6, ambiguous true."},
            {"role":"user","content":f"Title: {title}\nDescription: {description}"}]})
        response.raise_for_status()
        import json
        data = json.loads(response.json()["choices"][0]["message"]["content"])
        confidence = float(data.get("confidence", 0))
        if not 0 <= confidence <= 1:
            raise ValueError("Provider returned invalid confidence")
        category=str(data.get("category", "Other"))[:60]
        subcategory=str(data.get("subcategory", "General"))[:60]
        evidence=MockLLMProvider().analyze(title,description)
        # Provider self-confidence cannot raise the deterministic evidence ceiling.
        # Unsupported classifications are capped below the investigation threshold.
        compatible=category==evidence.category or (category=="Email" and evidence.category=="Software" and evidence.subcategory=="Email")
        safe_confidence=min(confidence,evidence.confidence) if compatible else min(confidence,0.59)
        signals=evidence.signals + ([] if compatible else ["LLM category did not match deterministic evidence"])
        summary=evidence.summary
        recommendation=f"Review curated {category} knowledge sources and validate findings with a human."
        return Understanding(category,subcategory,summary,safe_confidence,recommendation,signals,bool(data.get("ambiguous",False)) or evidence.ambiguous or not compatible)
