import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { api } from '../services/api';
import { 
  FileText, CheckCircle2, Search, BookOpen, Filter, ExternalLink, 
  Download, Eye, X, Calendar, Layers, ShieldCheck, Tag, Info, RefreshCw
} from 'lucide-react';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { TableSkeleton } from '../components/ui/Skeleton';
import { EmptyState } from '../components/ui/EmptyState';
import { Card } from '../components/ui/Card';

const CATEGORIES = [
  { id: 'all', label: 'All Documents' },
  { id: 'academic_regulations', label: 'Academic Regulations' },
  { id: 'curriculum', label: 'Curriculum & Syllabi' },
  { id: 'exam_policy', label: 'Exam Policies' },
  { id: 'fee_structure', label: 'Fee Structures' },
  { id: 'general', label: 'General Policies' },
];

export const SourcesPage = () => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedDoc, setSelectedDoc] = useState(null);

  const abortControllerRef = useRef(null);

  const fetchDocs = useCallback(async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      setLoading(true);
      setError(null);
      const data = await api.listDocuments('indexed', undefined, { signal: controller.signal });
      setDocuments(data.documents || []);
    } catch (err) {
      if (err.name !== 'AbortError') {
        console.error('Error loading documents:', err);
        setError(err.message || 'Failed to fetch knowledge sources.');
      }
    } finally {
      if (abortControllerRef.current === controller) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    fetchDocs();
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchDocs]);

  const getDocType = useCallback((doc) => doc.document_type || doc.doc_type || 'general', []);

  const filteredDocs = useMemo(() => {
    return documents.filter(doc => {
      const docType = getDocType(doc);
      const matchesCategory = selectedCategory === 'all' || docType === selectedCategory;
      const searchLower = searchTerm.toLowerCase();
      const matchesSearch = 
        doc.title?.toLowerCase().includes(searchLower) ||
        docType.toLowerCase().includes(searchLower) ||
        doc.academic_year?.toLowerCase().includes(searchLower) ||
        doc.original_filename?.toLowerCase().includes(searchLower);

      return matchesCategory && matchesSearch;
    });
  }, [documents, selectedCategory, searchTerm, getDocType]);

  return (
    <div className="rx-container py-8 sm:py-12 flex-1 flex flex-col">
      {/* Header section */}
      <div className="mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <BookOpen className="w-5 h-5 text-raxel-teal shrink-0" />
            <h1 className="text-2xl font-bold text-raxel-indigo tracking-tight">
              Knowledge Base Sources
            </h1>
            <span className="ml-2 px-2.5 py-0.5 text-xs font-semibold rounded-full bg-raxel-violet-soft text-raxel-indigo">
              {documents.length} Grounded Sources
            </span>
          </div>
          <p className="text-raxel-muted text-xs sm:text-sm max-w-2xl">
            Official indexed college documents used by RAXEL to synthesize accurate, multi-document grounded answers with citations.
          </p>
        </div>

        <Button
          variant="secondary"
          size="sm"
          icon={RefreshCw}
          onClick={fetchDocs}
          isLoading={loading}
        >
          {loading ? 'Refreshing Sources...' : 'Refresh List'}
        </Button>
      </div>

      {/* Controls: Search and Filter Tabs */}
      <div className="flex flex-col gap-4 mb-6">
        <div className="max-w-xl">
          <Input
            icon={Search}
            placeholder="Search verified sources by title, category, academic year..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        {/* Category Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-2 scrollbar-none">
          <Filter className="w-4 h-4 text-raxel-muted mr-1 shrink-0 hidden sm:block" />
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md whitespace-nowrap transition-all ${
                selectedCategory === cat.id
                  ? 'bg-raxel-indigo text-white shadow-sm'
                  : 'bg-white text-raxel-muted border border-raxel-border hover:text-raxel-indigo hover:bg-raxel-surface-subtle'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content Area */}
      {loading ? (
        <TableSkeleton rows={6} cols={5} />
      ) : error ? (
        <div className="p-6 text-center border border-red-200 bg-red-50 rounded-lg text-red-700">
          <p className="font-semibold text-sm mb-2">{error}</p>
          <Button variant="secondary" size="sm" onClick={fetchDocs}>
            Try Again
          </Button>
        </div>
      ) : filteredDocs.length === 0 ? (
        <EmptyState
          icon={Search}
          title="No Knowledge Documents Found"
          description={
            searchTerm || selectedCategory !== 'all'
              ? `No documents matching current filters. Try resetting search or category.`
              : 'No official indexed knowledge documents found in the system repository.'
          }
        />
      ) : (
        <div className="w-full overflow-x-auto border border-raxel-border rounded-lg bg-white shadow-sm">
          <table className="w-full text-left text-xs sm:text-sm border-collapse">
            <thead>
              <tr className="bg-raxel-soft-white text-raxel-muted uppercase text-[11px] font-semibold tracking-wider border-b border-raxel-border">
                <th className="p-3.5 sm:p-4">Document Title</th>
                <th className="p-3.5 sm:p-4">Category / Type</th>
                <th className="p-3.5 sm:p-4">Academic Year</th>
                <th className="p-3.5 sm:p-4">Version</th>
                <th className="p-3.5 sm:p-4">Status</th>
                <th className="p-3.5 sm:p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-raxel-border-subtle">
              {filteredDocs.map((doc, idx) => {
                const docId = doc.document_id || doc.id || `doc_${idx}`;
                const docType = getDocType(doc);
                const downloadUrl = api.getDocumentDownloadUrl(docId, 'attachment');
                const viewUrl = api.getDocumentViewUrl(docId);

                return (
                  <tr
                    key={docId}
                    onClick={() => setSelectedDoc(doc)}
                    className="hover:bg-raxel-surface-subtle transition-colors duration-150 cursor-pointer group"
                  >
                    <td className="p-3.5 sm:p-4 font-semibold text-raxel-indigo">
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-raxel-teal shrink-0 group-hover:scale-110 transition-transform" />
                        <span className="truncate max-w-xs sm:max-w-md">{doc.title}</span>
                      </div>
                    </td>
                    <td className="p-3.5 sm:p-4 capitalize text-raxel-ink">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] rounded bg-raxel-soft-white font-medium text-raxel-muted border border-raxel-border-subtle">
                        <Tag className="w-3 h-3 text-raxel-indigo/60" />
                        {docType.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="p-3.5 sm:p-4 text-raxel-muted">{doc.academic_year || 'N/A'}</td>
                    <td className="p-3.5 sm:p-4 text-raxel-muted">v{doc.version || '1.0'}</td>
                    <td className="p-3.5 sm:p-4">
                      <Badge variant="indexed">
                        <CheckCircle2 className="w-3 h-3 inline mr-1" />
                        Indexed
                      </Badge>
                    </td>
                    <td className="p-3.5 sm:p-4 text-right">
                      <div className="flex items-center justify-end gap-1.5" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => setSelectedDoc(doc)}
                          className="p-1.5 rounded text-raxel-muted hover:text-raxel-indigo hover:bg-raxel-violet-soft transition-colors"
                          title="View Metadata Details"
                        >
                          <Info className="w-4 h-4" />
                        </button>
                        <a
                          href={viewUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="p-1.5 rounded text-raxel-muted hover:text-raxel-indigo hover:bg-raxel-violet-soft transition-colors"
                          title="View PDF in Browser"
                        >
                          <Eye className="w-4 h-4" />
                        </a>
                        <a
                          href={downloadUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="p-1.5 rounded text-raxel-muted hover:text-raxel-teal hover:bg-teal-50 transition-colors"
                          title="Download PDF"
                        >
                          <Download className="w-4 h-4" />
                        </a>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Document Detail Modal */}
      <AnimatePresence>
        {selectedDoc && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-raxel-indigo/40 backdrop-blur-xs">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              transition={{ duration: 0.2 }}
              className="bg-white rounded-xl border border-raxel-border shadow-xl w-full max-w-lg overflow-hidden flex flex-col max-h-[90vh]"
            >
              {/* Modal Header */}
              <div className="p-5 border-b border-raxel-border bg-raxel-soft-white flex items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div className="p-2.5 rounded-lg bg-raxel-violet-soft text-raxel-indigo shrink-0">
                    <FileText className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="font-bold text-lg text-raxel-indigo leading-snug">
                      {selectedDoc.title}
                    </h3>
                    <p className="text-xs text-raxel-muted mt-0.5">
                      ID: {selectedDoc.document_id || selectedDoc.id || 'N/A'}
                    </p>
                  </div>
                </div>

                <button
                  onClick={() => setSelectedDoc(null)}
                  className="p-1.5 rounded-md text-raxel-muted hover:text-raxel-indigo hover:bg-raxel-surface-subtle transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Modal Body */}
              <div className="p-5 space-y-4 overflow-y-auto flex-1 text-xs sm:text-sm">
                <div>
                  <label className="text-[11px] font-semibold text-raxel-muted uppercase tracking-wider block mb-1">
                    Description / Purpose
                  </label>
                  <p className="text-raxel-ink bg-raxel-surface-subtle p-3 rounded-md border border-raxel-border-subtle">
                    {selectedDoc.description || 'Official college knowledge document indexed into RAXEL vector store for grounded retrieval.'}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-lg border border-raxel-border bg-white">
                    <span className="text-raxel-muted text-[11px] font-semibold block uppercase">Category</span>
                    <span className="font-medium text-raxel-indigo capitalize">
                      {getDocType(selectedDoc).replace(/_/g, ' ')}
                    </span>
                  </div>

                  <div className="p-3 rounded-lg border border-raxel-border bg-white">
                    <span className="text-raxel-muted text-[11px] font-semibold block uppercase">Academic Year</span>
                    <span className="font-medium text-raxel-indigo">
                      {selectedDoc.academic_year || '2024-2025'}
                    </span>
                  </div>

                  <div className="p-3 rounded-lg border border-raxel-border bg-white">
                    <span className="text-raxel-muted text-[11px] font-semibold block uppercase">Version</span>
                    <span className="font-medium text-raxel-indigo">
                      v{selectedDoc.version || '1.0'}
                    </span>
                  </div>

                  <div className="p-3 rounded-lg border border-raxel-border bg-white">
                    <span className="text-raxel-muted text-[11px] font-semibold block uppercase">Pages / Chunks</span>
                    <span className="font-medium text-raxel-indigo">
                      {selectedDoc.page_count || 'N/A'} pages ({selectedDoc.chunk_count || 'N/A'} chunks)
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between p-3 rounded-lg bg-teal-50 border border-teal-200 text-teal-800">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-teal-600 shrink-0" />
                    <div>
                      <span className="font-semibold block text-xs">Grounded Authority Source</span>
                      <span className="text-[11px] text-teal-700">Status: {selectedDoc.status || 'indexed'} (Governance: {selectedDoc.governance_status || 'approved'})</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Modal Footer */}
              <div className="p-4 border-t border-raxel-border bg-raxel-soft-white flex items-center justify-end gap-2 sm:gap-3">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setSelectedDoc(null)}
                >
                  Close
                </Button>
                <a
                  href={api.getDocumentViewUrl(selectedDoc.document_id || selectedDoc.id)}
                  target="_blank"
                  rel="noreferrer"
                >
                  <Button
                    variant="secondary"
                    size="sm"
                    icon={Eye}
                  >
                    View PDF
                  </Button>
                </a>
                <a
                  href={api.getDocumentDownloadUrl(selectedDoc.document_id || selectedDoc.id, 'attachment')}
                  target="_blank"
                  rel="noreferrer"
                >
                  <Button
                    variant="primary"
                    size="sm"
                    icon={Download}
                  >
                    Download PDF
                  </Button>
                </a>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default SourcesPage;
