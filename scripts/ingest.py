import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Add project root directory to python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import Config
from src.pdf_processor import PDFProcessor
from src.chunker import TextChunker
from src.embeddings import EmbeddingManager
from src.vector_store import VectorStoreManager

def run_ingestion():
    """
    Production-grade knowledge base ingestion pipeline with document validation 
    and structured ingestion reporting.
    """
    start_time = time.time()
    Config.ensure_directories()

    documents_dir = Config.DOCUMENTS_DIR
    pdf_files = sorted(list(documents_dir.glob("*.pdf")))

    if not pdf_files:
        print("==================================================")
        print("KNOWLEDGE BASE INGESTION REPORT")
        print("==================================================")
        print(f"[!] No PDF documents found in '{documents_dir}'.")
        print("Please place college PDFs in 'data/documents/' and re-run.")
        print("==================================================")
        sys.exit(1)

    processor = PDFProcessor(
        ocr_enabled=Config.OCR_ENABLED,
        ocr_min_text_length=Config.OCR_MIN_TEXT_LENGTH
    )
    chunker = TextChunker(
        chunk_size=Config.CHUNK_SIZE,
        chunk_overlap=Config.CHUNK_OVERLAP,
        min_chunk_size=Config.MIN_CHUNK_SIZE
    )

    all_pages: List[Dict[str, Any]] = []
    processed_docs: List[Dict[str, Any]] = []
    skipped_docs: List[str] = []
    warnings: List[str] = []
    ocr_pages_count = 0

    for pdf_file in pdf_files:
        doc_name = pdf_file.name
        pages = processor.process_pdf(pdf_file)

        if not pages:
            skipped_docs.append(doc_name)
            warnings.append(f"{doc_name} — Could not extract pages or file is corrupted/empty.")
            continue

        doc_ocr_count = 0
        for p in pages:
            if p.get("needs_ocr", False):
                ocr_pages_count += 1
                doc_ocr_count += 1
                warnings.append(
                    f"{doc_name} — Page {p['page_number']}: Text extraction produced very little content "
                    f"(< {Config.OCR_MIN_TEXT_LENGTH} chars). OCR required."
                )

        all_pages.extend(pages)
        processed_docs.append({
            "name": doc_name,
            "page_count": len(pages),
            "doc_type": pages[0].get("document_type", "general"),
            "version": pages[0].get("version_str", None)
        })

    # Chunking
    chunks = chunker.chunk_documents(all_pages) if all_pages else []

    if not chunks:
        print("==================================================")
        print("KNOWLEDGE BASE INGESTION REPORT")
        print("==================================================")
        print(f"[!] Error: Extraction succeeded on {len(all_pages)} pages, but 0 valid chunks were produced.")
        print("==================================================")
        sys.exit(1)

    # Embedding & Fresh Index Building
    embedder = EmbeddingManager(model_name=Config.EMBEDDING_MODEL_NAME)
    texts_to_embed = [c["text"] for c in chunks]
    embeddings = embedder.embed_texts(texts_to_embed, normalize=True)

    vector_store = VectorStoreManager(
        index_path=Config.FAISS_INDEX_PATH,
        metadata_path=Config.METADATA_PATH
    )
    vector_store.build_index(embeddings, chunks)

    elapsed = time.time() - start_time

    # Print Ingestion Report
    print("\n==================================================")
    print("KNOWLEDGE BASE INGESTION REPORT")
    print("==================================================")
    print(f"Documents processed: {len(processed_docs)}")
    print(f"Pages processed: {len(all_pages)}")
    print(f"Pages requiring OCR: {ocr_pages_count}")
    print(f"Chunks created: {len(chunks)}")
    print(f"Documents skipped: {len(skipped_docs)}")
    print(f"Warnings: {len(warnings)}")
    print(f"Ingestion time: {elapsed:.2f} seconds")

    print("\nDocuments Indexed:")
    for d in processed_docs:
        ver_str = f", Version: {d['version']}" if d['version'] else ""
        print(f" - {d['name']} (Type: {d['doc_type']}{ver_str}, Pages: {d['page_count']})")

    if skipped_docs:
        print("\nSkipped Documents:")
        for s in skipped_docs:
            print(f" - {s}")

    if warnings:
        print("\nWarnings:")
        for w in warnings[:10]:
            print(f" - [!] {w}")
        if len(warnings) > 10:
            print(f"   ... and {len(warnings) - 10} more warning(s).")

    print("\n==================================================")
    print(f"SUCCESS: Knowledge Base persisted to '{Config.VECTORSTORE_DIR}'")
    print("==================================================\n")

if __name__ == "__main__":
    run_ingestion()
