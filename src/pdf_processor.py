import re
import time
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Union, Optional
import logging

try:
    import pymupdf as fitz  # Recommended PyMuPDF import
except ImportError:
    try:
        import fitz  # Legacy fallback
    except ImportError:
        fitz = None

# Optional OCR imports
try:
    import pytesseract
    from PIL import Image
    import io
    HAS_PYTESSERACT = True
except ImportError:
    HAS_PYTESSERACT = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Document Type Keyword Mapping (Ordered by priority)
DOC_TYPE_KEYWORDS = {
    "timetable": ["timetable", "time_table", "schedule", "routine"],
    "syllabus": ["syllabus", "curriculum", "course_structure", "scheme"],
    "student_handbook": ["handbook", "student_handbook", "student handbook", "manual"],
    "notice": ["notice", "circular", "announcement", "memo"],
    "academic_regulations": ["regulation", "academic_reg", "academic reg", "ordinance"],
    "examination": ["examination", "exam", "evaluat", "re-eval", "grading"],
    "placement": ["placement", "recruit", "career"],
    "event": ["event", "fest", "seminar", "workshop", "symposium"]
}

class PDFProcessor:
    """
    Phase 5 Production PDF Processor for Synthetic GLS-Style Test Documents.
    Supports table extraction, multi-column layout sorting, notice metadata parsing,
    header/footer cleanup, OCR fallback, and document manifest management.
    """

    def __init__(self, ocr_enabled: bool = True, ocr_min_text_length: int = 50):
        self.ocr_enabled = ocr_enabled
        self.ocr_min_text_length = ocr_min_text_length

    @staticmethod
    def calculate_file_hash(file_path: Path) -> str:
        """Calculate MD5 hash of file for duplicate document detection."""
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()

    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean PDF extraction text without destroying headings, bullet points, 
        numbers, or dates.
        """
        if not text:
            return ""

        # 1. Fix line-break hyphenations (e.g., "Attend-\n-ance" -> "Attendance")
        text = re.sub(r'([a-zA-Z]{2,})-\s*\n\s*([a-zA-Z]{2,})', r'\1\2', text)

        # 2. Normalize excessive horizontal whitespace per line
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line_str = re.sub(r'[ \t]+', ' ', line).strip()
            cleaned_lines.append(line_str)

        text = '\n'.join(cleaned_lines)

        # 3. Collapse 3+ newlines to double newline (preserving paragraphs & headers)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        return text.strip()

    @staticmethod
    def detect_document_type(filename: str, sample_text: str = "") -> str:
        """
        Categorize document based on filename and header text patterns.
        Priority 1: Explicit filename matching.
        Priority 2: Header / sample text matching.
        Default: "general".
        """
        fname_lower = filename.lower()

        # Priority 1: Check filename first
        for doc_type, keywords in DOC_TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw in fname_lower:
                    return doc_type

        # Priority 2: Check sample text if filename is generic
        if sample_text:
            text_lower = sample_text[:1000].lower()
            for doc_type, keywords in DOC_TYPE_KEYWORDS.items():
                for kw in keywords:
                    if kw in text_lower:
                        return doc_type

        return "general"

    @staticmethod
    def detect_academic_year_or_version(text: str) -> Optional[str]:
        """Detect academic year or explicit version string if present in text."""
        match_year = re.search(r'\b(20\d{2}\s*[-–/]\s*(?:20)?\d{2})\b', text)
        if match_year:
            return match_year.group(1).replace(" ", "")

        match_ver = re.search(r'\b(?:v|version)\s*(\d+\.\d+)\b', text, re.IGNORECASE)
        if match_ver:
            return f"v{match_ver.group(1)}"

        return None

    @staticmethod
    def extract_notice_metadata(text: str) -> Dict[str, Any]:
        """Extract notice/circular dates, deadlines, issuing authority, and ref numbers."""
        meta = {
            "notice_date": None,
            "deadline": None,
            "issuing_authority": None,
            "notice_ref": None
        }
        
        # Notice Date
        date_match = re.search(r'\b(?:Date|Date of Issue):\s*([A-Za-z]+\s+\d{1,2},\s*20\d{2}|\d{1,2}[/-]\d{1,2}[/-]20\d{2})\b', text, re.IGNORECASE)
        if date_match:
            meta["notice_date"] = date_match.group(1)

        # Deadline
        deadline_match = re.search(r'\b(?:Deadline|Last Date|due date):\s*([A-Za-z]+\s+\d{1,2},\s*20\d{2}|\d{1,2}[/-]\d{1,2}[/-]20\d{2}(?:\s+at\s+\d{1,2}:\d{2}\s*(?:AM|PM)?)?)\b', text, re.IGNORECASE)
        if deadline_match:
            meta["deadline"] = deadline_match.group(1)

        # Notice Ref Number
        ref_match = re.search(r'\b(?:Ref|Circular|Notice No):\s*([A-Za-z0-9/-]+)\b', text, re.IGNORECASE)
        if ref_match:
            meta["notice_ref"] = ref_match.group(1)

        # Issuing Authority
        auth_match = re.search(r'\b(?:Issuing Authority|Issued by):\s*([A-Za-z\s,]+)\b', text, re.IGNORECASE)
        if auth_match:
            meta["issuing_authority"] = auth_match.group(1).strip()

        return meta

    def extract_tables_as_markdown(self, page) -> str:
        """
        Extract tables from PyMuPDF page as formatted markdown tables.
        Preserves row/column structure for course credit tables, timetables, and fee grids.
        """
        if not hasattr(page, "find_tables"):
            return ""

        try:
            tabs = page.find_tables()
            if not tabs or len(tabs.tables) == 0:
                return ""

            table_md_blocks = []
            for t_idx, tab in enumerate(tabs.tables, 1):
                df_rows = tab.extract()
                if not df_rows:
                    continue

                md_lines = []
                # Header row
                header = [str(cell).strip() if cell else "" for cell in df_rows[0]]
                md_lines.append("| " + " | ".join(header) + " |")
                md_lines.append("| " + " | ".join(["---"] * len(header)) + " |")

                # Data rows
                for row in df_rows[1:]:
                    row_cells = [str(cell).strip() if cell else "" for cell in row]
                    md_lines.append("| " + " | ".join(row_cells) + " |")

                table_md_blocks.append(f"\n[TABLE {t_idx}]\n" + "\n".join(md_lines) + "\n")

            return "\n".join(table_md_blocks)
        except Exception as e:
            logger.debug(f"Table extraction note: {str(e)}")
            return ""

    def attempt_ocr(self, page) -> str:
        """Attempt local OCR using PyMuPDF pixmap and pytesseract if available."""
        if not (self.ocr_enabled and HAS_PYTESSERACT):
            return ""

        try:
            pix = page.get_pixmap(dpi=150)
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            
            ocr_text = pytesseract.image_to_string(image)
            return self.clean_text(ocr_text)
        except Exception as e:
            logger.warning(f"OCR attempt failed: {str(e)}")
            return ""

    def process_pdf(self, pdf_path: Union[str, Path]) -> List[Dict[str, Any]]:
        """
        Extract page text, tables, multi-column layout, and rich metadata from a single PDF document.
        """
        if fitz is None:
            raise ImportError("PyMuPDF is not installed. Please run: pip install PyMuPDF")

        path = Path(pdf_path)
        if not path.is_file():
            logger.warning(f"File not found: {pdf_path}")
            return []

        doc_name = path.name
        file_hash = self.calculate_file_hash(path)
        mod_time = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(path.stat().st_mtime))

        try:
            doc = fitz.open(path)
        except Exception as e:
            logger.error(f"Cannot open PDF '{doc_name}': {str(e)}")
            return []

        try:
            total_pages = len(doc)
            if total_pages == 0:
                logger.warning(f"PDF file '{doc_name}' has 0 pages.")
                return []

            sample_text = ""
            for i in range(min(3, total_pages)):
                sample_text += (doc[i].get_text("text") or "") + "\n"

            doc_type = self.detect_document_type(doc_name, sample_text)
            version_str = self.detect_academic_year_or_version(sample_text)
            notice_meta = self.extract_notice_metadata(sample_text)

            doc_pages = []

            for page_idx in range(total_pages):
                page = doc[page_idx]

                # 1. Multi-column layout sorting: extract blocks in reading order
                blocks = page.get_text("blocks", sort=True)
                text_parts = []
                for b in blocks:
                    if b[4].strip():
                        text_parts.append(b[4].strip())
                raw_text = "\n\n".join(text_parts)

                # 2. Table extraction
                tables_md = self.extract_tables_as_markdown(page)
                if tables_md:
                    raw_text = raw_text + "\n\n" + tables_md

                cleaned_text = self.clean_text(raw_text)

                needs_ocr = False
                if len(cleaned_text) < self.ocr_min_text_length:
                    needs_ocr = True
                    ocr_result = self.attempt_ocr(page)
                    if ocr_result and len(ocr_result) >= self.ocr_min_text_length:
                        cleaned_text = ocr_result
                        needs_ocr = False

                doc_pages.append({
                    "document_name": doc_name,
                    "file_name": doc_name,
                    "file_hash": file_hash,
                    "page_number": page_idx + 1,  # 1-indexed human friendly
                    "source_path": str(path.resolve()),
                    "file_modified_time": mod_time,
                    "page_count": total_pages,
                    "document_type": doc_type,
                    "version_str": version_str,
                    "notice_date": notice_meta.get("notice_date"),
                    "deadline": notice_meta.get("deadline"),
                    "issuing_authority": notice_meta.get("issuing_authority"),
                    "text": cleaned_text,
                    "has_table": bool(tables_md),
                    "needs_ocr": needs_ocr
                })

            return doc_pages
        finally:
            doc.close()

    def process_directory(self, dir_path: Union[str, Path]) -> List[Dict[str, Any]]:
        """
        Recursively process all PDF files in a directory and build/update data/documents_manifest.json.
        Detects duplicate files by file hash to prevent double indexing.
        """
        directory = Path(dir_path)
        if not directory.exists() or not directory.is_dir():
            logger.warning(f"Directory not found: {dir_path}")
            return []

        pdf_files = sorted(list(directory.rglob("*.pdf")))
        all_pages = []
        seen_hashes = set()
        manifest_records = []

        for pdf_file in pdf_files:
            file_hash = self.calculate_file_hash(pdf_file)

            # Duplicate suppression check
            if file_hash in seen_hashes:
                logger.info(f"Skipping duplicate document content: {pdf_file.name} (hash={file_hash[:8]})")
                continue
            seen_hashes.add(file_hash)

            pages = self.process_pdf(pdf_file)
            if not pages:
                continue

            all_pages.extend(pages)

            first_page = pages[0]
            manifest_records.append({
                "document_id": f"doc_{file_hash[:10]}",
                "file_name": pdf_file.name,
                "relative_path": str(pdf_file.relative_to(directory)),
                "document_type": first_page.get("document_type", "general"),
                "academic_year": first_page.get("version_str", "2025"),
                "version": first_page.get("version_str", "v1.0"),
                "effective_date": first_page.get("notice_date", first_page.get("file_modified_time")[:10]),
                "page_count": len(pages),
                "file_hash": file_hash,
                "authority": "synthetic_fixture",
                "status": "active"
            })

        # Save manifest to data/documents_manifest.json
        manifest_path = directory.parent / "documents_manifest.json"
        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_records, f, indent=2)
            logger.info(f"Document manifest updated: {manifest_path} ({len(manifest_records)} documents)")
        except Exception as e:
            logger.warning(f"Could not save documents_manifest.json: {str(e)}")

        return all_pages
