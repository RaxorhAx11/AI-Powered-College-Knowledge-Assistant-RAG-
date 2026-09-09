import React from 'react';
import { AlertCircle, CheckCircle2, Info, AlertTriangle, X } from 'lucide-react';

export const Alert = ({
  type = 'info',
  message,
  onClose,
  className = '',
}) => {
  if (!message) return null;

  const styles = {
    success: 'bg-status-success-bg text-status-success-text border-status-success-border',
    error: 'bg-status-danger-bg text-status-danger-text border-status-danger-border',
    warning: 'bg-status-warning-bg text-status-warning-text border-status-warning-border',
    info: 'bg-raxel-violet-soft text-raxel-indigo border-raxel-violet-muted',
  };

  const icons = {
    success: CheckCircle2,
    error: AlertCircle,
    warning: AlertTriangle,
    info: Info,
  };

  const Icon = icons[type] || Info;

  return (
    <div className={`flex items-center justify-between gap-3 p-3 rounded-sm border text-xs sm:text-sm font-medium transition-all ${styles[type] || styles.info} ${className}`}>
      <div className="flex items-center gap-2.5">
        <Icon className="w-4 h-4 shrink-0" />
        <span>{message}</span>
      </div>
      {onClose && (
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-black/5 transition-colors"
          aria-label="Dismiss alert"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
};

export default Alert;
