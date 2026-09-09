/**
 * RAXEL Central API Service Client
 * Unified HTTP request layer with error handling and credentials support.
 */

const API_BASE = '/api';

async function request(endpoint, options = {}) {
  const defaultHeaders = {
    'Content-Type': 'application/json',
  };

  // If payload is FormData (for file uploads), do not set Content-Type header
  if (options.body instanceof FormData) {
    delete defaultHeaders['Content-Type'];
  }

  const token = localStorage.getItem('raxel_token');
  if (token) {
    defaultHeaders['Authorization'] = `Bearer ${token}`;
  }

  const config = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  };

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, config);
    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      const errorMsg = data.detail || data.message || `HTTP Error ${res.status}`;
      throw new Error(errorMsg);
    }
    return data;
  } catch (err) {
    if (err.name !== 'AbortError') {
      console.error(`API Error on [${endpoint}]:`, err.message);
    }
    throw err;
  }
}

export const api = {
  // Auth
  signup: (username, password, role = 'student', options = {}) => request('/auth/signup', { method: 'POST', body: JSON.stringify({ username, password, role }), ...options }),
  login: (username, password, options = {}) => request('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }), ...options }),
  logout: (options = {}) => request('/auth/logout', { method: 'POST', ...options }),
  getMe: (options = {}) => request('/auth/me', options),

  // Chat
  sendMessage: (message, conversationId, chatHistory, docTypeFilter, options = {}) => 
    request('/chat', {
      method: 'POST',
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
        chat_history: chatHistory,
        doc_type_filter: docTypeFilter
      }),
      ...options
    }),

  // Documents (Faculty & Student)
  listDocuments: (statusFilter, docType, options = {}) => {
    const params = new URLSearchParams();
    if (statusFilter) params.append('status_filter', statusFilter);
    if (docType) params.append('doc_type', docType);
    const query = params.toString() ? `?${params.toString()}` : '';
    return request(`/documents${query}`, options);
  },
  getSuggestedDocTypes: (options = {}) => request('/documents/suggested-types', options),
  getDocumentDetails: (docId, options = {}) => request(`/documents/${docId}`, options),
  getDocumentDownloadUrl: (docId, disposition = 'attachment') => {
    const token = localStorage.getItem('raxel_token');
    const params = new URLSearchParams();
    if (token) params.append('token', token);
    if (disposition) params.append('disposition', disposition);
    const query = params.toString() ? `?${params.toString()}` : '';
    return `/api/documents/${docId}/download${query}`;
  },
  getDocumentViewUrl: (docId) => {
    const token = localStorage.getItem('raxel_token');
    const params = new URLSearchParams();
    if (token) params.append('token', token);
    params.append('disposition', 'inline');
    return `/api/documents/${docId}/download?${params.toString()}`;
  },
  uploadDocument: (formData, options = {}) => request('/documents/upload', { method: 'POST', body: formData, ...options }),
  deleteDocument: (docId, options = {}) => request(`/documents/${docId}`, { method: 'DELETE', ...options }),

  // Admin Controls
  getUsers: (options = {}) => request('/admin/users', options),
  updateUserRole: (username, role, options = {}) => request(`/admin/users/${username}/role`, { method: 'PATCH', body: JSON.stringify({ role }), ...options }),
  toggleUserActive: (username, active, options = {}) => request(`/admin/users/${username}/active`, { method: 'PATCH', body: JSON.stringify({ active }), ...options }),

  getAdminDocuments: (statusFilter, docType, options = {}) => {
    const params = new URLSearchParams();
    if (statusFilter) params.append('status_filter', statusFilter);
    if (docType) params.append('doc_type', docType);
    const query = params.toString() ? `?${params.toString()}` : '';
    return request(`/admin/documents${query}`, options);
  },
  approveDocument: (docId, options = {}) => request(`/admin/documents/${docId}/approve`, { method: 'POST', ...options }),
  rejectDocument: (docId, rejectionReason, options = {}) => request(`/admin/documents/${docId}/reject`, { method: 'POST', body: JSON.stringify({ rejection_reason: rejectionReason }), ...options }),
  archiveDocument: (docId, options = {}) => request(`/admin/documents/${docId}/archive`, { method: 'POST', ...options }),
  restoreDocument: (docId, targetGovernance = 'pending_review', options = {}) => request(`/admin/documents/${docId}/restore`, { method: 'POST', body: JSON.stringify({ target_governance: targetGovernance }), ...options }),

  runQualityScan: (options = {}) => request('/admin/quality', options),
  resolveQualityIssue: (issueId, action, reason, options = {}) => request(`/admin/quality/${issueId}/resolve`, { method: 'POST', body: JSON.stringify({ resolution_action: action, reason }), ...options }),

  getHealth: (options = {}) => request('/admin/health', options),
  getDiagnostics: (options = {}) => request('/admin/diagnostics', options),

  getBackups: (options = {}) => request('/admin/backups', options),
  createBackup: (note, options = {}) => request('/admin/backups', { method: 'POST', body: JSON.stringify({ note }), ...options }),
  validateBackup: (backupId, options = {}) => request(`/admin/backups/${backupId}/validate`, { method: 'POST', ...options }),
  restoreBackup: (backupId, options = {}) => request(`/admin/backups/${backupId}/restore`, { method: 'POST', ...options }),
  rebuildIndex: (options = {}) => request('/admin/index/rebuild', { method: 'POST', ...options }),
};
