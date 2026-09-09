"""
Citation Validator for RAXEL Phase 4.
Ensures citations originate exclusively from actual retrieved chunk metadata
and validates LLM outputs against hallucinated source names or invalid page numbers.
"""

import re
from typing import List, Dict, Any

def extract_programmatic_citations(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract unique (document, page) pairs programmatically from retrieved evidence chunks.
    Guarantees citations originate directly from vector store metadata.
    """
    seen = set()
    citations = []

    for chunk in chunks:
        doc = chunk.get("document_name", chunk.get("document", "Unknown Document"))
        page = chunk.get("page_number", chunk.get("page", 1))
        doc_type = chunk.get("document_type", "general")
        year = chunk.get("academic_year", chunk.get("version_str", "N/A"))
        score = chunk.get("score", 0.0)

        key = (doc, page)
        if key not in seen:
            seen.add(key)
            citations.append({
                "document": doc,
                "page": page,
                "document_type": doc_type,
                "academic_year": year,
                "score": score,
                "formatted": f"{doc} — Page {page}"
            })

    return citations

def validate_and_sanitize_answer_citations(raw_answer: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Inspect LLM response for inline citation markers and validate them against actual retrieved chunks.
    
    Returns:
        {
            "sanitized_answer": str,
            "validated_citations": List[Dict],
            "hallucinations_detected": List[str],
            "is_valid": bool
        }
    """
    valid_citations = extract_programmatic_citations(chunks)
    valid_docs = {c["document"].lower() for c in valid_citations}
    valid_doc_pages = {(c["document"].lower(), int(c["page"])) for c in valid_citations}

    hallucinations = []
    
    # 1. Search for regex patterns where LLM tries to cite files (e.g., "File.pdf — Page X" or "Document: File.pdf, Page X")
    pdf_pattern = re.compile(r'([A-Za-z0-9_\-]+\.pdf)(?:[^\d]+Page\s*(\d+))?', re.IGNORECASE)
    matches = pdf_pattern.findall(raw_answer)

    for match in matches:
        doc_found = match[0].strip()
        page_found = match[1].strip() if match[1] else None

        if doc_found.lower() not in valid_docs:
            hallucinations.append(f"Fake document citation: '{doc_found}'")
        elif page_found and (doc_found.lower(), int(page_found)) not in valid_doc_pages:
            hallucinations.append(f"Invalid page citation: '{doc_found}' Page {page_found}")

    # Clean up trailing LLM-invented "Sources:" or "Citations:" sections if present to enforce consistent UI presentation
    cleaned_answer = raw_answer
    sources_split = re.split(r'\n+\s*(?:Sources|Citations|References):\s*\n', raw_answer, flags=re.IGNORECASE)
    if len(sources_split) > 1:
        cleaned_answer = sources_split[0].strip()

    return {
        "sanitized_answer": cleaned_answer,
        "validated_citations": valid_citations,
        "hallucinations_detected": hallucinations,
        "is_valid": len(hallucinations) == 0
    }
