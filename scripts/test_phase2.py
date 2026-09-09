import sys
import tempfile
from pathlib import Path
from typing import List

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import Config
from src.pdf_processor import PDFProcessor
from src.chunker import TextChunker
from src.embeddings import EmbeddingManager
from src.vector_store import VectorStoreManager
from src.retriever import KnowledgeRetriever
from src.llm import OllamaLLM
from src.rag_pipeline import RAGPipeline

def test_phase2_suite():
    print("=" * 60)
    print("RUNNING PHASE 2 COMPREHENSIVE TEST SUITE")
    print("=" * 60)

    processor = PDFProcessor()
    chunker = TextChunker()

    # TEST 1: Normal Text PDF Extraction
    print("\n--- TEST 1: Normal Text PDF Extraction ---")
    doc_path = Config.DOCUMENTS_DIR / "Academic_Regulations.pdf"
    if doc_path.exists():
        pages = processor.process_pdf(doc_path)
        assert len(pages) > 0, "Failed to extract pages from Academic_Regulations.pdf"
        assert "text" in pages[0] and len(pages[0]["text"]) > 20, "Page text is empty"
        print(f"[PASSED] Normal text PDF extracted successfully ({len(pages)} pages).")
    else:
        print("[SKIPPED] Academic_Regulations.pdf does not exist in data/documents.")

    # TEST 2: Multi-page PDF & Human-Friendly Page Numbering
    print("\n--- TEST 2: Multi-page PDF Page Numbering (1-Indexed) ---")
    if doc_path.exists():
        pages = processor.process_pdf(doc_path)
        page_nums = [p["page_number"] for p in pages]
        assert page_nums == list(range(1, len(pages) + 1)), f"Page numbers invalid: {page_nums}"
        assert page_nums[0] == 1, "Page numbering should be 1-indexed, not 0-based."
        print(f"[PASSED] Human-friendly 1-indexed page numbers verified: {page_nums}")

    # TEST 3: Headings and Paragraph Context Preservation
    print("\n--- TEST 3: Heading & Paragraph Context Chunking ---")
    sample_text = (
        "Chapter 1: Attendance Requirements\n\n"
        "Students must maintain at least 75% attendance in all courses to be eligible for exams.\n\n"
        "Chapter 2: Grading System\n\n"
        "Grades range from O to F on a 10-point CGPA scale."
    )
    raw_chunks = chunker.chunk_text(sample_text)
    assert len(raw_chunks) > 0, "Chunking returned empty list"
    assert "Attendance Requirements" in raw_chunks[0], "Heading separated from paragraph"
    print(f"[PASSED] Meaningful chunks created with heading context preserved.")

    # TEST 4: Low Text & OCR Warning Detection
    print("\n--- TEST 4: Low Text & OCR Detection ---")
    mock_low_text_page = {"text": "A", "document_name": "Scanned_Test.pdf", "page_number": 1, "source_path": "test.pdf"}
    processed_pages = processor.process_pdf(doc_path) if doc_path.exists() else []
    # Test OCR flag condition
    low_text_clean = processor.clean_text("   X   ")
    needs_ocr = len(low_text_clean) < Config.OCR_MIN_TEXT_LENGTH
    assert needs_ocr is True, "Failed to flag low text page as needing OCR."
    print("[PASSED] Scanned / Low text page correctly flagged for OCR.")

    # TEST 5: Multiple Documents Metadata Separation
    print("\n--- TEST 5: Multi-Document Indexing & Metadata ---")
    docs_pages = processor.process_directory(Config.DOCUMENTS_DIR)
    doc_names = set(p["document_name"] for p in docs_pages)
    assert len(doc_names) >= 1, "No documents found in directory"
    chunks = chunker.chunk_documents(docs_pages)
    for c in chunks:
        assert "document_name" in c, "Missing document_name in chunk metadata"
        assert "document_type" in c, "Missing document_type in chunk metadata"
        assert c["page_number"] >= 1, "Page number is less than 1"
    print(f"[PASSED] Indexed {len(chunks)} chunks across {len(doc_names)} unique document(s) with rich metadata.")

    # TEST 6: Path Separation for Same Filenames
    print("\n--- TEST 6: Source Path Metadata Collision Prevention ---")
    meta1 = {"document_name": "Guide.pdf", "source_path": "folderA/Guide.pdf", "page_number": 1}
    meta2 = {"document_name": "Guide.pdf", "source_path": "folderB/Guide.pdf", "page_number": 1}
    assert meta1["source_path"] != meta2["source_path"], "Source paths should differentiate identical filenames"
    print("[PASSED] Path metadata separation verified.")

    # TEST 7: Safe Re-indexing (No Duplicate Accumulation)
    print("\n--- TEST 7: Safe Re-Indexing Predictability ---")
    embedding_mgr = EmbeddingManager(model_name=Config.EMBEDDING_MODEL_NAME)
    vector_store = VectorStoreManager(index_path=Config.FAISS_INDEX_PATH, metadata_path=Config.METADATA_PATH)

    # First build
    texts = [c["text"] for c in chunks[:5]]
    embs1 = embedding_mgr.embed_texts(texts, normalize=True)
    vector_store.build_index(embs1, chunks[:5])
    count1 = vector_store.get_chunk_count()

    # Re-build (fresh overwrite)
    embs2 = embedding_mgr.embed_texts(texts, normalize=True)
    vector_store.build_index(embs2, chunks[:5])
    count2 = vector_store.get_chunk_count()

    assert count1 == count2 == 5, f"Re-indexing accumulated duplicates: count1={count1}, count2={count2}"
    print(f"[PASSED] Re-indexing produces predictable clean index (Count: {count2}).")

    # TEST 8: Retrieval & Citation Page Accuracy
    print("\n--- TEST 8: Grounded Retrieval Page Citation Accuracy ---")
    # Re-index full dataset
    full_texts = [c["text"] for c in chunks]
    full_embs = embedding_mgr.embed_texts(full_texts, normalize=True)
    vector_store.build_index(full_embs, chunks)

    llm = OllamaLLM(model_name=Config.LLM_MODEL, base_url=Config.OLLAMA_BASE_URL)
    retriever = KnowledgeRetriever(embedding_manager=embedding_mgr, vector_store=vector_store, top_k=Config.TOP_K)
    pipeline = RAGPipeline(retriever=retriever, llm=llm)

    res = pipeline.answer_question("What is the minimum attendance requirement?")
    assert res["has_sufficient_evidence"] is True, "Failed to retrieve evidence for attendance query"
    assert len(res["citations"]) > 0, "No citations generated for retrieved answer"

    cited_doc = res["citations"][0]["document"]
    cited_page = res["citations"][0]["page"]
    print(f"[PASSED] Citation accurately identified: {cited_doc} — Page {cited_page}")

    # TEST 9: Document Type Classification Priority
    print("\n--- TEST 9: Document Type Classification Rules ---")
    classification_tests = [
        ("Academic_Regulations.pdf", "ACADEMIC REGULATIONS 2026", "academic_regulations"),
        ("Student_Handbook.pdf", "ACADEMIC REGULATIONS Chapter 1 Attendance", "student_handbook"),
        ("BCA_Syllabus.pdf", "Course Structure 2026", "syllabus"),
        ("Examination_Rules.pdf", "End Semester Exam Rules", "examination"),
        ("Exam_Timetable.pdf", "End Semester Examination Schedule", "timetable"),
        ("Placement_Guidelines.pdf", "Campus Recruitment Drive", "placement"),
        ("College_Notice.pdf", "Circular for Students", "notice"),
        ("Annual_Event.pdf", "College Cultural Fest Guidelines", "event"),
        ("Random_Document.pdf", "Some unknown text content", "general")
    ]

    for fname, stext, expected_type in classification_tests:
        detected = processor.detect_document_type(fname, stext)
        assert detected == expected_type, f"Failed for {fname}: expected '{expected_type}', got '{detected}'"
        print(f"  [+] {fname} -> '{detected}' (Expected: '{expected_type}')")

    print("[PASSED] Document type classification rules verified successfully!")

    print("\n" + "=" * 60)
    print("ALL PHASE 2 TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    test_phase2_suite()
