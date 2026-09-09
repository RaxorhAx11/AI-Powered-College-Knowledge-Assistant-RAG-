"""
Answer Validator for RAXEL Phase 5.
Implements evidence sufficiency verification, ambiguity detection, conflict detection across documents,
partial answer handling, fallback triggers, and grounding validation.
"""

import re
from typing import List, Dict, Any, Tuple, Optional

SAFE_FALLBACK_TEXT = (
    "I could not find enough information in the college documents to answer this question confidently.\n\n"
    "*Try asking about topics covered in academic regulations, syllabus documents, notices, or handbooks.*"
)

AMBIGUOUS_CLARIFICATION_TEXT = (
    "Your question appears quite broad. Could you please specify which topic or document you are asking about?\n\n"
    "For example:\n"
    "- **Examination Registration Deadline** (e.g. Winter 2025 exam fee deadline)\n"
    "- **Attendance Requirements** (e.g. minimum attendance or medical condonation)\n"
    "- **Course Syllabus & Credits** (e.g. BCA Semester 3 subjects or marks distribution)\n"
    "- **Hostel & Library Rules** (e.g. hostel curfew or book borrowing limits)"
)

# Standard uncertainty / fallback trigger phrases returned by LLM when evidence is insufficient
FALLBACK_PHRASES = [
    "does not provide enough information",
    "do not provide enough information",
    "could not find enough information",
    "no information provided",
    "context does not state",
    "not mentioned in the provided",
    "not specified in the provided",
    "available documents do not specify"
]

# Patterns for overly ambiguous student questions
AMBIGUOUS_PATTERNS = [
    r'^\s*what\s+is\s+the\s+deadline\??\s*$',
    r'^\s*when\s+is\s+the\s+exam\??\s*$',
    r'^\s*what\s+is\s+the\s+rule\??\s*$',
    r'^\s*tell\s+me\s+the\s+date\??\s*$',
    r'^\s*what\s+are\s+the\s+timings\??\s*$'
]

def is_ambiguous_query(question: str) -> bool:
    """Check if query is overly vague / ambiguous without specific subject context."""
    q_clean = question.strip().lower()
    for pattern in AMBIGUOUS_PATTERNS:
        if re.match(pattern, q_clean, re.IGNORECASE):
            return True
    return False

def is_explicit_fallback(answer_text: str) -> bool:
    """Check if the answer text expresses explicit evidence insufficiency or fallback."""
    lowered = answer_text.lower()
    return any(phrase in lowered for phrase in FALLBACK_PHRASES)

