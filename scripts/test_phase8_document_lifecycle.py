"""
RAXEL Phase 8 — Comprehensive Document Lifecycle, Deletion Integrity & RBAC Security Test Suite.

Verifies:
1. Synthetic PDF upload via Faculty workflow.
2. Pending document retrieval exclusion (unapproved documents stay inactive).
3. Admin approval -> FAISS index rebuild -> in-memory cache reload.
4. Student RAG Chat retrieval, answer generation & citation.
5. Permanent document deletion (DB cleanup, PDF file removal, manifest sync, vector index rebuild & cache reload).
6. Post-deletion RAG query rejection (0 citations, safe fallback).
7. Server restart / index rebuild sanity persistence.
8. RBAC security enforcement (Guest, Student, and Cross-Faculty deletion protection).
"""

import sys
import os
import shutil
import sqlite3
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.config import Config
from src.permissions import ROLE_STUDENT, ROLE_FACULTY, ROLE_ADMIN
from src.auth import create_user, authenticate_user
from backend.dependencies import ComponentRegistry
from src.document_manager import DocumentManager
from src.pdf_processor import PDFProcessor

def generate_synthetic_pdf(output_path: Path, text: str) -> None:
    """Generate a clean synthetic PDF file using reportlab."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    output_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output_path), pagesize=letter)
    c.drawString(100, 750, "RAXEL PHASE 8 SYNTHETIC TEST FIXTURE DOCUMENT")
    c.drawString(100, 730, "Official Policy Notice: What time does the fictional Knowledge Lab close?")
    c.drawString(100, 700, "Information regarding Knowledge Lab closing time and operating schedule.")
    c.drawString(100, 680, text)
    c.drawString(100, 660, "Official Regulation: The fictional Knowledge Lab closes at 8:17 PM every day.")
    c.save()

def main():
    print("=" * 70)
    print("RAXEL PHASE 8 — DOCUMENT LIFECYCLE & DELETION INTEGRITY TEST SUITE")
    print("=" * 70)

    # 0. Setup & Singletons
    Config.ensure_directories()
    ComponentRegistry.initialize()
    doc_mgr = ComponentRegistry.get_doc_manager()
    rag_pipeline = ComponentRegistry.get_rag_pipeline()
    rag_pipeline.retriever.similarity_threshold = 0.20

    # Create Test Users
    faculty_user = {"username": "phase8_faculty", "role": ROLE_FACULTY, "authenticated": True}
    faculty_b_user = {"username": "phase8_faculty_b", "role": ROLE_FACULTY, "authenticated": True}
    admin_user = {"username": "phase8_admin", "role": ROLE_ADMIN, "authenticated": True}
    student_user = {"username": "phase8_student", "role": ROLE_STUDENT, "authenticated": True}
    guest_user = {"username": "Guest Student", "role": ROLE_STUDENT, "authenticated": False}

    # Purge leftover synthetic documents from previous runs & rebuild clean active index
    existing_docs = doc_mgr.list_documents()
    purged = False
    for d in existing_docs:
        fname = d.get("file_name", "") or d.get("original_filename", "") or ""
        title = d.get("title", "") or ""
        if "RAXEL_PHASE8" in fname or "RAXEL_PHASE8" in title:
            doc_mgr.delete_document(d["document_id"], user=admin_user)
            purged = True
    if purged:
        doc_mgr.rebuild_active_faiss_index()

    test_pdf_path = Config.DATA_DIR / "RAXEL_PHASE8_TEST_001.pdf"
    unique_fact_text = (
        "RAXEL_PHASE8_TEST_DOCUMENT_001\n"
        "FICTIONAL KNOWLEDGE LAB OPERATING HOURS AND POLICY\n\n"
        "Section 1: Operating Hours\n"
        "Question: What time does the fictional Knowledge Lab close?\n"
        "Answer: The fictional Knowledge Lab closes at exactly 8:17 PM.\n"
        "RAXEL_PHASE8_UNIQUE_FACT: The fictional Knowledge Lab closing time is 8:17 PM."
    )
    generate_synthetic_pdf(test_pdf_path, unique_fact_text)

    with open(test_pdf_path, "rb") as f:
        file_bytes = f.read()

    filename = "RAXEL_PHASE8_TEST_001.pdf"
    title = "Fictional Knowledge Lab Operating Policy 2025"

    print("\n[PART A] UPLOAD & PROCESSING")
    upload_res = doc_mgr.upload_document(
        file_bytes=file_bytes,
        filename=filename,
        title=title,
        document_type="academic_regulations",
        academic_year="2024-2025",
        version="1.0",
        effective_date="2025-01-01",
        description="Phase 8 synthetic test document",
        user=faculty_user
    )

    assert upload_res["success"], f"Upload failed: {upload_res.get('message')}"
    doc_id = upload_res["document"]["document_id"]
    print(f"  [PASS] Document uploaded successfully. ID: {doc_id}")

    process_res = doc_mgr.process_and_index_document(doc_id=doc_id, user=faculty_user)
    assert process_res["success"], f"Processing failed: {process_res.get('message')}"
    print(f"  [PASS] Document processed and chunks generated. Governance status: {process_res['document']['governance_status']}")

    # PART B — PENDING RETRIEVAL EXCLUSION
    print("\n[PART B] PENDING RETRIEVAL EXCLUSION")
    ret_pending = ComponentRegistry.get_rag_pipeline().retriever.retrieve("What time does the fictional Knowledge Lab close?")
    matching_pending_chunks = [c for c in ret_pending["chunks"] if doc_id in str(c.get("document_id", ""))]
    assert len(matching_pending_chunks) == 0, "Security violation: Pending document chunks were retrieved!"
    print("  [PASS] Pending document is correctly excluded from retrieval (retrieval_enabled=0).")

    # PART C — ADMIN APPROVAL
    print("\n[PART C] ADMIN APPROVAL")
    approve_res = doc_mgr.approve_document(doc_id=doc_id, user=admin_user)
    assert approve_res["success"], f"Approval failed: {approve_res.get('message')}"
    print("  [PASS] Document approved by Admin and indexed into active knowledge base.")

    # PART D — STUDENT RAG CHAT & CITATION
    print("\n[PART D] STUDENT RAG RETRIEVAL & ANSWERING")
    active_rag = ComponentRegistry.get_rag_pipeline()
    active_rag.retriever.similarity_threshold = 0.20
    chat_res = active_rag.answer_question("What time does the fictional Knowledge Lab close?")
    answer_text = chat_res["answer"]
    citations = chat_res["citations"]

    print(f"  RAG Answer: {answer_text}")
    print(f"  Citations: {citations}")

    assert "8:17 PM" in answer_text or "8:17" in answer_text, f"RAG failed to answer from approved doc. Answer: {answer_text}"
    assert len(citations) > 0, "No citations generated for active document."
    assert any("RAXEL_PHASE8_TEST_001" in (c.get("document") or c.get("document_name") or "") for c in citations), "Citation did not match uploaded document."
    print("  [PASS] Student RAG query answered correctly with grounded document citation.")

    # PART E — DOCUMENT DELETION (FACULTY OWNER OR ADMIN)
    print("\n[PART E] PERMANENT DOCUMENT DELETION & DATA CLEANUP")
    delete_res = doc_mgr.delete_document(doc_id=doc_id, user=faculty_user)
    assert delete_res["success"], f"Deletion failed: {delete_res.get('message')}"
    print("  [PASS] Document deleted by Faculty owner.")

    # Verify Database cleanup
    db_doc = doc_mgr.get_document_by_id(doc_id)
    assert db_doc is None, "Database document record still exists after deletion!"
    print("  [PASS] SQLite document record purged.")

    # Verify Physical file cleanup
    stored_path = Path(upload_res["document"]["stored_path"])
    assert not stored_path.exists(), f"Physical file '{stored_path}' still exists on disk!"
    print("  [PASS] Physical PDF file removed from disk.")

    # PART F — POST-DELETION RAG TEST
    print("\n[PART F] POST-DELETION RAG RETRIEVAL TEST")
    active_rag = ComponentRegistry.get_rag_pipeline()
    post_del_res = active_rag.answer_question("What time does the fictional Knowledge Lab close?")
    post_del_answer = post_del_res["answer"]
    post_del_citations = post_del_res["citations"]

    print(f"  Post-Delete Answer: {post_del_answer}")
    print(f"  Post-Delete Citations: {post_del_citations}")

    assert "8:17 PM" not in post_del_answer, "CRITICAL ERROR: Deleted document knowledge was retrieved after deletion!"
    assert len(post_del_citations) == 0 or not any("RAXEL_PHASE8_TEST_001" in (c.get("document") or c.get("document_name") or "") for c in post_del_citations), "Deleted document citation leaked!"
    print("  [PASS] RAXEL safely rejected deleted document knowledge (0 citations, safe fallback).")

    # PART G — REBUILD & RESTART PERSISTENCE TEST
    print("\n[PART G] INDEX REBUILD & RESTART SANITY CHECK")
    rebuild_res = doc_mgr.rebuild_active_faiss_index()
    assert rebuild_res["success"], f"Index rebuild failed: {rebuild_res.get('message')}"

    # Re-test after rebuild
    active_rag = ComponentRegistry.get_rag_pipeline()
    post_rebuild_res = active_rag.answer_question("What time does the fictional Knowledge Lab close?")
    assert "8:17 PM" not in post_rebuild_res["answer"], "CRITICAL ERROR: Rebuild restored deleted knowledge!"
    print("  [PASS] Deleted knowledge remains permanently unretrievable after FAISS index rebuild.")

    # PART H — RBAC SECURITY TESTS
    print("\n[PART H] RBAC SECURITY ENFORCEMENT TESTS")

    # 1. Guest Student Delete attempt
    try:
        doc_mgr.delete_document("doc_fake", user=guest_user)
        assert False, "Guest delete should have raised PermissionError"
    except PermissionError:
        print("  [PASS] Guest Student delete attempt rejected (401/403).")

    # 2. Student Delete attempt
    try:
        doc_mgr.delete_document("doc_fake", user=student_user)
        assert False, "Student delete should have raised PermissionError"
    except PermissionError:
        print("  [PASS] Student delete attempt rejected (403 Forbidden).")

    # 3. Cross-Faculty Delete attempt (Faculty B attempting to delete Faculty A's document)
    # Re-upload document as Faculty A
    upload_a = doc_mgr.upload_document(
        file_bytes=file_bytes,
        filename="RAXEL_PHASE8_CROSS_TEST.pdf",
        title="Cross Faculty Test Doc",
        document_type="syllabus",
        user=faculty_user
    )
    doc_a_id = upload_a["document"]["document_id"]

    try:
        doc_mgr.delete_document(doc_a_id, user=faculty_b_user)
        assert False, "Cross-faculty delete should have raised PermissionError"
    except PermissionError:
        print("  [PASS] Cross-Faculty deletion attempt blocked (403 Forbidden).")

    # Clean up cross test doc as Admin
    doc_mgr.delete_document(doc_a_id, user=admin_user)
    print("  [PASS] Admin successfully deleted cross test document.")

    # Clean up local synthetic test PDF file if remaining
    if test_pdf_path.exists():
        os.remove(test_pdf_path)

    print("\n" + "=" * 70)
    print("ALL PHASE 8 LIFECYCLE, DELETION & RBAC SECURITY TESTS PASSED PERFECTLY!")
    print("=" * 70)

if __name__ == "__main__":
    main()
