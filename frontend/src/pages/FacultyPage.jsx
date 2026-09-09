import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { UploadCloud, FileText, CheckCircle2, AlertCircle, Plus, X, Trash2, Eye, Download } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Input, Select, Textarea } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { Card } from '../components/ui/Card';
import { Alert } from '../components/ui/Alert';
import { TableSkeleton } from '../components/ui/Skeleton';
import { EmptyState } from '../components/ui/EmptyState';
import { HoverLift } from '../components/motion/MotionComponents';

import { useToast } from '../context/ToastContext';

export const FacultyPage = ({ isUploadModalOpenDefault = false }) => {
  const { user } = useAuth();
  const toast = useToast();
  const [documents, setDocuments] = useState([]);
  const [suggestedTypes, setSuggestedTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(isUploadModalOpenDefault);
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteConfirmDoc, setDeleteConfirmDoc] = useState(null);
  const [message, setMessage] = useState({ type: '', text: '' });

  // Upload Form Fields
  const [file, setFile] = useState(null);
  const [title, setTitle] = useState('');
  const [docType, setDocType] = useState('academic_regulations');
  const [academicYear, setAcademicYear] = useState('2024-2025');
  const [version, setVersion] = useState('1.0');
  const [effectiveDate, setEffectiveDate] = useState('');
  const [description, setDescription] = useState('');

  const abortControllerRef = useRef(null);

  const fetchDocs = useCallback(async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      setLoading(true);
      const data = await api.listDocuments(undefined, undefined, { signal: controller.signal });
      setDocuments(data.documents || []);
    } catch (err) {
      if (err.name !== 'AbortError') {
        console.error(err);
      }
    } finally {
      if (abortControllerRef.current === controller) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    fetchDocs();
    api.getSuggestedDocTypes().then(res => setSuggestedTypes(res.doc_types || [])).catch(() => { });
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchDocs]);

  const handleUploadSubmit = async (e) => {
    e.preventDefault();
    if (!file || !title.trim()) {
      setMessage({ type: 'error', text: 'Please choose a PDF file and enter a document title.' });
      toast.error('Please choose a PDF file and enter a title.');
      return;
    }

    setUploading(true);
    setMessage({ type: '', text: '' });

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('title', title.trim());
      formData.append('doc_type', docType);
      formData.append('academic_year', academicYear);
      formData.append('version', version);
      if (effectiveDate) formData.append('effective_date', effectiveDate);
      if (description) formData.append('description', description);

      const res = await api.uploadDocument(formData);
      const succMsg = res.message || 'Document uploaded successfully and queued for Admin governance review.';
      setMessage({ type: 'success', text: succMsg });
      toast.success(succMsg);

      setFile(null);
      setTitle('');
      setDescription('');
      setShowModal(false);
      fetchDocs();
    } catch (err) {
      const errMsg = err.message || 'Failed to upload document.';
      setMessage({ type: 'error', text: errMsg });
      toast.error(errMsg);
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteExecute = async () => {
    if (!deleteConfirmDoc) return;
    const docId = deleteConfirmDoc.document_id || deleteConfirmDoc.id;
    setDeleting(true);
    try {
      const res = await api.deleteDocument(docId);
      const succMsg = res.message || 'Document permanently deleted.';
      setMessage({ type: 'success', text: succMsg });
      toast.success(succMsg);
      setDeleteConfirmDoc(null);
      fetchDocs();
    } catch (err) {
      const errMsg = err.message || 'Failed to delete document.';
      setMessage({ type: 'error', text: errMsg });
      toast.error(errMsg);
    } finally {
      setDeleting(false);
    }
  };

  const totalDocs = useMemo(() => documents.length, [documents.length]);
  const pendingDocs = useMemo(() => documents.filter(d => d.status === 'pending_review' || d.status === 'uploaded' || d.status === 'processing').length, [documents]);
  const indexedDocs = useMemo(() => documents.filter(d => d.status === 'indexed').length, [documents]);
  const rejectedDocs = useMemo(() => documents.filter(d => d.status === 'rejected').length, [documents]);

  return (
    <div className="rx-container py-8 sm:py-12 flex-1 flex flex-col">
      <div className="flex flex-wrap justify-between items-center gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-raxel-indigo tracking-tight mb-1">
            Faculty Document Workspace
          </h1>
          <p className="text-raxel-muted text-xs sm:text-sm">
            Submit regulation PDFs, course handbooks, and syllabi for Admin governance indexing.
          </p>
        </div>
        <Button
          variant="primary"
          icon={Plus}
          onClick={() => setShowModal(true)}
        >
          Upload PDF Document
        </Button>
      </div>

      {message.text && (
        <Alert
          type={message.type}
          message={message.text}
          onClose={() => setMessage({ type: '', text: '' })}
          className="mb-6"
        />
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <HoverLift>
          <Card variant="metric" className="flex flex-col justify-between h-full">
            <div className="text-[11px] font-bold text-raxel-muted uppercase tracking-wider">TOTAL SUBMISSIONS</div>
            <div className="text-3xl font-extrabold text-raxel-indigo mt-2">{totalDocs}</div>
          </Card>
        </HoverLift>
        <HoverLift>
          <Card variant="metric" className="flex flex-col justify-between h-full">
            <div className="text-[11px] font-bold text-raxel-muted uppercase tracking-wider">INDEXED & ACTIVE</div>
            <div className="text-3xl font-extrabold text-status-success-text mt-2">{indexedDocs}</div>
          </Card>
        </HoverLift>
        <HoverLift>
          <Card variant="metric" className="flex flex-col justify-between h-full">
            <div className="text-[11px] font-bold text-raxel-muted uppercase tracking-wider">PENDING REVIEW</div>
            <div className="text-3xl font-extrabold text-status-warning-text mt-2">{pendingDocs}</div>
          </Card>
        </HoverLift>
        <HoverLift>
          <Card variant="metric" className="flex flex-col justify-between h-full">
            <div className="text-[11px] font-bold text-raxel-muted uppercase tracking-wider">REJECTED</div>
            <div className="text-3xl font-extrabold text-status-danger-text mt-2">{rejectedDocs}</div>
          </Card>
        </HoverLift>
      </div>

      {/* Documents Table */}
      {loading ? (
        <TableSkeleton rows={4} cols={6} />
      ) : documents.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No Document Submissions"
          description="No documents submitted yet. Click 'Upload PDF Document' to submit a regulation or handbook."
          action={
            <Button variant="primary" icon={Plus} onClick={() => setShowModal(true)}>
              Upload PDF Document
            </Button>
          }
        />
      ) : (
        <div className="w-full overflow-x-auto border border-raxel-border rounded-lg bg-white shadow-sm">
          <table className="w-full text-left text-xs sm:text-sm border-collapse">
            <thead>
              <tr className="bg-raxel-soft-white text-raxel-muted uppercase text-[11px] font-semibold tracking-wider border-b border-raxel-border">
                <th className="p-3.5 sm:p-4">Document Title</th>
                <th className="p-3.5 sm:p-4">Category / Type</th>
                <th className="p-3.5 sm:p-4">Version</th>
                <th className="p-3.5 sm:p-4">Governance Status</th>
                <th className="p-3.5 sm:p-4">Submission Date</th>
                <th className="p-3.5 sm:p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-raxel-border-subtle">
              {documents.map((doc, idx) => {
                const isOwner = !doc.uploaded_by || doc.uploaded_by.toLowerCase() === (user?.username || '').toLowerCase() || user?.role === 'admin';
                const docId = doc.document_id || doc.id;
                return (
                  <tr key={docId || idx} className="hover:bg-raxel-surface-subtle transition-colors">
                    <td className="p-3.5 sm:p-4 font-semibold text-raxel-indigo">
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-raxel-teal shrink-0" />
                        <span className="truncate max-w-xs sm:max-w-md">{doc.title}</span>
                      </div>
                    </td>
                    <td className="p-3.5 sm:p-4 capitalize text-raxel-ink">
                      {doc.doc_type ? doc.doc_type.replace('_', ' ') : 'General'}
                    </td>
                    <td className="p-3.5 sm:p-4 text-raxel-muted">v{doc.version || '1.0'}</td>
                    <td className="p-3.5 sm:p-4">
                      <Badge variant={doc.status === 'indexed' ? 'indexed' : doc.status === 'rejected' ? 'rejected' : 'pending'}>
                        {doc.status || 'uploaded'}
                      </Badge>
                    </td>
                    <td className="p-3.5 sm:p-4 text-raxel-muted text-xs">
                      {doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString() : 'Recent'}
                    </td>
                    <td className="p-3.5 sm:p-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <a
                          href={api.getDocumentViewUrl(docId)}
                          target="_blank"
                          rel="noreferrer"
                          className="p-1.5 rounded text-raxel-muted hover:text-raxel-indigo hover:bg-raxel-violet-soft transition-colors"
                          title="View PDF in Browser"
                        >
                          <Eye className="w-4 h-4" />
                        </a>
                        <a
                          href={api.getDocumentDownloadUrl(docId, 'attachment')}
                          target="_blank"
                          rel="noreferrer"
                          className="p-1.5 rounded text-raxel-muted hover:text-raxel-teal hover:bg-teal-50 transition-colors"
                          title="Download PDF"
                        >
                          <Download className="w-4 h-4" />
                        </a>
                        {isOwner && (
                          <Button
                            variant="danger"
                            size="sm"
                            icon={Trash2}
                            onClick={() => setDeleteConfirmDoc(doc)}
                            className="!py-1 !px-2.5 !text-xs ml-1"
                          >
                            Delete
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Faculty Delete Confirmation Modal */}
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
                <h3 className="text-lg font-semibold">Delete Your Document?</h3>
              </div>
              <p className="text-xs sm:text-sm text-raxel-ink mb-3">
                Are you sure you want to permanently delete <strong>{deleteConfirmDoc.title}</strong>?
              </p>
              <p className="text-xs text-status-danger-text bg-status-danger-bg p-3 rounded border border-status-danger-border mb-5">
                Warning: This will remove the document and its associated knowledge from RAXEL retrieval.
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
                  {deleting ? 'Deleting Document...' : 'Delete Document'}
                </Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Upload Modal with Motion */}
      <AnimatePresence>
        {showModal && (
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
              className="bg-white rounded-lg border border-raxel-border shadow-xl w-full max-w-lg p-6 relative"
            >
              <div className="flex justify-between items-center mb-5">
                <div className="flex items-center gap-2">
                  <UploadCloud className="w-5 h-5 text-raxel-indigo" />
                  <h2 className="text-lg font-semibold text-raxel-indigo">Submit Knowledge Document</h2>
                </div>
                <button
                  onClick={() => setShowModal(false)}
                  disabled={uploading}
                  className="p-1 rounded text-raxel-muted hover:text-raxel-indigo hover:bg-raxel-surface-subtle transition-colors disabled:opacity-50"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleUploadSubmit} className="flex flex-col gap-4">
                <Input
                  label="Document PDF File"
                  type="file"
                  accept=".pdf"
                  onChange={(e) => setFile(e.target.files[0])}
                  disabled={uploading}
                  required
                />

                <Input
                  label="Document Title"
                  placeholder="e.g. B.Tech Academic Regulations 2025"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  disabled={uploading}
                  required
                />

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Select
                    label="Document Type"
                    value={docType}
                    onChange={(e) => setDocType(e.target.value)}
                    disabled={uploading}
                  >
                    {suggestedTypes.map((t, idx) => (
                      <option key={idx} value={t}>{t.replace('_', ' ')}</option>
                    ))}
                  </Select>

                  <Input
                    label="Academic Year"
                    value={academicYear}
                    onChange={(e) => setAcademicYear(e.target.value)}
                    disabled={uploading}
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Input
                    label="Version"
                    value={version}
                    onChange={(e) => setVersion(e.target.value)}
                    disabled={uploading}
                  />

                  <Input
                    label="Effective Date (Optional)"
                    type="date"
                    value={effectiveDate}
                    onChange={(e) => setEffectiveDate(e.target.value)}
                    disabled={uploading}
                  />
                </div>

                <Textarea
                  label="Description (Optional)"
                  placeholder="Brief summary of document regulations..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  disabled={uploading}
                  rows={2}
                />

                <div className="flex justify-end gap-3 mt-3">
                  <Button type="button" variant="secondary" onClick={() => setShowModal(false)} disabled={uploading}>
                    Cancel
                  </Button>
                  <Button type="submit" variant="primary" isLoading={uploading}>
                    {uploading ? 'Uploading PDF...' : 'Upload & Submit'}
                  </Button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default FacultyPage;
