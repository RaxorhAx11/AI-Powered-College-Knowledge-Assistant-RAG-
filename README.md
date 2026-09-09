# AI-Powered College Knowledge Assistant (RAXEL)

An offline-first, student-facing AI assistant built using Retrieval-Augmented Generation (RAG) to answer questions using ingested college documents, providing exact page citations and preventing hallucinations.

---

## 📌 Overview & Problem Statement

College rules, syllabus details, exam policies, attendance criteria, timetables, and notices are often spread across numerous PDFs and web pages. Students frequently receive inaccurate or outdated information when asking peers or general LLMs.

**RAXEL** solves this problem by providing a student-friendly AI assistant that:
1. Answers questions **strictly** using ingested college PDF documents.
2. Clearly displays **programmatically verified source document and page numbers** for all cited answers.
3. Automatically **refuses to answer** (safe fallback) when ingested documents do not contain sufficient evidence, preventing hallucinations.
4. Detects **conflicting document rules**, handles **partial evidence**, provides **ambiguity clarification prompts**, and resists **prompt injection** embedded in PDFs.
5. Implements a **multi-role governance lifecycle** (Student, Faculty, Admin) ensuring unapproved or draft documents are strictly isolated from student search until approved by an Admin.
6. Includes **Admin system diagnostics**, local timestamped **safety backups**, **atomic safety restores**, and **active vector store index rebuilds**.

---

## 🏗️ System Architecture

```
                                  ┌─────────────────────────────────────────┐
                                  │   React 19 + Vite SPA (Port 5173)       │
                                  └────────────────────┬────────────────────┘
                                                       │  REST API (JSON)
                                                       ▼
                                  ┌─────────────────────────────────────────┐
                                  │   FastAPI REST Backend (Port 8000)      │
                                  └────────────────────┬────────────────────┘
                                                       │
         ┌─────────────────────────────────────────────┼─────────────────────────────────────────────┐
         ▼                                             ▼                                             ▼
┌──────────────────┐                         ┌──────────────────┐                          ┌──────────────────┐
│  Auth & Session  │                         │   RAG Pipeline   │                          │  Document & Admin│
│ SQLite raxel.db  │                         │ Hybrid Retriever │                          │ Governance Engine│
└──────────────────┘                         └─────────┬────────┘                          └─────────┬────────┘
                                                       │                                             │
                                     ┌─────────────────┴─────────────────┐                           │
                                     ▼                                   ▼                           ▼
                           ┌───────────────────┐               ┌───────────────────┐       ┌───────────────────┐
                           │   FAISS Vector    │               │  Local Ollama     │       │  Audit Logs &     │
                           │   + BM25 Store    │               │ (llama3:latest)   │       │ Safe Backup System│
                           └───────────────────┘               └───────────────────┘       └───────────────────┘
```

### Component Details
- **Frontend**: React 19 single-page application built with Vite, Tailwind CSS, and Lucide React icons. Features dark mode UI with glassmorphism design.
- **Backend**: FastAPI REST API providing modular routers:
  - `/api/auth`: Login, signup, user session context, logout.
  - `/api/chat`: Grounded RAG query processing, response streaming, history retrieval.
  - `/api/documents`: Document upload, metadata management, user document status.
  - `/api/admin`: Document governance (approval/rejection), quality control, component diagnostics, local backups, atomic restore, and index rebuilding.
- **Database**: Local SQLite database (`data/raxel.db`) configured with Write-Ahead Logging (WAL) and parameterized queries. Stores users, salted PBKDF2 password hashes, document metadata, audit logs, and quality control flags.
- **Ingestion & Processing**: PyMuPDF table extraction (`page.find_tables()`), scanned page OCR detection (`pytesseract`), duplicate file hashing (MD5/SHA-256), and layout sorting.
- **Retrieval Engine**: Dense cosine similarity search via FAISS (`all-MiniLM-L6-v2` embeddings) combined with BM25 keyword matching for hybrid retrieval.
- **LLM Inference**: Local offline inference via Ollama (`llama3:latest`).
- **Validation**: Citation validator and answer grounding validator to prevent hallucinated citations and ungrounded statements.

---

## 🛠️ Setup and Installation

### 1. Prerequisites
- **Python**: 3.10 or higher
- **Node.js**: 18.0 or higher
- **Ollama**: Installed and running locally
- **Tesseract OCR** *(Optional)*: Required for OCR text extraction on scanned PDFs.

### 2. Environment Setup & Dependencies

