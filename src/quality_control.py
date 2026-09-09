"""
Knowledge Base Quality Control & Conflict Management Layer for RAXEL (Phase 6.4).

Provides lightweight, offline quality-control scanning for approved college documents:
1. Exact duplicate detection (SHA-256 / MD5 hashing)
2. Near-duplicate detection (text & token similarity fingerprinting)
3. Same-topic document & version sequence tracking
4. Effective date priority & future-dated document suppression
5. Outdated / superseded document deactivation
6. Factual conflict detection & severity classification (LOW, MEDIUM, HIGH)
7. SQLite quality issue tracking & Admin conflict resolution workflows
"""

import re
import datetime
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set

from src.config import Config
from src.permissions import require_role, ROLE_ADMIN
from src.pdf_processor import PDFProcessor

logger = logging.getLogger(__name__)

# Quality States
QUALITY_CLEAN = "clean"
QUALITY_DUPLICATE = "duplicate"
QUALITY_POSSIBLE_DUPLICATE = "possible_duplicate"
QUALITY_CONFLICT = "conflict"
QUALITY_OUTDATED = "outdated"
QUALITY_REVIEW_REQUIRED = "review_required"
QUALITY_FUTURE_EFFECTIVE = "future_effective"

# Issue Types
ISSUE_EXACT_DUPLICATE = "exact_duplicate"
ISSUE_NEAR_DUPLICATE = "near_duplicate"
ISSUE_SAME_TOPIC = "same_topic"
ISSUE_VERSION_CONFLICT = "version_conflict"
ISSUE_FACTUAL_CONFLICT = "factual_conflict"
ISSUE_OUTDATED = "outdated"

# Conflict Severities
SEVERITY_LOW = "LOW"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_HIGH = "HIGH"

def extract_tokens(text: str) -> Set[str]:
    """Extract lowercase alpha tokens >= 3 chars for similarity comparison."""
    if not text:
        return set()
    return set(re.findall(r'\b[a-z]{3,}\b', text.lower()))

def calculate_jaccard_similarity(text1: str, text2: str) -> float:
    """Calculate token-level Jaccard similarity between two text strings."""
    t1 = extract_tokens(text1)
    t2 = extract_tokens(text2)
    if not t1 or not t2:
        return 0.0
    intersection = t1.intersection(t2)
    union = t1.union(t2)
    return len(intersection) / len(union) if union else 0.0

def parse_date(date_str: Optional[str]) -> Optional[datetime.date]:
    """Parse common ISO or standard date strings into datetime.date object."""
    if not date_str or not isinstance(date_str, str):
        return None
    clean = date_str.strip()
    # Try ISO YYYY-MM-DD
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y", "%Y"):
        try:
            dt = datetime.datetime.strptime(clean, fmt)
            return dt.date()
        except ValueError:
            continue
    # Try 4-digit year fallback
    m = re.search(r'\b(20\d{2})\b', clean)
    if m:
        try:
            return datetime.date(int(m.group(1)), 1, 1)
        except ValueError:
            pass
    return None