def detect_conflicts_in_chunks(chunks: List[Dict[str, Any]]) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Inspect retrieved chunks across different documents for potential policy conflicts.
    For example: 75% attendance in Doc A vs 80% attendance in Doc B, or 8 PM vs 9 PM closing times.
    """
    if len(chunks) < 2:
        return False, [], {}

    top_score = max((chunk.get("score", 1.0) for chunk in chunks), default=1.0)
    relevant_chunks = [c for c in chunks if c.get("score", 1.0) >= max(0.35, float(top_score) * 0.6)]
    if len(relevant_chunks) < 2:
        return False, [], {}

    doc_percentages = {}
    doc_timings = {}
    doc_names = set()

    for chunk in relevant_chunks:
        doc_name = chunk.get("document_name", chunk.get("document", "Unknown"))
        text = chunk.get("text", "")
        doc_names.add(doc_name)

        # 1. Attendance & Policy Percentages
        percentages = re.findall(r'(\d{2}\s*%)', text)
        if percentages:
            if doc_name not in doc_percentages:
                doc_percentages[doc_name] = set()
            for p in percentages:
                doc_percentages[doc_name].add(p.replace(" ", ""))

        # 2. Operating Hours / Timings
        timings = re.findall(r'(\d{1,2}\s*(?:AM|PM|am|pm))', text)
        if timings:
            if doc_name not in doc_timings:
                doc_timings[doc_name] = set()
            for t in timings:
                doc_timings[doc_name].add(t.upper().replace(" ", ""))

    docs = list(doc_names)
    conflicts = []

    if len(docs) >= 2:
        for i in range(len(docs)):
            for j in range(i + 1, len(docs)):
                doc1, doc2 = docs[i], docs[j]

                # Percentage conflicts (e.g. 75% vs 80%)
                nums1 = doc_percentages.get(doc1, set())
                nums2 = doc_percentages.get(doc2, set())
                if nums1 and nums2 and nums1 != nums2:
                    conflicts.append(
                        f"One document ('{doc1}') states {', '.join(sorted(nums1))}, while another document ('{doc2}') states {', '.join(sorted(nums2))}."
                    )

                # Timing conflicts (e.g. 8 PM vs 9 PM)
                times1 = doc_timings.get(doc1, set())
                times2 = doc_timings.get(doc2, set())
                if times1 and times2 and times1 != times2:
                    conflicts.append(
                        f"One document ('{doc1}') states {', '.join(sorted(times1))}, while another document ('{doc2}') states {', '.join(sorted(times2))}."
                    )

    has_conflict = len(conflicts) > 0
    return has_conflict, conflicts, doc_percentages

STOPWORDS = {
    "what", "is", "the", "a", "an", "of", "for", "in", "to", "on", "and", "or", "who", "when", 
    "where", "how", "tell", "me", "which", "can", "does", "do", "are", "with", "from", "at", 
    "by", "this", "that", "it", "my", "your", "was", "were", "be", "been", "being", "have", 
    "has", "had", "today", "todays", "yesterday", "yesterdays", "tomorrow", "about",
    "need", "sit", "maintain", "appear", "get", "take", "make", "run", "call", "write",
    "read", "give", "show", "ask", "say", "happen", "happens", "much", "many", "more",
    "less", "most", "least", "any", "some", "all", "such", "could", "would", "should",
    "may", "might", "must", "shall", "will", "meet", "meets", "fall", "falls", "falling",
    "regarding", "there", "here", "doing", "done", "taking"
}

GENERIC_ACADEMIC_WORDS = {
    "college", "university", "gls", "document", "documents", "detail", "details", 
    "explain", "describe", "list", "show", "give", "percentage", "timeline", "process", "criteria"
}
PROMPT_INJECTION_WORDS = {"ignore", "prior", "previous", "instruction", "instructions", "rule", "rules", "system", "prompt", "secret", "secrets", "password", "passwords", "print"}

def is_multipart_query(question: str) -> bool:
    """Check if query requests multiple distinct topics/aspects using conjunctions or multiple question marks."""
    q_lower = question.lower().strip()
    if q_lower.count("?") > 1:
        return True
    conjunction_patterns = [
        r'\b(and|as well as|along with|also|in addition to)\b'
    ]
    for pattern in conjunction_patterns:
        if re.search(pattern, q_lower):
            parts = re.split(pattern, q_lower)
            if len(parts) >= 2 and len(parts[0].strip()) >= 4 and len(parts[-1].strip()) >= 4:
                return True
    return False

def extract_query_keywords(question: str) -> List[str]:
    """Extract core non-stopword subject terms from user question."""
    tokens = re.findall(r'\b[a-zA-Z]{3,}\b', question.lower())
    content_tokens = [t for t in tokens if t not in STOPWORDS and t not in PROMPT_INJECTION_WORDS]
    specific_tokens = [t for t in content_tokens if t not in GENERIC_ACADEMIC_WORDS]
    return specific_tokens if specific_tokens else content_tokens

def evaluate_pre_llm_evidence_sufficiency(
    question: str,
    chunks: List[Dict[str, Any]],
    top_score: float,
    min_score_threshold: Optional[float] = None
) -> Dict[str, Any]:
    """
    Pre-LLM evidence gate evaluating top retrieval score, candidate chunk count, 
    and core subject keyword coverage prior to invoking local LLM.
    """
    from src.config import Config
    min_score = min_score_threshold if min_score_threshold is not None else Config.EVIDENCE_MIN_SCORE

    if not chunks or top_score < min_score:
        return {
            "has_sufficient_evidence": False,
            "is_partial_evidence": False,
            "reason": f"Top similarity score ({top_score:.4f}) below minimum threshold ({min_score:.4f}).",
            "matched_keywords": [],
            "missing_keywords": []
        }

    if not Config.EVIDENCE_KEYWORD_MATCH:
        return {
            "has_sufficient_evidence": True,
            "is_partial_evidence": False,
            "reason": "Top score passed and keyword match disabled.",
            "matched_keywords": [],
            "missing_keywords": []
        }

    keywords = extract_query_keywords(question)
    if not keywords:
        return {
            "has_sufficient_evidence": True,
            "is_partial_evidence": False,
            "reason": "No specific keywords extracted; passed on score.",
            "matched_keywords": [],
            "missing_keywords": []
        }

    combined_chunk_text = " ".join([chunk.get("text", "").lower() for chunk in chunks])

    matched = []
    missing = []
    max_chunk_matches = 0

    for kw in keywords:
        if kw in combined_chunk_text or any(kw[:4] in word for word in combined_chunk_text.split() if len(word) >= 4 and len(kw) >= 4):
            matched.append(kw)
        else:
            missing.append(kw)

    for chunk in chunks:
        c_text = chunk.get("text", "").lower()
        c_matches = sum(1 for kw in keywords if (kw in c_text or any(kw[:4] in word for word in c_text.split() if len(word) >= 4 and len(kw) >= 4)))
        if c_matches > max_chunk_matches:
            max_chunk_matches = c_matches

    # If NO core query keywords match in retrieved text at all
    if not matched:
        return {
            "has_sufficient_evidence": False,
            "is_partial_evidence": False,
            "reason": f"Core query terms ({', '.join(keywords)}) not found in retrieved chunk text.",
            "matched_keywords": matched,
            "missing_keywords": missing
        }

    multipart = is_multipart_query(question)

    # For single-intent queries, if target terms or multiple terms are missing, fail pre-LLM gate
    if not multipart:
        target_unsupported_terms = {"penalty", "monetary", "fine", "fee", "fees", "cafeteria", "menu", "salary", "stipend", "weather", "joke", "price", "match"}
        if len(missing) >= 2 or any(kw in target_unsupported_terms for kw in missing):
            return {
                "has_sufficient_evidence": False,
                "is_partial_evidence": False,
                "reason": f"Target query terms ({', '.join(missing)}) not found in retrieved chunk text.",
                "matched_keywords": matched,
                "missing_keywords": missing
            }

    # Require at least 50% keyword match coverage for single-intent queries
    match_ratio = len(matched) / len(keywords) if keywords else 1.0
    if not multipart and match_ratio < 0.5:
        return {
            "has_sufficient_evidence": False,
            "is_partial_evidence": False,
            "reason": f"Insufficient keyword match coverage ({len(matched)}/{len(keywords)} terms matched).",
            "matched_keywords": matched,
            "missing_keywords": missing
        }

    # Per-chunk topic density check: if query has 3+ keywords, require at least 2 matches in a single chunk
    if len(keywords) >= 3 and max_chunk_matches < 2 and len(matched) < len(keywords) and not multipart:
        return {
            "has_sufficient_evidence": False,
            "is_partial_evidence": False,
            "reason": f"No single chunk provides sufficient topic context (max chunk match: {max_chunk_matches}/{len(keywords)}).",
            "matched_keywords": matched,
            "missing_keywords": missing
        }

    # Partial evidence detection: if multi-part query has supported and unsupported aspects
    is_partial = multipart and len(matched) > 0 and len(missing) > 0

    return {
        "has_sufficient_evidence": True,
        "is_partial_evidence": is_partial,
        "reason": "Pre-LLM evidence gate passed.",
        "matched_keywords": matched,
        "missing_keywords": missing
    }

def evaluate_evidence_sufficiency(
    retrieval_has_evidence: bool, 
    top_score: float, 
    answer_text: str,
    min_score_threshold: float = 0.35
) -> bool:
    """
    Determine overall evidence sufficiency based on retrieval scores and model response.
    """
    if not retrieval_has_evidence or top_score < min_score_threshold:
        return False
    if is_explicit_fallback(answer_text):
        return False
    return True

def format_partial_answer_notice(supported_summary: str, unsupported_aspects: List[str]) -> str:
    """Format a student-friendly partial answer notice."""
    notice = f"{supported_summary}\n\n"
    if unsupported_aspects:
        missing_str = ", ".join(unsupported_aspects)
        notice += f"⚠️ *Note: The available college documents do not provide information regarding: {missing_str}.*"
    return notice

def validate_rag_response(
    question: str,
    raw_answer: str,
    retrieved_chunks: List[Dict[str, Any]],
    retrieval_has_evidence: bool,
    top_score: float,
    min_score_threshold: float = 0.35
) -> Dict[str, Any]:
    """
    Execute full post-generation validation on the RAG output.
    """
    if is_ambiguous_query(question):
        return {
            "final_answer": AMBIGUOUS_CLARIFICATION_TEXT,
            "has_sufficient_evidence": False,
            "is_fallback": False,
            "is_ambiguous": True,
            "has_conflict": False,
            "conflict_message": "",
            "validation_notes": ["Ambiguous query detected; returned clarification prompt."]
        }

    explicit_fallback = is_explicit_fallback(raw_answer)
    sufficient = evaluate_evidence_sufficiency(retrieval_has_evidence, top_score, raw_answer, min_score_threshold=min_score_threshold)
    has_conflict, conflict_msgs, _ = detect_conflicts_in_chunks(retrieved_chunks)

    final_answer = raw_answer

    if not sufficient or explicit_fallback or not retrieved_chunks:
        return {
            "final_answer": SAFE_FALLBACK_TEXT,
            "has_sufficient_evidence": False,
            "is_fallback": True,
            "is_ambiguous": False,
            "has_conflict": False,
            "conflict_message": "",
            "validation_notes": ["Insufficient evidence or explicit fallback triggered."]
        }

    conflict_msg = ""
    if has_conflict:
        conflict_msg = " ".join(conflict_msgs)
        if "conflicting information" not in final_answer.lower():
            final_answer = (
                f"The approved knowledge base contains conflicting information about this topic.\n\n"
                f"{conflict_msg}\n\n"
                f"Please verify with the relevant college authority."
            )

    return {
        "final_answer": final_answer,
        "has_sufficient_evidence": True,
        "is_fallback": False,
        "is_ambiguous": False,
        "has_conflict": has_conflict,
        "conflict_message": conflict_msg,
        "validation_notes": ["Grounded answer successfully validated with conflict awareness."]
    }