```powershell
# 1. Clone repository & enter workspace
git clone https://github.com/your-username/raxel.git
cd raxel

# 2. Create and activate Python virtual environment
python -m venv venv
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
# source venv/bin/activate

# 3. Install Python backend dependencies
pip install -r requirements.txt

# 4. Install Frontend npm dependencies
cd frontend
npm install
cd ..
```

### 3. Initialize Ollama LLM Model
Ensure Ollama is running and pull the `llama3:latest` model:
```powershell
ollama pull llama3:latest
```

---

## 🚀 How to Run Frontend and Backend

### Terminal 1: Start Local Ollama LLM
```powershell
ollama serve
```

### Terminal 2: Launch FastAPI Backend Server
```powershell
# Activate venv in project root
.\venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --reload --port 8000
```
- **Backend API**: `http://localhost:8000`
- **Interactive OpenAPI Documentation (Swagger)**: `http://localhost:8000/docs`

### Terminal 3: Launch React + Vite Frontend
```powershell
cd frontend
npm run dev
```
- **Web Application UI**: 👉 **`http://localhost:5173`**

---

## 👥 Student, Faculty, and Admin Flows

### 1. 🎓 Student Flow (Guest & Registered)
- **Guest Mode**: Access RAG search instantly without signing in.
- **Registered Mode**: Sign up / Log in to maintain chat history and personalized profile settings.
- **Interactive RAG Search**:
  - Ask natural language questions regarding college rules, exam schedules, attendance requirements, or course syllabi.
  - View streamed responses with exact document title and page citations (e.g. `[GLS_Academic_Regulations_2025.pdf - Page 1]`).
  - View confidence scores, ambiguity clarification prompts when queries are vague, or safe fallback messages when evidence is missing.
- **Knowledge Sources Directory**: Browse the list of approved active college documents, filtered by category and academic year.

### 2. 👨‍🏫 Faculty Flow
- **Authentication**: Log in with Faculty credentials.
- **Document Upload**:
  - Upload college PDFs (up to 25 MB) with metadata: Title, Document Type (`academic_regulations`, `syllabus`, `timetable`, `notices`, etc.), Academic Year, Version, Effective Date, and Description.
  - Automated PDF validation checks magic bytes (`%PDF-`), strips unsafe path characters, and computes MD5 hash to prevent duplicate uploads.
- **Submission Staging**:
  - PDF is extracted, parsed for tables, chunked, and embedded into SQLite.
  - Status is automatically set to `pending_review` (`retrieval_enabled = 0`).
  - **Self-Approval Prevention**: Faculty cannot approve documents (including their own submissions).
- **Status Tracking & Audit Feedback**: Faculty can track upload status and inspect Admin rejection reasons if revisions are required.

### 3. ⚙️ Admin Flow
- **Authentication**: Log in with Admin credentials.
- **Governance & Approval Panel**:
  - View documents categorized into tabs: *Pending Review*, *Approved*, *Rejected*, *Archived*, and *All Documents*.
  - Inspect uploader details, file hash, chunk counts, and OCR status.
  - Execute actions: **Approve** (enables retrieval and rebuilds vector store), **Reject** (requires mandatory rejection reason), **Archive**, or **Restore**.
- **Document Management**: Perform permanent document deletion (with confirmation modal), force reprocessing, or trigger manual index rebuilds.
- **Quality Control**: Inspect flagged issues such as exact duplicates, policy conflicts, superseded/outdated document versions, and future effective dates.
- **System Diagnostics**: Execute read-only system health checks covering Database schema, File Storage integrity, Document Manifest consistency, FAISS Vector Index integrity, Embedding Model alignment, and Ollama LLM availability.
- **Safety Backups & Atomic Restore**:
  - Create timestamped local backup archives (`data/backups/raxel_backup_YYYYMMDD_HHMMSS/`).
  - Perform fail-safe atomic restores from backup archives with isolated validation.
- **Vector Store Rebuild**: Trigger manual or automatic rebuilding of the FAISS vector index strictly from active, approved documents.

---

## 🔄 Document Lifecycle: Upload → Approval → RAG Flow

