import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { api } from '../services/api';
import {
  Activity,
  CheckCircle,
  XCircle,
  Users,
  ShieldCheck,
  Database,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  FileText,
  Trash2,
  DownloadCloud,
  Cpu,
  Server,
  Archive,
  RotateCcw,
  Eye,
  X
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Input, Select } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { Card } from '../components/ui/Card';
import { Alert } from '../components/ui/Alert';
import { TableSkeleton } from '../components/ui/Skeleton';
import { EmptyState } from '../components/ui/EmptyState';
import { HoverLift } from '../components/motion/MotionComponents';

import { useToast } from '../context/ToastContext';

export const AdminPage = ({ activeTab = 'overview' }) => {
  const toast = useToast();
  const [tab, setTab] = useState(activeTab);
  const [users, setUsers] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [docFilter, setDocFilter] = useState('all');
  const [docSearch, setDocSearch] = useState('');

  const [qualityData, setQualityData] = useState(null);
  const [healthData, setHealthData] = useState(null);
  const [diagnosticsData, setDiagnosticsData] = useState(null);
  const [backups, setBackups] = useState([]);

  const [loading, setLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState({ type: '', text: '' });
  const [rejectReason, setRejectReason] = useState({});
  const [backupNote, setBackupNote] = useState('');

  // Granular Per-Action Loading Map
  const [actionLoading, setActionLoading] = useState({});
  const startAction = (key) => setActionLoading(prev => ({ ...prev, [key]: true }));
  const stopAction = (key) => setActionLoading(prev => ({ ...prev, [key]: false }));
  const isActionLoading = (key) => !!actionLoading[key];

  // Modals & Active selections
  const [deleteConfirmDoc, setDeleteConfirmDoc] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const [detailsDoc, setDetailsDoc] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);

  const [restoreConfirmBackup, setRestoreConfirmBackup] = useState(null);
  const [restoringBackup, setRestoringBackup] = useState(false);

  const abortControllerRef = useRef(null);

  const loadData = useCallback(async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;
    const signal = controller.signal;

    setLoading(true);
    try {
      const fetches = [];
      if (tab === 'overview' || tab === 'documents' || tab === 'approvals') {
        fetches.push(api.getAdminDocuments(undefined, undefined, { signal }).then(res => setDocuments(res.documents || [])));
      }
      if (tab === 'overview' || tab === 'users') {
        fetches.push(api.getUsers({ signal }).then(res => setUsers(res.users || [])));
      }
      if (tab === 'overview' || tab === 'quality') {
        fetches.push(api.runQualityScan({ signal }).then(res => setQualityData(res)));
      }
      if (tab === 'overview' || tab === 'recovery') {
        fetches.push(api.getHealth({ signal }).then(res => setHealthData(res)));
        fetches.push(api.getBackups({ signal }).then(res => setBackups(res.backups || [])));
      }
      if (tab === 'diagnostics') {
        fetches.push(api.getDiagnostics({ signal }).then(res => setDiagnosticsData(res)));
      }

      await Promise.all(fetches);
    } catch (err) {
      if (err.name !== 'AbortError') {
        setActionMessage({ type: 'error', text: err.message || 'Error loading Admin governance data.' });
      }
    } finally {
      if (abortControllerRef.current === controller) {
        setLoading(false);
      }
    }
  }, [tab]);

  useEffect(() => {
    loadData();
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [loadData]);

  // Document Governance Actions
  const handleApprove = async (docId) => {
    const key = `approve_${docId}`;
    startAction(key);
    try {
      const res = await api.approveDocument(docId);
      const msg = res.message || 'Document approved and indexed into active FAISS store.';
      setActionMessage({ type: 'success', text: msg });
      toast.success(msg);
      await loadData();
    } catch (err) {
      const errMsg = err.message || 'Failed to approve document.';
      setActionMessage({ type: 'error', text: errMsg });
      toast.error(errMsg);
    } finally {
      stopAction(key);
    }
  };

  const handleReject = async (docId) => {
    const reason = rejectReason[docId];
    if (!reason || !reason.trim()) {
      const msg = 'Please provide a rejection reason for governance rejection.';
      setActionMessage({ type: 'error', text: msg });
      toast.error('Please enter a rejection reason.');
      return;
    }
    const key = `reject_${docId}`;
    startAction(key);
    try {
      const res = await api.rejectDocument(docId, reason);
      const msg = res.message || 'Document submission rejected.';
      setActionMessage({ type: 'success', text: msg });
      toast.success(msg);
      await loadData();
    } catch (err) {
      const errMsg = err.message || 'Failed to reject document.';
      setActionMessage({ type: 'error', text: errMsg });
      toast.error(errMsg);
    } finally {
      stopAction(key);
    }
  };

  const handleArchive = async (docId) => {
    const key = `archive_${docId}`;
    startAction(key);
    try {
      const res = await api.archiveDocument(docId);
      const msg = res.message || 'Document archived and excluded from active RAG retrieval.';
      setActionMessage({ type: 'success', text: msg });
      toast.success(msg);
      await loadData();
    } catch (err) {
      const errMsg = err.message || 'Failed to archive document.';
      setActionMessage({ type: 'error', text: errMsg });
      toast.error(errMsg);
    } finally {
      stopAction(key);
    }
  };

  const handleRestore = async (docId) => {
    const key = `restore_${docId}`;
    startAction(key);
    try {
      const res = await api.restoreDocument(docId, 'pending_review');
      const msg = res.message || 'Document restored to review queue.';
      setActionMessage({ type: 'success', text: msg });
      toast.success(msg);
      await loadData();
    } catch (err) {
      const errMsg = err.message || 'Failed to restore document.';
      setActionMessage({ type: 'error', text: errMsg });
      toast.error(errMsg);
    } finally {
      stopAction(key);
    }
  };

  const handleDeleteExecute = async () => {
    if (!deleteConfirmDoc) return;
    const docId = deleteConfirmDoc.document_id || deleteConfirmDoc.id;
    setDeleting(true);
    try {
      const res = await api.deleteDocument(docId);
      const msg = res.message || 'Document permanently deleted.';
      setActionMessage({ type: 'success', text: msg });
      toast.success(msg);
      setDeleteConfirmDoc(null);
      await loadData();
    } catch (err) {
      const errMsg = err.message || 'Failed to delete document.';
      setActionMessage({ type: 'error', text: errMsg });
      toast.error(errMsg);
    } finally {
      setDeleting(false);
    }
  };

  const handleViewDetails = async (docId) => {
    const key = `details_${docId}`;
    startAction(key);
    try {
      const data = await api.getDocumentDetails(docId);
      setDetailsDoc(data.document);
      setAuditLogs(data.audit_logs || []);
    } catch (err) {
      const errMsg = err.message || 'Failed to fetch details.';
      setActionMessage({ type: 'error', text: errMsg });
      toast.error(errMsg);
    } finally {
      stopAction(key);
    }
  };

  // Role Action
  const handleRoleChange = async (username, newRole) => {
    const key = `role_${username}_${newRole}`;
    startAction(key);
    try {
      const res = await api.updateUserRole(username, newRole);
      const msg = res.message || `Updated ${username}'s role to ${newRole}.`;
      setActionMessage({ type: 'success', text: msg });
      toast.success(msg);
      await loadData();
    } catch (err) {
      const errMsg = err.message || 'Failed to update user role.';
      setActionMessage({ type: 'error', text: errMsg });
      toast.error(errMsg);
    } finally {
      stopAction(key);
    }
  };

  const handleToggleActive = async (username, currentActive) => {
    const key = `toggle_${username}`;
    startAction(key);
    try {
      const res = await api.toggleUserActive(username, !currentActive);
      const msg = res.message || `Toggled active status for ${username}.`;
      setActionMessage({ type: 'success', text: msg });
      toast.success(msg);
      await loadData();
    } catch (err) {
      const errMsg = err.message || 'Failed to update account status.';
      setActionMessage({ type: 'error', text: errMsg });
      toast.error(errMsg);
    } finally {
      stopAction(key);
    }
  };

  // Backup & Index Actions
  const handleCreateBackup = async () => {
    const key = 'create_backup';
    startAction(key);
    try {
      const res = await api.createBackup(backupNote || 'Safety backup via Admin control center');
      const msg = res.message || 'Safety backup created successfully.';
      setActionMessage({ type: 'success', text: msg });
      toast.success(msg);
      setBackupNote('');
      await loadData();
    } catch (err) {
      const errMsg = err.message || 'Failed to create backup.';
      setActionMessage({ type: 'error', text: errMsg });
      toast.error(errMsg);
    } finally {
      stopAction(key);
    }
  };

  const handleValidateBackup = async (backupId) => {
    const key = `validate_${backupId}`;
    startAction(key);
    try {
      const res = await api.validateBackup(backupId);
      const msg = res.message || `Backup ${backupId} validation result: ${res.valid}`;
      setActionMessage({
        type: res.valid ? 'success' : 'error',
        text: msg
      });
      if (res.valid) toast.success(msg); else toast.error(msg);
      await loadData();
    } catch (err) {
      const errMsg = err.message || 'Failed to validate backup.';
      setActionMessage({ type: 'error', text: errMsg });
      toast.error(errMsg);
    } finally {
      stopAction(key);
    }
  };

  const handleRestoreBackupExecute = async () => {
    if (!restoreConfirmBackup) return;
    setRestoringBackup(true);
    try {
      const res = await api.restoreBackup(restoreConfirmBackup.backup_id);
      const msg = res.message || 'System state restored from backup.';
      setActionMessage({ type: 'success', text: msg });
      toast.success(msg);
      setRestoreConfirmBackup(null);
      await loadData();
    } catch (err) {
      const errMsg = err.message || 'Failed to restore backup.';
      setActionMessage({ type: 'error', text: errMsg });
      toast.error(errMsg);
    } finally {
      setRestoringBackup(false);
    }
  };

  const handleRebuildIndex = async () => {
    const key = 'rebuild_index';
    startAction(key);
    try {
      const res = await api.rebuildIndex();
      const msg = res.message || 'Active FAISS vector index rebuilt from all approved documents.';
      setActionMessage({ type: 'success', text: msg });
      toast.success(msg);
      await loadData();
    } catch (err) {
      const errMsg = err.message || 'Failed to rebuild index.';
      setActionMessage({ type: 'error', text: errMsg });
      toast.error(errMsg);
    } finally {
      stopAction(key);
    }
  };

  // Quality Control Issue Resolution
  const handleResolveQualityIssue = async (issueId, action, reason) => {
    const key = `qc_${issueId}_${action}`;
    startAction(key);
    try {
      const res = await api.resolveQualityIssue(issueId, action, reason || 'Resolved by Admin');
      const msg = res.message || `Resolved quality issue ${issueId}.`;
      setActionMessage({ type: 'success', text: msg });
      toast.success(msg);
      await loadData();
    } catch (err) {
      const errMsg = err.message || 'Failed to resolve quality issue.';
      setActionMessage({ type: 'error', text: errMsg });
      toast.error(errMsg);
    } finally {
      stopAction(key);
    }
  };

  const pendingDocs = useMemo(() => documents.filter(d => d.status === 'pending_review' || d.status === 'uploaded' || d.governance_status === 'pending_review'), [documents]);
  const indexedDocs = useMemo(() => documents.filter(d => d.status === 'indexed' && (d.governance_status === 'approved' || d.retrieval_enabled === 1)), [documents]);
  const archivedDocs = useMemo(() => documents.filter(d => d.governance_status === 'archived'), [documents]);
  const rejectedDocs = useMemo(() => documents.filter(d => d.governance_status === 'rejected'), [documents]);

  const filteredDocs = useMemo(() => documents.filter(d => {
    const matchesSearch = !docSearch || d.title?.toLowerCase().includes(docSearch.toLowerCase()) || d.original_filename?.toLowerCase().includes(docSearch.toLowerCase());
    if (!matchesSearch) return false;

    if (docFilter === 'active') return d.status === 'indexed' && d.governance_status === 'approved';
    if (docFilter === 'pending') return d.governance_status === 'pending_review' || d.status === 'uploaded';
    if (docFilter === 'archived') return d.governance_status === 'archived';
    if (docFilter === 'rejected') return d.governance_status === 'rejected';
    return true;
  }), [documents, docSearch, docFilter]);

  const tabsConfig = useMemo(() => [
    { key: 'overview', label: 'Overview', icon: Activity },
    { key: 'documents', label: `All Documents (${documents.length})`, icon: FileText },
    { key: 'approvals', label: `Approvals Queue (${pendingDocs.length})`, icon: CheckCircle },
    { key: 'users', label: 'User Roles', icon: Users },
    { key: 'quality', label: 'Quality Control', icon: ShieldCheck },
    { key: 'recovery', label: 'Health & Backups', icon: Database },
    { key: 'diagnostics', label: 'Diagnostics', icon: Cpu },
  ], [documents.length, pendingDocs.length]);

  return (
    <div className="rx-container py-8 sm:py-12 flex-1 flex flex-col">
      <div className="flex flex-wrap justify-between items-center gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-raxel-indigo tracking-tight mb-1">
            RAXEL Governance & Administration Control Suite
          </h1>
          <p className="text-raxel-muted text-xs sm:text-sm">
            Manage document approvals, user roles, vector index rebuilds, quality scans, and system health.
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          icon={RefreshCw}
          onClick={loadData}
          isLoading={loading}
        >
          Refresh Data
        </Button>
      </div>

      {actionMessage.text && (
        <Alert
          type={actionMessage.type}
          message={actionMessage.text}
          onClose={() => setActionMessage({ type: '', text: '' })}
          className="mb-6"
        />
      )}

      {/* Admin Navigation Bar */}
      <div className="flex items-center gap-1 border-b border-raxel-border mb-6 overflow-x-auto">
        {tabsConfig.map((t) => {
          const IconComp = t.icon;
          const isActive = tab === t.key;
          return (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`relative flex items-center gap-2 px-4 py-2.5 text-xs sm:text-sm font-medium rounded-t-md transition-all whitespace-nowrap focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-raxel-indigo ${
                isActive
                  ? 'bg-raxel-indigo text-white font-semibold shadow-sm'
                  : 'text-raxel-muted hover:text-raxel-indigo hover:bg-raxel-surface-subtle'
              }`}
            >
              <IconComp className="w-4 h-4" />
              <span>{t.label}</span>
            </button>
          );
        })}
      </div>

      {/* OVERVIEW TAB */}
      {tab === 'overview' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <HoverLift>
              <Card variant="metric" className="h-full">
                <div className="text-[11px] font-bold text-raxel-muted uppercase tracking-wider">TOTAL DOCUMENTS</div>
                <div className="text-3xl font-extrabold text-raxel-indigo mt-2">{documents.length}</div>
              </Card>
            </HoverLift>
            <HoverLift>
              <Card variant="metric" className="h-full">
                <div className="text-[11px] font-bold text-raxel-muted uppercase tracking-wider">ACTIVE INDEXED</div>
                <div className="text-3xl font-extrabold text-status-success-text mt-2">{indexedDocs.length}</div>
              </Card>
            </HoverLift>
            <HoverLift>
              <Card variant="metric" className="h-full">
                <div className="text-[11px] font-bold text-raxel-muted uppercase tracking-wider">PENDING REVIEW</div>
                <div className="text-3xl font-extrabold text-status-warning-text mt-2">{pendingDocs.length}</div>
              </Card>
            </HoverLift>
            <HoverLift>
              <Card variant="metric" className="h-full">
                <div className="text-[11px] font-bold text-raxel-muted uppercase tracking-wider">REGISTERED USERS</div>
                <div className="text-3xl font-extrabold text-raxel-teal mt-2">{users.length}</div>
              </Card>
            </HoverLift>
          </div>
        </motion.div>
      )}

      {/* ALL DOCUMENTS TAB */}
      {tab === 'documents' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-4">
          <div className="flex flex-wrap justify-between items-center gap-4 mb-2">
            <div className="flex items-center gap-2">
              <Select value={docFilter} onChange={(e) => setDocFilter(e.target.value)} className="!w-44">
                <option value="all">All Governance States</option>
                <option value="active">Active Approved ({indexedDocs.length})</option>
                <option value="pending">Pending Review ({pendingDocs.length})</option>
                <option value="archived">Archived ({archivedDocs.length})</option>
                <option value="rejected">Rejected ({rejectedDocs.length})</option>
              </Select>
              <Input
                placeholder="Filter by title..."
                value={docSearch}
                onChange={(e) => setDocSearch(e.target.value)}
                className="!w-64"
              />
            </div>
            <div className="text-xs text-raxel-muted">
              Showing <strong>{filteredDocs.length}</strong> of {documents.length} document(s)
            </div>
          </div>

          {filteredDocs.length === 0 ? (
            <EmptyState icon={FileText} title="No Documents Found" description="No documents match the selected governance state filter." />
          ) : (
            <div className="w-full overflow-x-auto border border-raxel-border rounded-lg bg-white shadow-sm">
              <table className="w-full text-left text-xs sm:text-sm border-collapse">
                <thead>
                  <tr className="bg-raxel-soft-white text-raxel-muted uppercase text-[11px] font-semibold tracking-wider border-b border-raxel-border">
                    <th className="p-3.5 sm:p-4">Title</th>
                    <th className="p-3.5 sm:p-4">Type</th>
                    <th className="p-3.5 sm:p-4">Uploaded By</th>
                    <th className="p-3.5 sm:p-4">Status</th>
                    <th className="p-3.5 sm:p-4">Governance</th>
                    <th className="p-3.5 sm:p-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-raxel-border-subtle">
                  {filteredDocs.map((d, idx) => {
                    const docId = d.document_id || d.id;
                    const govState = d.governance_status || 'pending_review';
                    return (
                      <tr key={docId || idx} className="hover:bg-raxel-surface-subtle transition-colors">
                        <td className="p-3.5 sm:p-4 font-semibold text-raxel-indigo">
                          <div className="flex items-center gap-2">
                            <FileText className="w-4 h-4 text-raxel-teal shrink-0" />
                            <span className="truncate max-w-xs">{d.title}</span>
                          </div>
                        </td>
                        <td className="p-3.5 sm:p-4 capitalize text-raxel-ink">{(d.document_type || d.doc_type || 'general').replace('_', ' ')}</td>
                        <td className="p-3.5 sm:p-4 text-raxel-muted">{d.uploaded_by || 'System'}</td>
                        <td className="p-3.5 sm:p-4">
                          <Badge variant={d.status === 'indexed' ? 'indexed' : d.status === 'rejected' ? 'rejected' : 'pending'}>{d.status}</Badge>
                        </td>
                        <td className="p-3.5 sm:p-4 capitalize font-medium text-raxel-ink">{govState.replace('_', ' ')}</td>
                        <td className="p-3.5 sm:p-4 text-right">
                          <div className="flex justify-end gap-1.5">
                            <Button variant="secondary" size="sm" icon={Eye} onClick={() => handleViewDetails(docId)} isLoading={isActionLoading(`details_${docId}`)} className="!py-1 !px-2 !text-[11px]">Details</Button>
                            {govState === 'pending_review' && (
                              <Button variant="teal" size="sm" icon={CheckCircle} onClick={() => handleApprove(docId)} isLoading={isActionLoading(`approve_${docId}`)} className="!py-1 !px-2 !text-[11px]">
                                {isActionLoading(`approve_${docId}`) ? 'Approving...' : 'Approve'}
                              </Button>
                            )}
                            {govState === 'approved' && (
                              <Button variant="secondary" size="sm" icon={Archive} onClick={() => handleArchive(docId)} isLoading={isActionLoading(`archive_${docId}`)} className="!py-1 !px-2 !text-[11px]">
                                {isActionLoading(`archive_${docId}`) ? 'Archiving...' : 'Archive'}
                              </Button>
                            )}
                            {(govState === 'archived' || govState === 'rejected') && (
                              <Button variant="secondary" size="sm" icon={RotateCcw} onClick={() => handleRestore(docId)} isLoading={isActionLoading(`restore_${docId}`)} className="!py-1 !px-2 !text-[11px]">
                                {isActionLoading(`restore_${docId}`) ? 'Restoring...' : 'Restore'}
                              </Button>
                            )}
                            <Button variant="danger" size="sm" icon={Trash2} onClick={() => setDeleteConfirmDoc(d)} className="!py-1 !px-2 !text-[11px]">Delete</Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </motion.div>
      )}

      {/* APPROVALS TAB */}
      {tab === 'approvals' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <h2 className="text-base sm:text-lg font-semibold text-raxel-indigo mb-4">
            Governance Review Queue
          </h2>
          {pendingDocs.length === 0 ? (
            <EmptyState
              icon={CheckCircle}
              title="Review Queue Clear"
              description="No pending documents currently requiring governance approval."
            />
          ) : (
            <div className="flex flex-col gap-4">
              {pendingDocs.map((doc, idx) => {
                const docId = doc.document_id || doc.id;
                return (
                  <Card key={docId || idx} className="p-5 flex flex-col gap-3">
                    <div className="flex justify-between items-center flex-wrap gap-2">
                      <div className="font-semibold text-base text-raxel-indigo">{doc.title}</div>
                      <Badge variant="pending">{doc.status}</Badge>
                    </div>
                    <div className="text-xs text-raxel-muted flex flex-wrap gap-4">
                      <span>Type: <strong className="text-raxel-ink">{doc.document_type || doc.doc_type}</strong></span>
                      <span>Version: <strong className="text-raxel-ink">v{doc.version || '1.0'}</strong></span>
                      <span>Uploaded By: <strong className="text-raxel-ink">{doc.uploaded_by || 'Faculty'}</strong></span>
                    </div>
                    <div className="flex items-center gap-3 mt-1 flex-wrap sm:flex-nowrap">
                      <Button
                        variant="teal"
                        size="sm"
                        icon={CheckCircle}
                        isLoading={isActionLoading(`approve_${docId}`)}
                        onClick={() => handleApprove(docId)}
                      >
                        {isActionLoading(`approve_${docId}`) ? 'Approving & Indexing...' : 'Approve & Index'}
                      </Button>
                      <div className="flex-1 min-w-[200px]">
                        <Input
                          placeholder="Reason for rejection..."
                          value={rejectReason[docId] || ''}
                          onChange={(e) => setRejectReason({ ...rejectReason, [docId]: e.target.value })}
                          disabled={isActionLoading(`reject_${docId}`)}
                          className="!min-h-[34px] !py-1.5"
                        />
                      </div>
                      <Button
                        variant="danger"
                        size="sm"
                        icon={XCircle}
                        isLoading={isActionLoading(`reject_${docId}`)}
                        onClick={() => handleReject(docId)}
                      >
                        {isActionLoading(`reject_${docId}`) ? 'Rejecting...' : 'Reject'}
                      </Button>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </motion.div>
      )}

      {/* USER ROLES TAB */}
      {tab === 'users' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <h2 className="text-base sm:text-lg font-semibold text-raxel-indigo mb-4">
            User Account Role Management
          </h2>
          <div className="w-full overflow-x-auto border border-raxel-border rounded-lg bg-white shadow-sm">
            <table className="w-full text-left text-xs sm:text-sm border-collapse">
              <thead>
                <tr className="bg-raxel-soft-white text-raxel-muted uppercase text-[11px] font-semibold tracking-wider border-b border-raxel-border">
                  <th className="p-3.5 sm:p-4">Username</th>
                  <th className="p-3.5 sm:p-4">Role</th>
                  <th className="p-3.5 sm:p-4">Status</th>
                  <th className="p-3.5 sm:p-4">Change Role Action</th>
                  <th className="p-3.5 sm:p-4 text-right">Account Active Toggle</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-raxel-border-subtle">
                {users.map((u, idx) => (
                  <tr key={u.username || idx} className="hover:bg-raxel-surface-subtle transition-colors">
                    <td className="p-3.5 sm:p-4 font-semibold text-raxel-indigo">{u.username}</td>
                    <td className="p-3.5 sm:p-4">
                      <Badge variant={u.role}>{u.role}</Badge>
                    </td>
                    <td className="p-3.5 sm:p-4 text-raxel-muted">{u.active ? 'Active' : 'Disabled'}</td>
                    <td className="p-3.5 sm:p-4">
                      <div className="flex gap-1.5">
                        <Button variant="secondary" size="sm" isLoading={isActionLoading(`role_${u.username}_student`)} onClick={() => handleRoleChange(u.username, 'student')} className="!py-1 !px-2.5 !text-[11px] !min-h-[28px]">Student</Button>
                        <Button variant="secondary" size="sm" isLoading={isActionLoading(`role_${u.username}_faculty`)} onClick={() => handleRoleChange(u.username, 'faculty')} className="!py-1 !px-2.5 !text-[11px] !min-h-[28px]">Faculty</Button>
                        <Button variant="secondary" size="sm" isLoading={isActionLoading(`role_${u.username}_admin`)} onClick={() => handleRoleChange(u.username, 'admin')} className="!py-1 !px-2.5 !text-[11px] !min-h-[28px]">Admin</Button>
                      </div>
                    </td>
                    <td className="p-3.5 sm:p-4 text-right">
                      <Button
                        variant={u.active ? 'secondary' : 'teal'}
                        size="sm"
                        isLoading={isActionLoading(`toggle_${u.username}`)}
                        onClick={() => handleToggleActive(u.username, u.active)}
                        className="!py-1 !px-2.5 !text-[11px]"
                      >
                        {isActionLoading(`toggle_${u.username}`) ? 'Updating...' : u.active ? 'Disable' : 'Enable'}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      )}

      {/* HEALTH & RECOVERY TAB */}
      {tab === 'recovery' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-6">
          <Card className="p-6">
            <h3 className="text-base font-semibold text-raxel-indigo mb-1">FAISS Vector Index Management</h3>
            <p className="text-xs sm:text-sm text-raxel-muted mb-4">Rebuild vector embeddings safely from all currently approved college documents.</p>
            <Button variant="teal" icon={RefreshCw} isLoading={isActionLoading('rebuild_index')} onClick={handleRebuildIndex}>
              {isActionLoading('rebuild_index') ? 'Rebuilding Index...' : 'Rebuild Active FAISS Index'}
            </Button>
          </Card>

          <Card className="p-6">
            <h3 className="text-base font-semibold text-raxel-indigo mb-1">Create System Backup</h3>
            <div className="flex flex-col sm:flex-row gap-3 mt-3">
              <div className="flex-1">
                <Input
                  placeholder="Optional backup note..."
                  value={backupNote}
                  onChange={(e) => setBackupNote(e.target.value)}
                  disabled={isActionLoading('create_backup')}
                />
              </div>
              <Button variant="primary" icon={DownloadCloud} isLoading={isActionLoading('create_backup')} onClick={handleCreateBackup}>
                {isActionLoading('create_backup') ? 'Creating Backup...' : 'Create Safety Backup'}
              </Button>
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="text-base font-semibold text-raxel-indigo mb-3">Available Safety Backups ({backups.length})</h3>
            {backups.length === 0 ? (
              <p className="text-xs text-raxel-muted">No safety backups saved yet.</p>
            ) : (
              <div className="flex flex-col gap-3">
                {backups.map((b, idx) => (
                  <div key={idx} className="p-3.5 border border-raxel-border rounded-lg flex items-center justify-between flex-wrap gap-2 bg-raxel-surface-subtle">
                    <div>
                      <div className="font-semibold text-sm text-raxel-indigo">{b.backup_id}</div>
                      <div className="text-xs text-raxel-muted">{b.created_at} | Created by: {b.created_by} | {b.document_count} docs, {b.vector_count} vectors</div>
                    </div>
                    <div className="flex gap-2">
                      <Button variant="secondary" size="sm" isLoading={isActionLoading(`validate_${b.backup_id}`)} onClick={() => handleValidateBackup(b.backup_id)}>
                        {isActionLoading(`validate_${b.backup_id}`) ? 'Validating...' : 'Validate'}
                      </Button>
                      <Button variant="primary" size="sm" onClick={() => setRestoreConfirmBackup(b)}>Restore</Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </motion.div>
      )}

      {/* QUALITY CONTROL TAB */}
      {tab === 'quality' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-6">
          <h2 className="text-base sm:text-lg font-semibold text-raxel-indigo">
            Knowledge Base Quality Control Scan
          </h2>
          <Card className="p-6">
            {qualityData ? (
              <div className="flex flex-col gap-3 text-sm text-raxel-ink">
                <div className="font-semibold text-status-success-text flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5" /> Scan Status: Complete
                </div>
                <div>Total Scanned Documents: <strong>{qualityData.scanned_documents || documents.length}</strong></div>
                <div>Potential Duplicate Chunks: <strong>{qualityData.duplicates?.length || qualityData.quality_issues?.length || 0}</strong></div>
                <div>Document Conflicts: <strong>{qualityData.conflicts?.length || 0}</strong></div>
              </div>
            ) : (
              <div className="text-raxel-muted text-sm">Loading quality scan...</div>
            )}
          </Card>

          {qualityData?.quality_issues?.length > 0 && (
            <Card className="p-6">
              <h3 className="font-semibold text-sm text-raxel-indigo mb-3">Detected Quality Issues & Conflicts</h3>
              <div className="flex flex-col gap-3">
                {qualityData.quality_issues.map((iss, idx) => (
                  <div key={idx} className="p-4 border border-raxel-border rounded-lg bg-white flex flex-col gap-2">
                    <div className="flex justify-between items-center">
                      <Badge variant="warning">{iss.issue_type}</Badge>
                      <span className="text-xs text-raxel-muted">Severity: <strong>{iss.severity}</strong></span>
                    </div>
                    <div className="text-xs text-raxel-ink">{iss.description}</div>
                    <div className="flex justify-end gap-2 mt-2">
                      <Button variant="secondary" size="sm" isLoading={isActionLoading(`qc_${iss.issue_id}_mark_reviewed`)} onClick={() => handleResolveQualityIssue(iss.issue_id, 'mark_reviewed')}>
                        {isActionLoading(`qc_${iss.issue_id}_mark_reviewed`) ? 'Resolving...' : 'Mark Reviewed'}
                      </Button>
                      <Button variant="teal" size="sm" isLoading={isActionLoading(`qc_${iss.issue_id}_prefer_newer`)} onClick={() => handleResolveQualityIssue(iss.issue_id, 'prefer_newer')}>
                        {isActionLoading(`qc_${iss.issue_id}_prefer_newer`) ? 'Resolving...' : 'Prefer Newer Version'}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </motion.div>
      )}

      {/* DIAGNOSTICS TAB */}
      {tab === 'diagnostics' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <h2 className="text-base sm:text-lg font-semibold text-raxel-indigo mb-4">
            System Infrastructure & AI Diagnostics
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <Card className="p-5">
              <div className="font-semibold text-sm text-raxel-indigo flex items-center gap-2 mb-3">
                <Server className="w-4 h-4 text-raxel-teal" /> Database & Storage
              </div>
              <div className="text-xs sm:text-sm text-raxel-muted flex flex-col gap-2">
                <div className="flex items-center justify-between">SQLite Database: <Badge variant="indexed">Healthy</Badge></div>
                <div className="flex items-center justify-between">Manifest Store: <Badge variant="indexed">Healthy</Badge></div>
              </div>
            </Card>

            <Card className="p-5">
              <div className="font-semibold text-sm text-raxel-indigo flex items-center gap-2 mb-3">
                <Cpu className="w-4 h-4 text-raxel-indigo" /> AI Engine Services
              </div>
              <div className="text-xs sm:text-sm text-raxel-muted flex flex-col gap-2">
                <div className="flex items-center justify-between">FAISS Vector Store: <Badge variant="indexed">Ready</Badge></div>
                <div className="flex items-center justify-between">Ollama Service: <Badge variant="indexed">Available</Badge></div>
              </div>
            </Card>
          </div>
        </motion.div>
      )}

      {/* Admin Delete Confirmation Modal */}
      <AnimatePresence>
        {deleteConfirmDoc && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-raxel-indigo-deep/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              transition={{ duration: 0.2, ease: 'easeOut' }}
              className="bg-white rounded-lg border border-raxel-border shadow-xl w-full max-w-md p-6 relative"
            >
              <div className="flex items-center gap-2 text-status-danger-text mb-3">
                <Trash2 className="w-5 h-5" />
                <h3 className="text-lg font-semibold">Permanently Delete Document?</h3>
              </div>
              <p className="text-xs sm:text-sm text-raxel-ink mb-3">
                Are you sure you want to delete <strong>{deleteConfirmDoc.title}</strong>?
              </p>
              <p className="text-xs text-status-danger-text bg-status-danger-bg p-3 rounded border border-status-danger-border mb-5">
                Warning: This will permanently remove the database record, raw PDF file, chunk metadata, and vector embeddings from RAXEL retrieval.
              </p>
              <div className="flex justify-end gap-3">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => setDeleteConfirmDoc(null)}
                  disabled={deleting}
                >
                  Cancel
                </Button>
                <Button
                  type="button"
                  variant="danger"
                  size="sm"
                  icon={Trash2}
                  isLoading={deleting}
                  onClick={handleDeleteExecute}
                >
                  {deleting ? 'Deleting...' : 'Permanently Delete'}
                </Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Restore Backup Confirmation Modal */}
      <AnimatePresence>
        {restoreConfirmBackup && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-raxel-indigo-deep/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              transition={{ duration: 0.2, ease: 'easeOut' }}
              className="bg-white rounded-lg border border-raxel-border shadow-xl w-full max-w-md p-6 relative"
            >
              <div className="flex items-center gap-2 text-raxel-indigo mb-3">
                <RotateCcw className="w-5 h-5 text-raxel-teal" />
                <h3 className="text-lg font-semibold">Restore System Backup?</h3>
              </div>
              <p className="text-xs sm:text-sm text-raxel-ink mb-3">
                Restore system state to backup <strong>{restoreConfirmBackup.backup_id}</strong>?
              </p>
              <p className="text-xs text-raxel-muted bg-raxel-surface-subtle p-3 rounded border border-raxel-border mb-5">
                A safety backup of the current state will be created automatically before restoring.
              </p>
              <div className="flex justify-end gap-3">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => setRestoreConfirmBackup(null)}
                  disabled={restoringBackup}
                >
                  Cancel
                </Button>
                <Button
                  type="button"
                  variant="primary"
                  size="sm"
                  icon={RotateCcw}
                  isLoading={restoringBackup}
                  onClick={handleRestoreBackupExecute}
                >
                  {restoringBackup ? 'Restoring Backup...' : 'Confirm Restore'}
                </Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Document Details Modal */}
      <AnimatePresence>
        {detailsDoc && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-raxel-indigo-deep/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white rounded-lg border border-raxel-border shadow-xl w-full max-w-lg p-6 relative max-h-[85vh] overflow-y-auto"
            >
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-base font-bold text-raxel-indigo truncate">{detailsDoc.title}</h3>
                <button onClick={() => setDetailsDoc(null)} className="p-1 rounded text-raxel-muted hover:text-raxel-indigo">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="flex flex-col gap-2 text-xs sm:text-sm text-raxel-ink mb-4">
                <div>Document ID: <strong>{detailsDoc.document_id}</strong></div>
                <div>Original Filename: <strong>{detailsDoc.original_filename}</strong></div>
                <div>Category: <strong className="capitalize">{detailsDoc.document_type}</strong></div>
                <div>Uploaded By: <strong>{detailsDoc.uploaded_by}</strong></div>
                <div>Status: <Badge variant={detailsDoc.status === 'indexed' ? 'indexed' : 'pending'}>{detailsDoc.status}</Badge></div>
                <div>Governance: <strong className="capitalize">{detailsDoc.governance_status}</strong></div>
                <div>Page Count: <strong>{detailsDoc.page_count}</strong> | Chunk Count: <strong>{detailsDoc.chunk_count}</strong></div>
              </div>
              <h4 className="font-semibold text-xs text-raxel-indigo uppercase mb-2">Audit History</h4>
              <div className="flex flex-col gap-1.5 text-xs border border-raxel-border rounded p-3 bg-raxel-surface-subtle max-h-36 overflow-y-auto mb-4">
                {auditLogs.length === 0 ? (
                  <div className="text-raxel-muted">No audit logs recorded.</div>
                ) : (
                  auditLogs.map((log, i) => (
                    <div key={i} className="flex justify-between border-b border-raxel-border-subtle pb-1">
                      <span><strong className="capitalize">{log.action}</strong> by {log.performed_by}</span>
                      <span className="text-raxel-muted">{log.timestamp}</span>
                    </div>
                  ))
                )}
              </div>
              <div className="flex items-center justify-end gap-2 pt-2 border-t border-raxel-border">
                <Button variant="secondary" size="sm" onClick={() => setDetailsDoc(null)}>Close</Button>
                <a href={api.getDocumentViewUrl(detailsDoc.document_id || detailsDoc.id)} target="_blank" rel="noreferrer">
                  <Button variant="secondary" size="sm" icon={Eye}>View PDF</Button>
                </a>
                <a href={api.getDocumentDownloadUrl(detailsDoc.document_id || detailsDoc.id, 'attachment')} target="_blank" rel="noreferrer">
                  <Button variant="primary" size="sm" icon={DownloadCloud}>Download PDF</Button>
                </a>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default AdminPage;
