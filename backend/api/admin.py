"""
Admin Management & System Operations API Router (Phases 7.5 & 7.6).
Exposes Admin controls for:
- User & Role Management (RBAC)
- Document Approvals, Rejections, Archival & Restores
- Quality Control Scans & Conflict Resolutions
- Knowledge Base Health Monitoring
- System Diagnostics
- Safety Backups, Validations & Recovery Restores
- Active Vector Index Rebuilds
Strictly requires ADMIN role for all endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.dependencies import ComponentRegistry, require_role
from src.permissions import ROLE_ADMIN
from src.auth import list_all_users, update_user_role, toggle_user_active, VALID_ROLES

router = APIRouter(prefix="/api/admin", tags=["Admin Suite"])

# Pydantic Schemas
class RoleUpdateRequest(BaseModel):
    role: str = Field(..., description="Target user role: student, faculty, or admin")

class ActiveToggleRequest(BaseModel):
    active: bool

class RejectDocumentRequest(BaseModel):
    rejection_reason: str = Field(..., min_length=3)

class RestoreDocumentRequest(BaseModel):
    target_governance: Optional[str] = "pending_review"

class ResolveQualityIssueRequest(BaseModel):
    resolution_action: str = Field(..., description="Action: mark_resolved, archive_document, replace_version, ignore")
    reason: Optional[str] = None

class CreateBackupRequest(BaseModel):
    note: Optional[str] = "Manual admin backup via REST API"

# ---------------------------------------------------------------------------
# 1. USER & ROLE MANAGEMENT
# ---------------------------------------------------------------------------

@router.get("/users")
def get_all_users(admin_user: dict = Depends(require_role(ROLE_ADMIN))):
    """Retrieve list of all registered users."""
    users = list_all_users()
    return {"users": users, "total": len(users)}

@router.patch("/users/{username}/role")
def update_role(
    username: str,
    payload: RoleUpdateRequest,
    admin_user: dict = Depends(require_role(ROLE_ADMIN))
):
    """Update role for a user (Admin only)."""
    clean_role = payload.role.strip().lower()
    if clean_role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}"
        )
    
    success = update_user_role(username, clean_role)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or role update failed."
        )
    
    return {"message": f"Successfully updated user '{username}' role to '{clean_role}'."}

@router.patch("/users/{username}/active")
def toggle_active(
    username: str,
    payload: ActiveToggleRequest,
    admin_user: dict = Depends(require_role(ROLE_ADMIN))
):
    """Toggle user active status."""
    success = toggle_user_active(username, payload.active)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or active status update failed."
        )
    return {"message": f"User '{username}' active status updated to {payload.active}."}


# ---------------------------------------------------------------------------
# 2. DOCUMENT GOVERNANCE & APPROVALS
# ---------------------------------------------------------------------------

@router.get("/documents")
def get_all_documents(
    status_filter: Optional[str] = None,
    doc_type: Optional[str] = None,
    admin_user: dict = Depends(require_role(ROLE_ADMIN))
):
    """List all documents in the system across all governance statuses."""
    doc_mgr = ComponentRegistry.get_doc_manager()
    docs = doc_mgr.list_documents(doc_type=doc_type, status=status_filter)
    return {"documents": docs, "total": len(docs)}

@router.post("/documents/{doc_id}/approve")
def approve_document(doc_id: str, admin_user: dict = Depends(require_role(ROLE_ADMIN))):
    """Approve pending document and integrate into active knowledge base."""
    try:
        doc_mgr = ComponentRegistry.get_doc_manager()
        res = doc_mgr.approve_document(doc_id=doc_id, user=admin_user)
        if not res.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=res.get("message") or res.get("error") or "Failed to approve document."
            )
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/documents/{doc_id}/reject")
def reject_document(
    doc_id: str,
    payload: RejectDocumentRequest,
    admin_user: dict = Depends(require_role(ROLE_ADMIN))
):
    """Reject pending document with recorded explanation."""
    try:
        doc_mgr = ComponentRegistry.get_doc_manager()
        res = doc_mgr.reject_document(
            doc_id=doc_id,
            rejection_reason=payload.rejection_reason,
            user=admin_user
        )
        if not res.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=res.get("message") or res.get("error") or "Failed to reject document."
            )
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/documents/{doc_id}/archive")
def archive_document(doc_id: str, admin_user: dict = Depends(require_role(ROLE_ADMIN))):
    """Archive document and exclude from active RAG search."""
    try:
        doc_mgr = ComponentRegistry.get_doc_manager()
        res = doc_mgr.archive_document(doc_id=doc_id, user=admin_user)
        if not res.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=res.get("message") or res.get("error") or "Failed to archive document."
            )
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/documents/{doc_id}/restore")
def restore_document(
    doc_id: str,
    payload: Optional[RestoreDocumentRequest] = None,
    admin_user: dict = Depends(require_role(ROLE_ADMIN))
):
    """Restore archived or rejected document back into governance workflow."""
    try:
        target_gov = payload.target_governance if payload else "pending_review"
        doc_mgr = ComponentRegistry.get_doc_manager()
        res = doc_mgr.restore_document(doc_id=doc_id, target_governance=target_gov, user=admin_user)
        if not res.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=res.get("message") or res.get("error") or "Failed to restore document."
            )
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/documents/{doc_id}")
def delete_document(doc_id: str, admin_user: dict = Depends(require_role(ROLE_ADMIN))):
    """Permanently purge document record and raw PDF file."""
    doc_mgr = ComponentRegistry.get_doc_manager()
    try:
        res = doc_mgr.delete_document(doc_id=doc_id, user=admin_user)
        if not res.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=res.get("message", res.get("error", "Failed to delete document."))
            )
        return res
    except PermissionError as pe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(pe)
        )



# ---------------------------------------------------------------------------
# 3. QUALITY CONTROL
# ---------------------------------------------------------------------------

@router.get("/quality")
def run_quality_scan(admin_user: dict = Depends(require_role(ROLE_ADMIN))):
    """Execute Phase 6.4 Quality Control scan (duplicates, conflicts, stale docs)."""
    qc_mgr = ComponentRegistry.get_qc_manager()
    scan_results = qc_mgr.run_quality_scan()
    issues = qc_mgr.get_quality_issues()
    return {
        "scan_summary": scan_results,
        "quality_issues": issues
    }

@router.post("/quality/{issue_id}/resolve")
def resolve_quality_issue(
    issue_id: int,
    payload: ResolveQualityIssueRequest,
    admin_user: dict = Depends(require_role(ROLE_ADMIN))
):
    """Resolve a detected document quality issue."""
    qc_mgr = ComponentRegistry.get_qc_manager()
    res = qc_mgr.resolve_quality_issue(
        issue_id=issue_id,
        resolution_action=payload.resolution_action,
        user=admin_user,
        reason=payload.reason
    )
    if not res.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=res.get("error", "Failed to resolve quality issue.")
        )
    return res


# ---------------------------------------------------------------------------
# 4. KNOWLEDGE BASE HEALTH & DIAGNOSTICS
# ---------------------------------------------------------------------------

@router.get("/health")
def get_kb_health(admin_user: dict = Depends(require_role(ROLE_ADMIN))):
    """Retrieve Knowledge Base Health status (Phase 6.5)."""
    diag_mgr = ComponentRegistry.get_diag_manager()
    diag_results = diag_mgr.run_full_diagnostics(user=admin_user)
    kb_health = diag_results.get("kb_health", {})
    return {"kb_health": kb_health, "overall_status": diag_results.get("overall_status")}

@router.get("/diagnostics")
def get_system_diagnostics(admin_user: dict = Depends(require_role(ROLE_ADMIN))):
    """Run Phase 6.6 Full System Diagnostics."""
    diag_mgr = ComponentRegistry.get_diag_manager()
    diag_results = diag_mgr.run_full_diagnostics(user=admin_user)
    return diag_results


# ---------------------------------------------------------------------------
# 5. BACKUP, RESTORE & RECOVERY
# ---------------------------------------------------------------------------

@router.get("/backups")
def list_backups(admin_user: dict = Depends(require_role(ROLE_ADMIN))):
    """List available system safety backups."""
    diag_mgr = ComponentRegistry.get_diag_manager()
    backups = diag_mgr.list_backups(user=admin_user)
    return {"backups": backups, "total": len(backups)}

@router.post("/backups")
def create_backup(
    payload: Optional[CreateBackupRequest] = None,
    admin_user: dict = Depends(require_role(ROLE_ADMIN))
):
    """Create a complete system safety backup (SQLite + Manifest + FAISS + Files)."""
    diag_mgr = ComponentRegistry.get_diag_manager()
    note = payload.note if payload else "Manual admin backup"
    res = diag_mgr.create_backup(user=admin_user, note=note)
    if not res.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=res.get("error", "Backup creation failed.")
        )
    return res

@router.post("/backups/{backup_id}/validate")
def validate_backup(backup_id: str, admin_user: dict = Depends(require_role(ROLE_ADMIN))):
    """Validate checksums and structure of a safety backup."""
    diag_mgr = ComponentRegistry.get_diag_manager()
    res = diag_mgr.validate_backup(backup_id)
    return res

@router.post("/backups/{backup_id}/restore")
def restore_backup(backup_id: str, admin_user: dict = Depends(require_role(ROLE_ADMIN))):
    """Restore system to a previously saved safety backup."""
    diag_mgr = ComponentRegistry.get_diag_manager()
    res = diag_mgr.restore_backup(backup_id=backup_id, user=admin_user)
    if not res.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=res.get("error", "Backup restoration failed.")
        )
    return res

@router.post("/index/rebuild")
def rebuild_faiss_index(admin_user: dict = Depends(require_role(ROLE_ADMIN))):
    """Rebuild active FAISS index safely from approved document chunks."""
    doc_mgr = ComponentRegistry.get_doc_manager()
    res = doc_mgr.rebuild_active_faiss_index()
    if not res.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=res.get("error", "FAISS index rebuild failed.")
        )
    return res