```
[1. Upload PDF & Metadata] (Faculty/Admin)
           │
           ▼
[2. Ingestion Pipeline] ──► Extract Text, Parse Tables, Detect OCR, Hash MD5, Generate Embeddings
           │
           ▼
[3. Storage & Pending State] ──► SQLite (status: indexed, governance_status: pending_review, retrieval_enabled: 0)
           │                    *CRITICAL SAFETY RULE: UNAPPROVED DOCUMENTS ARE NEVER USED IN STUDENT RAG*
           ▼
[4. Admin Governance Review] ──► Admin inspects metadata, chunk counts & hash in Admin Panel
           │
           ├──► [Reject] ──► governance_status: rejected (rejection reason saved in audit log)
           │
           ▼
[5. Approve Document] ──► governance_status: approved, retrieval_enabled: 1
           │
           ▼
[6. Atomic FAISS Rebuild] ──► rebuild_active_faiss_index() queries ONLY approved active documents
           │
           ▼
[7. Active Student RAG] ──► Students query active index and receive grounded answers with exact page citations
```

---

## 🛠️ Delete, Backup, Recovery, and Index Rebuild

### 1. Document Archive & Permanent Deletion
- **Archive**: Disables retrieval (`retrieval_enabled = 0`, `governance_status = archived`). The document is excluded from the FAISS vector index upon the next rebuild, but file and metadata remain stored for record-keeping.
- **Permanent Delete** *(Admin Only)*: Deletes PDF file from disk, purges database records, writes an immutable audit log entry, and triggers an immediate atomic rebuild of the FAISS vector store.

### 2. Local Safety Backups
- Admins can create timestamped backups at any time via the Admin Panel or API (`POST /api/admin/backups/create`).
- Backups are stored in `data/backups/raxel_backup_YYYYMMDD_HHMMSS/` containing:
  - Database snapshot (`raxel.db`)
  - Document manifest (`documents_manifest.json`)
  - Active FAISS vector store (`vectorstore/index.faiss` and `metadata.pkl`)
  - PDF document repository (`documents/`)
  - `backup_manifest.json` with SHA-256 checksums for every backed-up file.

### 3. Recovery & Atomic Safety Restore
- Admins can restore the system to any previously created backup point.
- **Safety Safeguard Process**:
  1. System automatically creates an emergency safety backup of current state before making any changes.
  2. Target backup files are extracted into an isolated temporary folder (`data/backups/temp_restore`).
  3. Staged Database, manifest, FAISS index, and retrieval sanity are validated in isolation.
  4. Only if validation succeeds, active system files are atomically replaced.
  5. If validation fails, the restore aborts immediately and the existing active system remains completely untouched.

### 4. Safe Active Index Rebuild Engine
- **Engine Function**: `rebuild_active_faiss_index()` in `src/document_manager.py`.
- **Query Filter**: Rebuilds FAISS index strictly from active approved documents (`processing_status == 'indexed' AND governance_status == 'approved' AND retrieval_enabled == 1`).
- **Atomic Swap**: New index is generated in a temporary folder. Upon successful embedding generation and dimension check, the temporary index atomically overwrites `data/vectorstore/`. If rebuilding encounters an error, the active index is left completely intact.

---

## 📊 Verification & Evaluation Test Suites

RAXEL includes comprehensive unit and integration test suites covering all system phases:

```powershell
# Run FastAPI Backend REST API Test Suite
python scripts/test_phase7_backend_api.py

# Run Admin System Diagnostics, Backup, Restore & Rebuild Test Suite
python -m unittest scripts/test_phase6_6.py

# Run Governance & Approval Test Suite
python -m unittest scripts/test_phase6_3.py

# Run Quality Control & Conflict Test Suite
python -m unittest scripts/test_phase6_4.py

# Run PDF Ingestion & Table Parsing Suite
python -m unittest scripts/test_phase2.py
```

---

## 💡 Grounded Query Demonstrations

### 1. Grounded Question with Page Citation
- **User Question**: *"What is the minimum attendance requirement for exams?"*
- **RAXEL Response**: *"The minimum attendance requirement for all undergraduate and postgraduate students is 75% in every registered course to be eligible for End-Semester Examinations."*
- **Citations**: `GLS_Academic_Regulations_2025.pdf - Page 1`

### 2. Conflict Handling Disclosure
- **User Question**: *"What is the attendance percentage required?"*
- **RAXEL Response**: *"The approved knowledge base contains conflicting information about this topic. One document ('Academic Regulations 2025.pdf') states 75%, while another document ('Academic Regulations 2026.pdf') states 80%. Please verify with the relevant college authority."*
- **Citations**: `Academic Regulations 2025.pdf - Page 1`, `Academic Regulations 2026.pdf - Page 1`

### 3. Out-of-Scope Query Safe Fallback
- **User Question**: *"What is the recipe for chocolate cake?"*
- **RAXEL Response**: *"I could not find enough information in the college documents to answer this question confidently."*
- **Citations**: None *(Zero hallucinated citations)*.
