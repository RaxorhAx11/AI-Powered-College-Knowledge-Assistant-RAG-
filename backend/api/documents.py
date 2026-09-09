"""
Document Management API Router (Phase 7.4).
Exposes document listing, metadata inspection, and PDF upload workflows for Faculty & Admin.
Reuses src/document_manager.py for PDF validation, safe file storage, duplicate checks, and indexing.
"""

from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse

from backend.dependencies import ComponentRegistry, require_role, get_current_user, get_current_user_optional
from src.permissions import ROLE_FACULTY, ROLE_STUDENT, ROLE_ADMIN
from src.document_manager import validate_pdf_bytes, SUGGESTED_DOC_TYPES

router = APIRouter(prefix="/api/documents", tags=["Document Management"])

@router.get("")
def list_documents(
    doc_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    user: dict = Depends(get_current_user_optional)
):
    """
    List documents.
    Faculty can view documents they uploaded or all active documents.
    Admin views all documents across governance statuses.
    """
    doc_mgr = ComponentRegistry.get_doc_manager()
    docs = doc_mgr.list_documents(doc_type=doc_type, status=status_filter)
    
    # Filter by user if faculty (unless viewing approved active docs)
    if user.get("role") == ROLE_FACULTY:
        # Include documents uploaded by this faculty member OR approved documents
        docs = [
            d for d in docs 
            if d.get("uploaded_by") == user.get("username") or d.get("status") == "indexed"
        ]
    elif user.get("role") == ROLE_STUDENT:
        # Students only see approved indexed documents
        docs = [d for d in docs if d.get("status") == "indexed"]
        
    return {"documents": docs, "total": len(docs)}

@router.get("/suggested-types")
def get_suggested_types():
    """Return available document types for upload metadata forms."""
    return {"doc_types": SUGGESTED_DOC_TYPES}

@router.get("/{doc_id}")
def get_document_details(doc_id: str, user: dict = Depends(get_current_user_optional)):
    """Retrieve document metadata and audit history."""
    doc_mgr = ComponentRegistry.get_doc_manager()
    doc = doc_mgr.get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )
    
    is_approved = (doc.get("governance_status") == "approved" or doc.get("status") == "indexed")
    if not is_approved and user.get("role") not in [ROLE_FACULTY, ROLE_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view unapproved or restricted document details."
        )
    
    audit_logs = doc_mgr.get_audit_logs(doc_id=doc_id)
    return {"document": doc, "audit_logs": audit_logs}

@router.get("/{doc_id}/download")
def download_document(
    doc_id: str,
    disposition: Optional[str] = "inline",
    user: dict = Depends(get_current_user_optional)
):
    """Download/stream raw document PDF file."""
    doc_mgr = ComponentRegistry.get_doc_manager()
    doc = doc_mgr.get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )
    is_approved = (doc.get("governance_status") == "approved" or doc.get("status") == "indexed")
    if not is_approved and user.get("role") not in [ROLE_FACULTY, ROLE_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view non-indexed or unapproved documents."
        )
    stored_path = doc.get("stored_path")
    if not stored_path or not Path(stored_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file path not found on server disk."
        )
    
    disp_type = "attachment" if disposition == "attachment" else "inline"
    filename = doc.get("original_filename") or f"{doc.get('title', 'document')}.pdf"
    
    headers = {
        "Content-Disposition": f'{disp_type}; filename="{filename}"'
    }

    return FileResponse(
        path=stored_path,
        media_type="application/pdf",
        filename=filename,
        headers=headers,
        content_disposition_type=disp_type
    )

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    doc_type: str = Form(...),
    academic_year: Optional[str] = Form("2024-2025"),
    version: Optional[str] = Form("1.0"),
    effective_date: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    user: dict = Depends(require_role(ROLE_FACULTY))
):
    """
    Faculty & Admin PDF upload endpoint.
    Validates PDF file, stores securely, creates SQLite record, and runs extraction/indexing.
    """
    file_bytes = await file.read()
    
    is_valid, err_msg = validate_pdf_bytes(file_bytes, file.filename)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file upload: {err_msg}"
        )
    
    doc_mgr = ComponentRegistry.get_doc_manager()
    
    upload_res = doc_mgr.upload_document(
        file_bytes=file_bytes,
        filename=file.filename,
        title=title,
        document_type=doc_type,
        academic_year=academic_year or "2024-2025",
        version=version or "1.0",
        effective_date=effective_date,
        description=description,
        user=user
    )
    
    if not upload_res.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=upload_res.get("message") or upload_res.get("error") or "Document upload failed."
        )
    
    doc_id = upload_res.get("doc_id") or upload_res.get("document", {}).get("document_id")
    if not doc_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve document ID after upload."
        )
    
    # Process & index document (runs extraction, chunking, embeddings, FAISS staging/indexing)
    process_res = doc_mgr.process_and_index_document(doc_id=doc_id, user=user)
    
    return {
        "message": process_res.get("message", "Document uploaded and processed successfully."),
        "doc_id": doc_id,
        "upload_info": upload_res,
        "process_info": process_res
    }

@router.delete("/{doc_id}")
def delete_document(
    doc_id: str,
    user: dict = Depends(require_role(ROLE_FACULTY))
):
    """
    Delete document endpoint.
    Faculty can delete their own uploaded documents.
    Admin can delete any document.
    Students are forbidden from deleting documents.
    """
    doc_mgr = ComponentRegistry.get_doc_manager()
    try:
        res = doc_mgr.delete_document(doc_id=doc_id, user=user)
        if not res.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=res.get("message", "Failed to delete document.")
            )
        return res
    except PermissionError as pe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(pe)
        )

