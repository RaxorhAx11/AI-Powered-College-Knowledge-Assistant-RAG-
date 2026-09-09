import re
from typing import Dict, Any, Optional

ABBREVIATION_MAP = {
    r'\batt\b': 'attendance',
    r'\battendance req\b': 'attendance requirement',
    r'\bprof\b': 'professor',
    r'\bgpa\b': 'CGPA',
    r'\bcurfew\b': 'hostel curfew'
}

class QueryPreprocessor:
    """Lightweight query cleaner and term normalizer."""

    @staticmethod
    def preprocess(query: str) -> str:
        """
        Normalize query string while preserving essential numbers, percentages, 
        and academic terms.
        """
        if not query or not query.strip():
            return ""

        text = query.strip()

        # 1. Normalize multiple spaces & tabs
        text = re.sub(r'[ \t]+', ' ', text)

        # 2. Expand common student abbreviations cleanly
        for pattern, replacement in ABBREVIATION_MAP.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # 3. Trim extra punctuation around words while preserving hyphenated words and percentages
        text = re.sub(r'[!?.,;:]+$', '', text)
        return text.strip()

    @staticmethod
    def detect_query_intent(query: str, current_year: int = 2026) -> Dict[str, Any]:
        """
        Detect whether query is asking for CURRENT policy vs HISTORICAL policy.
        Returns {"is_historical": bool, "target_year": Optional[str], "is_ambiguous": bool}
        """
        if not query:
            return {"is_historical": False, "target_year": None, "is_ambiguous": False}
        
        q_lower = query.lower()
        years = re.findall(r'\b(20\d{2})\b', q_lower)
        past_words = ["was", "previous", "former", "historically", "old", "earlier", "back in"]
        has_past_word = any(w in q_lower for w in past_words)

        if years:
            y_int = int(years[0])
            if y_int < current_year:
                return {"is_historical": True, "target_year": str(y_int), "is_ambiguous": False}
            elif y_int == current_year:
                return {"is_historical": False, "target_year": str(y_int), "is_ambiguous": False}

        if has_past_word:
            return {"is_historical": True, "target_year": None, "is_ambiguous": False}

        return {"is_historical": False, "target_year": None, "is_ambiguous": False}
