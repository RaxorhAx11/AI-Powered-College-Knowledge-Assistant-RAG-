import React from 'react';
import { BookOpen, Calendar, Tag, Layers, ExternalLink, Download, Eye } from 'lucide-react';
import { api } from '../services/api';

export const CitationCard = ({ citation }) => {
  if (!citation) return null;

  const docName = citation.document || citation.document_name || citation.doc_title || 'College Document';
  const pageNum = citation.page_number || citation.page;
  const docType = citation.document_type || citation.doc_type;
  const version = citation.version;
  const effectiveDate = citation.effective_date;
  const docId = citation.document_id || citation.doc_id || citation.id;

  return (
    <div className="bg-raxel-soft-white border border-raxel-border rounded-sm p-3 mt-2 text-xs shadow-sm flex flex-col gap-1.5 transition-all hover:border-raxel-indigo/30">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 font-semibold text-raxel-indigo truncate">
          <BookOpen className="w-4 h-4 text-raxel-teal shrink-0" />
          <span className="text-xs sm:text-sm truncate">{docName}</span>
        </div>

        {docId && (
          <div className="flex items-center gap-1.5 shrink-0">
            <a
              href={api.getDocumentViewUrl(docId)}
              target="_blank"
              rel="noreferrer"
              className="p-1 rounded text-raxel-muted hover:text-raxel-indigo hover:bg-raxel-violet-soft transition-colors flex items-center gap-1 text-[11px]"
              title="View Original PDF"
            >
              <Eye className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">View</span>
            </a>
            <a
              href={api.getDocumentDownloadUrl(docId, 'attachment')}
              target="_blank"
              rel="noreferrer"
              className="p-1 rounded text-raxel-muted hover:text-raxel-teal hover:bg-teal-50 transition-colors flex items-center gap-1 text-[11px]"
              title="Download Original PDF"
            >
              <Download className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Download</span>
            </a>
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-2 text-[11px] text-raxel-muted">
        {pageNum && (
          <span className="inline-flex items-center gap-1 bg-white px-2 py-0.5 rounded border border-raxel-border-subtle">
            <strong className="text-raxel-ink">Page:</strong> {pageNum}
          </span>
        )}
        {docType && (
          <span className="inline-flex items-center gap-1">
            <Tag className="w-3 h-3 text-raxel-muted" />
            <span className="capitalize">{docType.replace('_', ' ')}</span>
          </span>
        )}
        {version && (
          <span className="inline-flex items-center gap-1">
            <Layers className="w-3 h-3 text-raxel-muted" />
            <span>v{version}</span>
          </span>
        )}
        {effectiveDate && (
          <span className="inline-flex items-center gap-1">
            <Calendar className="w-3 h-3 text-raxel-muted" />
            <span>Effective: {effectiveDate}</span>
          </span>
        )}
      </div>
    </div>
  );
};

export default CitationCard;
