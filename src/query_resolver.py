"""
Query Context Resolver for RAXEL Phase 5.1 Step 3.
Resolves follow-up queries using conversation history (USER messages ONLY)
to construct standalone search queries for accurate retrieval while ensuring
that previous assistant answers NEVER serve as factual evidence.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Patterns identifying referential pronouns or follow-up starters
PRONOUN_PATTERNS = [
    r'\b(it|this|that|they|them|these|those|its|their|the same)\b',
    r'^\s*(what about|how about|does this|is there|what if|and what|what happens if|why|how about)\b'
]

# Core domain topic keywords to check for topic shifts
TOPIC_KEYWORDS = [
    "attendance", "hostel", "library", "bca", "syllabus", "exam", "exams", "examination",
    "grade", "grades", "cgpa", "gpa", "scholarship", "placement", "placements", "curfew",
    "timetable", "schedule", "notice", "circular", "fee", "fees", "registration",
    "condonation", "medical", "backlog", "backlogs", "borrowing", "regulation",
    "regulations", "handbook", "event", "fest", "canteen", "cafeteria", "mess",
    "wifi", "internet", "facility", "facilities"
]

def needs_resolution(question: str) -> bool:
    """Check if question contains referential terms or is a short follow-up."""
    q_lower = question.strip().lower()
    
    # Check if question has explicit referential terms or follow-up starters
    for pattern in PRONOUN_PATTERNS:
        if re.search(pattern, q_lower):
            return True
            
    # Short question with <= 4 words likely needs context if history is present
    words = q_lower.split()
    if len(words) <= 4 and not any(kw in q_lower for kw in ["hello", "hi", "help"]):
        return True
        
    return False

def is_topic_change(question: str, previous_user_query: str) -> bool:
    """
    Check if current question is a distinct topic change rather than a follow-up.
    If the question introduces a new distinct domain subject (e.g., hostel vs attendance)
    and doesn't use referential pronouns ('it', 'this', 'that', 'same'), it's a topic change.
    """
    q_lower = question.strip().lower()
    
    # If explicit referential pronouns or follow-up starters are present, it's a follow-up
    if re.search(r'\b(it|this|that|same|these|those|them)\b', q_lower):
        return False
    if re.search(r'^\s*(what about|how about|does this|is there|what if|and what|what happens if|why)\b', q_lower):
        return False
        
    current_topics = [kw for kw in TOPIC_KEYWORDS if kw in q_lower]
    prev_topics = [kw for kw in TOPIC_KEYWORDS if kw in previous_user_query.lower()]
    
    # If current question has a specific topic different from previous, it's a topic change
    if current_topics and not any(t in prev_topics for t in current_topics):
        return True
        
    return False

def extract_previous_user_topic(chat_history: List[Dict[str, str]]) -> Optional[str]:
    """
    Extract key topic phrase strictly from previous USER messages in history.
    NEVER inspect Assistant messages to prevent adopting misinformation.
    Combines core subject context (e.g. BCA-301) across multi-turn user messages.
    """
    if not chat_history:
        return None

    # Filter strictly user messages
    user_messages = [
        msg.get("content", "").strip() 
        for msg in chat_history 
        if msg.get("role", "").lower() == "user" and msg.get("content", "").strip()
    ]
    
    if not user_messages:
        return None
        
    # Get most recent user message
    last_msg = user_messages[-1]
    
    # If there are earlier user messages, check if an earlier message contains a specific course code / subject
    if len(user_messages) > 1:
        for prev_msg in reversed(user_messages[:-1]):
            # Check for course code (e.g., BCA-301) in earlier message
            course_match = re.search(r'\b[A-Za-z]{2,4}-\d{3}\b', prev_msg)
            if course_match:
                return course_match.group(0)
                
    return last_msg

def deterministic_query_rewrite(question: str, previous_user_query: str) -> str:
    """
    Perform deterministic query resolution by replacing referential pronouns
    or appending context from previous user question.
    """
    clean_prev = re.sub(
        r'^(what is|what are|tell me about|how many|when is|where is|explain|details on)\s+', 
        '', 
        previous_user_query.lower(), 
        flags=re.IGNORECASE
    ).strip('? ')
    
    q_text = question.strip()
    replacement = clean_prev if clean_prev.startswith("the ") else f"the {clean_prev}"
    
    # Replace pronouns cleanly if present
    if re.search(r'\b(it|this|that|them|these|those)\b', q_text, re.IGNORECASE):
        rep_text = f"{replacement} course" if re.search(r'\b[A-Za-z]{2,4}-\d{3}\b', replacement, re.IGNORECASE) else replacement
        resolved = re.sub(r'\bthe\s+(it|this|that|them|these|those)\b', rep_text, q_text, flags=re.IGNORECASE)
        resolved = re.sub(r'\b(it|this|that|them|these|those)\b', rep_text, resolved, flags=re.IGNORECASE)
        return resolved
        
    return f"{q_text.strip('?')} regarding {clean_prev}?"

def resolve_followup_query(
    question: str,
    chat_history: Optional[List[Dict[str, str]]] = None,
    llm=None
) -> Tuple[str, bool]:
    """
    Resolve a follow-up question using previous USER context into a standalone query.
    Returns (resolved_query, was_resolved).
    """
    if not chat_history:
        return question, False
        
    last_user_query = extract_previous_user_topic(chat_history)
    if not last_user_query:
        return question, False
        
    # Check if it's a clear topic change
    if is_topic_change(question, last_user_query):
        return question, False
        
    # Check if resolution is needed
    if not needs_resolution(question):
        return question, False

    # Perform lightweight LLM reformulation if LLM is provided AND operational
    if llm:
        try:
            conn = llm.check_connection() if hasattr(llm, "check_connection") else {"available": True}
            if conn.get("available", False):
                rewrite_prompt = (
                    f"Rewrite the current follow-up question into a single complete, standalone search question "
                    f"by incorporating the topic from the previous user question.\n"
                    f"Do NOT answer the question. Do NOT add new facts or assume details not in the question.\n\n"
                    f"Previous User Question: {last_user_query}\n"
                    f"Current Follow-Up Question: {question}\n\n"
                    f"Standalone Rewritten Question:"
                )
                rewritten = llm.generate(rewrite_prompt, system_prompt="You are a query rewriter. Output ONLY the standalone question.")
                rewritten_clean = rewritten.strip().strip('"').strip("'").split('\n')[0]
                if (
                    rewritten_clean 
                    and len(rewritten_clean) > 5 
                    and not rewritten_clean.lower().startswith("i ")
                    and "error" not in rewritten_clean.lower()
                    and "connect" not in rewritten_clean.lower()
                ):
                    return rewritten_clean, True
        except Exception as e:
            logger.warning(f"LLM query reformulation failed: {e}")

    # Robust deterministic resolution
    resolved = deterministic_query_rewrite(question, last_user_query)
    return resolved, True
