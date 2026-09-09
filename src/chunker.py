import re
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class TextChunker:
    """
    Phase 5 Production Text Chunker with Table-Aware Context Preservation.
    Handles sliding window paragraph splitting, micro-chunk merging, and rich metadata inheritance.
    """

    def __init__(
        self, 
        chunk_size: int = 500, 
        chunk_overlap: int = 100, 
        min_chunk_size: int = 80
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_text(self, text: str, page_meta: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Split page text into chunks while preserving heading and table context 
        and avoiding micro-chunks.
        """
        if not text or not text.strip():
            return []

        clean_text = text.strip()

        # If text contains markdown table tags, preserve table block integrity
        is_table_block = "[TABLE" in clean_text or "| --- |" in clean_text or clean_text.count("|") > 4

        if len(clean_text) <= self.chunk_size:
            return [clean_text]

        # Split into paragraph blocks
        paragraphs = [p.strip() for p in clean_text.split("\n\n") if p.strip()]
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            # Check if adding this paragraph exceeds chunk_size
            if len(current_chunk) + len(para) + 2 > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
                    current_chunk = current_chunk[overlap_start:].strip() + "\n\n"

                # If paragraph itself exceeds chunk_size, split by sentence boundaries or table lines
                if len(para) > self.chunk_size:
                    if "|" in para:
                        # Split table by line boundaries to keep table rows intact
                        lines = para.split("\n")
                        for line in lines:
                            if len(current_chunk) + len(line) + 1 > self.chunk_size:
                                if current_chunk:
                                    chunks.append(current_chunk.strip())
                                    current_chunk = ""
                            current_chunk += line + "\n"
                    else:
                        sentences = re.split(r'(?<=[.!?])\s+', para)
                        for sent in sentences:
                            if len(current_chunk) + len(sent) + 1 > self.chunk_size:
                                if current_chunk:
                                    chunks.append(current_chunk.strip())
                                    overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
                                    current_chunk = current_chunk[overlap_start:].strip() + " "
                                
                                while len(sent) > self.chunk_size:
                                    chunks.append(sent[:self.chunk_size].strip())
                                    sent = sent[self.chunk_size - self.chunk_overlap:]
                            
                            current_chunk += sent + " "
                else:
                    current_chunk += para + "\n\n"
            else:
                current_chunk += para + "\n\n"

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # Post-process: Merge micro-chunks (< min_chunk_size) into previous or next chunk
        final_chunks = []
        for idx, c in enumerate(chunks):
            if len(c) < self.min_chunk_size and final_chunks:
                final_chunks[-1] = (final_chunks[-1] + "\n\n" + c).strip()
            else:
                final_chunks.append(c)

        return final_chunks

    def chunk_documents(self, page_documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Takes a list of extracted page dicts and generates chunk dicts carrying 
        full rich metadata.
        """
        all_chunks = []

        for page_doc in page_documents:
            text = page_doc.get("text", "")
            if not text:
                continue

            doc_name = page_doc.get("document_name", page_doc.get("document", "Unknown.pdf"))
            page_num = page_doc.get("page_number", page_doc.get("page", 1))

            raw_chunks = self.chunk_text(text, page_meta=page_doc)

            for idx, chunk_text in enumerate(raw_chunks, 1):
                chunk_id = f"{doc_name}_p{page_num}_c{idx:02d}"

                chunk_meta = {
                    "text": chunk_text,
                    "chunk_id": chunk_id,
                    "document_name": doc_name,
                    "file_name": doc_name,
                    "file_hash": page_doc.get("file_hash", ""),
                    "document": doc_name,  # Phase 1 backwards compatibility
                    "page_number": page_num,
                    "page": page_num,      # Phase 1 backwards compatibility
                    "source_path": page_doc.get("source_path", page_doc.get("source", "")),
                    "source": page_doc.get("source_path", page_doc.get("source", "")), # Phase 1 compatibility
                    "file_modified_time": page_doc.get("file_modified_time", ""),
                    "page_count": page_doc.get("page_count", 1),
                    "document_type": page_doc.get("document_type", "general"),
                    "version_str": page_doc.get("version_str", None),
                    "academic_year": page_doc.get("version_str", "2025"),
                    "notice_date": page_doc.get("notice_date"),
                    "deadline": page_doc.get("deadline"),
                    "issuing_authority": page_doc.get("issuing_authority"),
                    "has_table": page_doc.get("has_table", False),
                    "needs_ocr": page_doc.get("needs_ocr", False),
                    "document_id": page_doc.get("document_id"),
                    "document_title": page_doc.get("document_title"),
                    "authority": page_doc.get("authority")
                }
                all_chunks.append(chunk_meta)

        logger.info(f"Generated {len(all_chunks)} chunks from {len(page_documents)} page documents.")
        return all_chunks