class QualityControlManager:
    """Manages RAXEL Knowledge Base Quality Control, duplicate scanning, and conflict resolution."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else Config.AUTH_DATABASE_PATH

    def get_connection(self) -> sqlite3.Connection:
        """Return SQLite connection with Row factory."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def list_documents(self) -> List[Dict[str, Any]]:
        """Fetch all document records from SQLite."""
        conn = self.get_connection()
        try:
            cursor = conn.execute("SELECT * FROM documents ORDER BY uploaded_at DESC")
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    def get_document_text(self, doc_record: Dict[str, Any]) -> str:
        """Extract or read document full text from stored PDF file."""
        stored_path = doc_record.get("stored_path")
        if not stored_path or not Path(stored_path).exists():
            return ""
        try:
            processor = PDFProcessor(ocr_enabled=False)
            pages = processor.process_pdf(Path(stored_path))
            return " ".join([p.get("text", "") for p in pages])
        except Exception as e:
            logger.warning(f"Could not extract text for quality check on doc {doc_record.get('document_id')}: {str(e)}")
            return ""

    def run_quality_scan(self, current_date: Optional[datetime.date] = None) -> Dict[str, Any]:
        """
        Run complete quality control scan over all documents:
        1. Exact duplicate check
        2. Near duplicate check
        3. Same topic & version sequence check
        4. Effective date evaluation (future vs current)
        5. Outdated / superseded document marking
        6. Factual conflict detection & severity rating
        """
        now_date = current_date or datetime.date.today()
        docs = self.list_documents()
        if not docs:
            return {"success": True, "issues_found": 0, "message": "Knowledge base is empty."}

        new_issues = []
        doc_texts = {}

        # 1. Effective Date & Future-Date Handling
        conn = self.get_connection()
        try:
            with conn:
                for doc in docs:
                    doc_id = doc["document_id"]
                    eff_str = doc.get("effective_date")
                    eff_dt = parse_date(eff_str)
                    
                    # Future-dated document check
                    if eff_dt and eff_dt > now_date:
                        conn.execute("""
                            UPDATE documents
                            SET quality_status = 'future_effective',
                                retrieval_enabled = 0,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE document_id = ?
                        """, (doc_id,))
                        self._log_audit(doc_id, "quality_future_effective", "system", details=f"Effective date {eff_str} is in the future")

            # 2. Version Sequence & Superseded Document Handling
            # Group approved/indexed documents by topic / type
            approved_docs = [d for d in docs if d.get("governance_status") == "approved" and d.get("status") == "indexed"]
            
            topic_groups: Dict[str, List[Dict[str, Any]]] = {}
            for d in approved_docs:
                dt = (d.get("document_type") or "general").lower()
                clean_title = re.sub(r'[\d_vV\.\s]+', '', (d.get("title") or "").lower())
                group_key = f"{dt}_{clean_title[:15]}"
                if group_key not in topic_groups:
                    topic_groups[group_key] = []
                topic_groups[group_key].append(d)

            for g_key, g_docs in topic_groups.items():
                if len(g_docs) < 2:
                    continue

                def sort_key(doc):
                    dt = parse_date(doc.get("effective_date")) or datetime.date(1970, 1, 1)
                    ver = doc.get("version") or "1.0"
                    up = doc.get("uploaded_at") or ""
                    return (dt, ver, up)

                sorted_g = sorted(g_docs, key=sort_key)
                latest_doc = sorted_g[-1]
                latest_id = latest_doc["document_id"]
                latest_date = parse_date(latest_doc.get("effective_date")) or now_date

                for older_doc in sorted_g[:-1]:
                    older_id = older_doc["document_id"]
                    older_date = parse_date(older_doc.get("effective_date"))
                    
                    if older_date and latest_doc.get("effective_date") and older_date < (parse_date(latest_doc.get("effective_date")) or now_date):
                        with conn:
                            conn.execute("""
                                UPDATE documents
                                SET quality_status = 'outdated',
                                    superseded_by = ?,
                                    retrieval_enabled = 0,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE document_id = ?
                            """, (latest_id, older_id))

                            conn.execute("""
                                UPDATE documents
                                SET supersedes_document_id = ?
                                WHERE document_id = ?
                            """, (older_id, latest_id))

                        self._record_issue_if_new(
                            doc_a_id=older_id,
                            doc_b_id=latest_id,
                            issue_type=ISSUE_OUTDATED,
                            severity=SEVERITY_LOW,
                            description=f"Document '{older_doc['title']}' (Effective: {older_doc.get('effective_date')}) is superseded by newer approved version '{latest_doc['title']}' (Effective: {latest_doc.get('effective_date')})."
                        )

            # 3. Pairwise Document Comparisons (Exact Duplicate, Near Duplicate, Factual Conflicts)
            for i in range(len(docs)):
                for j in range(i + 1, len(docs)):
                    doc_a, doc_b = docs[i], docs[j]
                    doc_a_id, doc_b_id = doc_a["document_id"], doc_b["document_id"]

                    # Exact Duplicate (file_hash match)
                    if doc_a.get("file_hash") and doc_a.get("file_hash") == doc_b.get("file_hash"):
                        with conn:
                            conn.execute("UPDATE documents SET quality_status = 'duplicate' WHERE document_id IN (?, ?)", (doc_a_id, doc_b_id))
                        self._record_issue_if_new(
                            doc_a_id=doc_a_id,
                            doc_b_id=doc_b_id,
                            issue_type=ISSUE_EXACT_DUPLICATE,
                            severity=SEVERITY_MEDIUM,
                            description=f"Exact binary file duplicate detected between '{doc_a['title']}' and '{doc_b['title']}' (SHA-256 Hash match)."
                        )
                        continue

                    # Same Topic or Near Duplicate check
                    type_a = (doc_a.get("document_type") or "").lower()
                    type_b = (doc_b.get("document_type") or "").lower()
                    same_type = (type_a == type_b) and (type_a not in ("other", "general"))

                    title_sim = calculate_jaccard_similarity(doc_a.get("title", ""), doc_b.get("title", ""))

                    if same_type or title_sim > 0.4:
                        if doc_a_id not in doc_texts:
                            doc_texts[doc_a_id] = self.get_document_text(doc_a)
                        if doc_b_id not in doc_texts:
                            doc_texts[doc_b_id] = self.get_document_text(doc_b)

                        text_a, text_b = doc_texts[doc_a_id], doc_texts[doc_b_id]
                        content_sim = calculate_jaccard_similarity(text_a, text_b)

                        if content_sim >= 0.70:
                            with conn:
                                conn.execute("UPDATE documents SET quality_status = 'possible_duplicate' WHERE document_id IN (?, ?) AND quality_status = 'clean'", (doc_a_id, doc_b_id))
                            self._record_issue_if_new(
                                doc_a_id=doc_a_id,
                                doc_b_id=doc_b_id,
                                issue_type=ISSUE_NEAR_DUPLICATE,
                                severity=SEVERITY_MEDIUM,
                                description=f"Possible duplicate / highly similar content detected between '{doc_a['title']}' and '{doc_b['title']}' (Similarity: {content_sim:.2%})."
                            )

                        if doc_a.get("governance_status") == "approved" and doc_b.get("governance_status") == "approved":
                            conflict_detected, severity, desc = self.analyze_factual_conflict(doc_a, text_a, doc_b, text_b)
                            if conflict_detected:
                                with conn:
                                    conn.execute("UPDATE documents SET quality_status = 'conflict' WHERE document_id IN (?, ?) AND quality_status != 'outdated'", (doc_a_id, doc_b_id))
                                self._record_issue_if_new(
                                    doc_a_id=doc_a_id,
                                    doc_b_id=doc_b_id,
                                    issue_type=ISSUE_FACTUAL_CONFLICT,
                                    severity=severity,
                                    description=desc
                                )

        finally:
            conn.close()

        open_issues = self.get_quality_issues(status="open")
        return {
            "success": True,
            "issues_found": len(open_issues),
            "open_issues": open_issues,
            "message": f"Quality scan complete. {len(open_issues)} open quality issue(s) detected."
        }

    def analyze_factual_conflict(
        self,
        doc_a: Dict[str, Any],
        text_a: str,
        doc_b: Dict[str, Any],
        text_b: str
    ) -> Tuple[bool, str, str]:
        """
        Analyze two same-topic document texts for factual contradictions.
        Detects numeric rules (attendance percentages, library hours, fee amounts, dates).
        Returns (conflict_detected, severity, description).
        """
        if not text_a or not text_b:
            return False, SEVERITY_LOW, ""

        p_a = set(re.findall(r'(\d{2}\s*%\s*(?:attendance|shortage|requirement|condonation)?)', text_a, re.IGNORECASE))
        p_b = set(re.findall(r'(\d{2}\s*%\s*(?:attendance|shortage|requirement|condonation)?)', text_b, re.IGNORECASE))

        nums_a = set(re.findall(r'(\d{2})\s*%', text_a))
        nums_b = set(re.findall(r'(\d{2})\s*%', text_b))

        if nums_a and nums_b and nums_a != nums_b and ("attendance" in text_a.lower() or "attendance" in text_b.lower()):
            desc = (
                f"Factual policy contradiction on Attendance Requirement: '{doc_a['title']}' mentions "
                f"{', '.join(sorted(nums_a))}% while '{doc_b['title']}' mentions {', '.join(sorted(nums_b))}%."
            )
            return True, SEVERITY_HIGH, desc

        times_a = set(re.findall(r'(\d{1,2}\s*(?:AM|PM|am|pm|:\d{2}))', text_a))
        times_b = set(re.findall(r'(\d{1,2}\s*(?:AM|PM|am|pm|:\d{2}))', text_b))

        if times_a and times_b and times_a != times_b and ("library" in text_a.lower() or "timing" in text_a.lower() or "closing" in text_a.lower()):
            desc = (
                f"Factual policy contradiction on Operating Hours / Timings: '{doc_a['title']}' specifies "
                f"{', '.join(sorted(times_a))} while '{doc_b['title']}' specifies {', '.join(sorted(times_b))}."
            )
            return True, SEVERITY_MEDIUM, desc

        if nums_a and nums_b and nums_a != nums_b:
            desc = (
                f"Potentially conflicting numerical values detected between '{doc_a['title']}' ({', '.join(sorted(nums_a))}) "
                f"and '{doc_b['title']}' ({', '.join(sorted(nums_b))})."
            )
            return True, SEVERITY_MEDIUM, desc

        return False, SEVERITY_LOW, ""

    def _record_issue_if_new(
        self,
        doc_a_id: str,
        doc_b_id: str,
        issue_type: str,
        severity: str,
        description: str
    ) -> None:
        """Insert issue into SQLite table `document_quality_issues` if not already logged."""
        conn = self.get_connection()
        try:
            with conn:
                cursor = conn.execute("""
                    SELECT issue_id FROM document_quality_issues
                    WHERE ((document_a_id = ? AND document_b_id = ?) OR (document_a_id = ? AND document_b_id = ?))
                      AND issue_type = ? AND status = 'open'
                """, (doc_a_id, doc_b_id, doc_b_id, doc_a_id, issue_type))
                if cursor.fetchone():
                    return

                import uuid
                issue_id = f"issue_{doc_a_id[:6]}_{doc_b_id[:6]}_{issue_type[:4]}_{uuid.uuid4().hex[:6]}"
                conn.execute("""
                    INSERT INTO document_quality_issues (
                        issue_id, document_a_id, document_b_id, issue_type, severity, description, status
                    ) VALUES (?, ?, ?, ?, ?, ?, 'open')
                """, (issue_id, doc_a_id, doc_b_id, issue_type, severity, description))
        finally:
            conn.close()

    def get_quality_issues(
        self,
        status: Optional[str] = None,
        issue_type: Optional[str] = None,
        severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve quality issues from SQLite with optional filtering."""
        conn = self.get_connection()
        try:
            query = "SELECT * FROM document_quality_issues WHERE 1=1"
            params = []
            if status:
                query += " AND status = ?"
                params.append(status)
            if issue_type:
                query += " AND issue_type = ?"
                params.append(issue_type)
            if severity:
                query += " AND severity = ?"
                params.append(severity)
            query += " ORDER BY created_at DESC"

            cursor = conn.execute(query, params)
            issues = [dict(r) for r in cursor.fetchall()]

            for issue in issues:
                doc_a = self._get_doc_meta(issue["document_a_id"], conn)
                doc_b = self._get_doc_meta(issue["document_b_id"], conn)
                issue["doc_a_title"] = doc_a.get("title", issue["document_a_id"]) if doc_a else issue["document_a_id"]
                issue["doc_b_title"] = doc_b.get("title", issue["document_b_id"]) if doc_b else issue["document_b_id"]
                issue["doc_a_version"] = doc_a.get("version") if doc_a else None
                issue["doc_b_version"] = doc_b.get("version") if doc_b else None
                issue["doc_a_date"] = doc_a.get("effective_date") if doc_a else None
                issue["doc_b_date"] = doc_b.get("effective_date") if doc_b else None

            return issues
        finally:
            conn.close()

    def _get_doc_meta(self, doc_id: str, conn: sqlite3.Connection) -> Optional[Dict[str, Any]]:
        """Helper to fetch document metadata row."""
        cursor = conn.execute("SELECT * FROM documents WHERE document_id = ?", (doc_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def resolve_quality_issue(
        self,
        issue_id: str,
        resolution_action: str,
        user: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None,
        preferred_doc_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Resolve a quality issue (Admin ONLY).
        Actions:
          - 'mark_reviewed': Mark issue reviewed without changing doc statuses.
          - 'prefer_newer': Mark older document as superseded/outdated and set retrieval_enabled=0.
          - 'set_preferred_source': Set preferred_source=1 for chosen document and preferred_reason.
          - 'mark_unresolved': Keep conflict flagged open as unresolved.
        """
        require_role(ROLE_ADMIN, user)
        username = user.get("username", "admin") if user else "admin"

        conn = self.get_connection()
        try:
            cursor = conn.execute("SELECT * FROM document_quality_issues WHERE issue_id = ?", (issue_id,))
            issue = cursor.fetchone()
            if not issue:
                return {"success": False, "message": f"Issue ID '{issue_id}' not found."}
            issue_dict = dict(issue)

            doc_a_id = issue_dict["document_a_id"]
            doc_b_id = issue_dict["document_b_id"]

            with conn:
                if resolution_action == "mark_reviewed":
                    conn.execute("""
                        UPDATE document_quality_issues
                        SET status = 'reviewed', resolved_by = ?, resolved_at = CURRENT_TIMESTAMP, resolution = ?
                        WHERE issue_id = ?
                    """, (username, notes or "Marked reviewed by Admin", issue_id))

                    conn.execute("""
                        UPDATE documents SET quality_reviewed = 1, quality_reviewed_by = ?, quality_reviewed_at = CURRENT_TIMESTAMP
                        WHERE document_id IN (?, ?)
                    """, (username, doc_a_id, doc_b_id))

                elif resolution_action == "prefer_newer":
                    doc_a = self._get_doc_meta(doc_a_id, conn)
                    doc_b = self._get_doc_meta(doc_b_id, conn)
                    
                    dt_a = parse_date(doc_a.get("effective_date")) if doc_a else None
                    dt_b = parse_date(doc_b.get("effective_date")) if doc_b else None

                    newer_id, older_id = (doc_b_id, doc_a_id) if (dt_b and dt_a and dt_b > dt_a) else (doc_a_id, doc_b_id)

                    conn.execute("""
                        UPDATE documents
                        SET quality_status = 'outdated', superseded_by = ?, retrieval_enabled = 0, updated_at = CURRENT_TIMESTAMP
                        WHERE document_id = ?
                    """, (newer_id, older_id))

                    conn.execute("""
                        UPDATE documents
                        SET quality_status = 'clean', supersedes_document_id = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE document_id = ?
                    """, (older_id, newer_id))

                    conn.execute("""
                        UPDATE document_quality_issues
                        SET status = 'resolved', resolved_by = ?, resolved_at = CURRENT_TIMESTAMP,
                            resolution = ?
                        WHERE issue_id = ?
                    """, (username, f"Preferred newer version {newer_id}; archived/superseded {older_id}", issue_id))

                elif resolution_action == "set_preferred_source":
                    target_id = preferred_doc_id or doc_a_id
                    other_id = doc_b_id if target_id == doc_a_id else doc_a_id

                    conn.execute("""
                        UPDATE documents
                        SET preferred_source = 1, preferred_reason = ?, quality_status = 'clean', updated_at = CURRENT_TIMESTAMP
                        WHERE document_id = ?
                    """, (notes or "Explicitly marked as preferred source by Admin", target_id))

                    conn.execute("""
                        UPDATE documents
                        SET preferred_source = 0, quality_status = 'conflict_overridden', retrieval_enabled = 0, updated_at = CURRENT_TIMESTAMP
                        WHERE document_id = ?
                    """, (other_id,))

                    conn.execute("""
                        UPDATE document_quality_issues
                        SET status = 'resolved', resolved_by = ?, resolved_at = CURRENT_TIMESTAMP,
                            resolution = ?
                        WHERE issue_id = ?
                    """, (username, f"Admin selected preferred source: {target_id}", issue_id))

                elif resolution_action == "mark_unresolved":
                    conn.execute("""
                        UPDATE document_quality_issues
                        SET status = 'open', resolved_by = ?, resolved_at = CURRENT_TIMESTAMP,
                            resolution = 'Flagged as unresolved conflict'
                        WHERE issue_id = ?
                    """, (username, issue_id))

            self._log_audit(doc_a_id, "quality_issue_resolved", username, reason=notes, details=f"Action: {resolution_action} on {issue_id}")
            self._log_audit(doc_b_id, "quality_issue_resolved", username, reason=notes, details=f"Action: {resolution_action} on {issue_id}")

            return {
                "success": True,
                "message": f"Quality issue '{issue_id}' updated with action '{resolution_action}'."
            }
        finally:
            conn.close()

    def get_unresolved_conflicts_between_documents(self, doc_ids: List[str]) -> List[Dict[str, Any]]:
        """Check if any pair among doc_ids has an active unresolved factual conflict."""
        if len(doc_ids) < 2:
            return []
        conn = self.get_connection()
        try:
            placeholders = ",".join(["?"] * len(doc_ids))
            cursor = conn.execute(f"""
                SELECT * FROM document_quality_issues
                WHERE document_a_id IN ({placeholders})
                  AND document_b_id IN ({placeholders})
                  AND issue_type = 'factual_conflict'
                  AND status = 'open'
            """, doc_ids + doc_ids)
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    def _log_audit(self, doc_id: str, action: str, performed_by: str, reason: Optional[str] = None, details: Optional[str] = None) -> None:
        """Record governance audit trail entry."""
        conn = self.get_connection()
        try:
            with conn:
                conn.execute("""
                    INSERT INTO document_audit_log (document_id, action, performed_by, reason, details)
                    VALUES (?, ?, ?, ?, ?)
                """, (doc_id, action, performed_by, reason, details))
        except Exception as e:
            logger.warning(f"Audit log warning: {str(e)}")
        finally:
            conn.close()
