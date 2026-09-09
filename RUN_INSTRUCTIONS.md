# 🚀 How to Run RAXEL Locally (React + FastAPI)

This guide provides step-by-step instructions and exact commands to run the **AI-Powered College Knowledge Assistant (RAXEL)** with the **React + Vite** single-page frontend and **FastAPI** REST backend.

---

## 📋 Architecture Overview

```
                   React + Vite SPA (http://localhost:5173)
                                      │
                                  REST / JSON
                                      │
                   FastAPI Backend (http://localhost:8000/api)
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
     Auth & Session DB           RAG Pipeline             Document Ops
     (SQLite raxel.db)       (FAISS / SentenceTrans /     (PyMuPDF / Quality /
                                Ollama llama3:latest)       Diagnostics / Backups)
```

---

## 🛠️ Step-by-Step Launch Instructions

### Step 1: Start Ollama LLM Service (Terminal 1)

Ensure Ollama is running locally with the `llama3:latest` model loaded.

```powershell
ollama serve
```

---

### Step 2: Start FastAPI REST Backend (Terminal 2)

Open a terminal window, navigate to the project root directory, activate the Python virtual environment, and launch FastAPI with Uvicorn:

```powershell
# Open terminal in project root & activate venv:
.\venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --reload --port 8000
```

- **FastAPI Server Base URL**: `http://localhost:8000`
- **Interactive OpenAPI Documentation (Swagger UI)**: `http://localhost:8000/docs`

---

### Step 3: Start React + Vite Frontend (Terminal 3)

Open a third terminal window, navigate to the `frontend/` directory, and launch the Vite development server:

```powershell
cd frontend
npm run dev
```

- **Vite Development Server URL**: `http://localhost:5173`

---

### Step 4: Open RAXEL Web Application

Open your web browser and navigate to:

👉 **[http://localhost:5173](http://localhost:5173)**

---

## 👤 Available User Roles & Access Modes

| User Type | Login Requirement | Features & Capabilities |
| :--- | :--- | :--- |
| **🎓 Guest Student** | **No login required** | Ask college questions, grounded RAG answers, official document & page citations, follow-up clarification. |
| **🎓 Registered Student** | Sign in / Signup | Personalized chat session, knowledge sources directory, user profile settings. |
| **👨‍🏫 Faculty** | Login required | Faculty workspace, upload PDF documents with metadata, review submission statuses, self-approval prevention. |
| **⚙️ Admin** | Login required | Full governance suite, document approvals/rejections, quality control, component health & diagnostics, safety backups, atomic safety restores, active vector index rebuilds. |

---

## 🛠️ Useful Commands & Test Runners

| Action / Component | Command | Notes / Location |
| :--- | :--- | :--- |
| **Start Ollama** | `ollama serve` | Port `11434` |
| **FastAPI Backend** | `python -m uvicorn backend.main:app --reload --port 8000` | Port `8000` |
| **React Frontend** | `cd frontend && npm run dev` | Port `5173` |
| **Backend API Tests** | `python scripts/test_phase7_backend_api.py` | Full REST endpoint validation |
| **System Diagnostics Suite** | `python -m unittest scripts/test_phase6_6.py` | Backup, restore, FAISS rebuild tests |
| **Governance Approval Suite** | `python -m unittest scripts/test_phase6_3.py` | Role permissions & approval tests |
| **Quality Control Suite** | `python -m unittest scripts/test_phase6_4.py` | Conflict & duplicate detection tests |
