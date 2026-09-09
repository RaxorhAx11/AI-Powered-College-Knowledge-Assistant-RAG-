import React from 'react';
import { CheckCircle2, AlertCircle, Clock, ShieldCheck, FileText, User } from 'lucide-react';

export const Badge = ({ variant = 'default', children, icon: CustomIcon, className = '' }) => {
  const baseStyles = 'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium tracking-wide border transition-colors select-none';

  const variants = {
    student: 'bg-raxel-violet-soft text-raxel-indigo border-raxel-violet-muted',
    faculty: 'bg-raxel-teal-light text-raxel-teal-deep border-raxel-border',
    admin: 'bg-red-50 text-red-700 border-red-200',
    guest: 'bg-raxel-surface-subtle text-raxel-muted border-raxel-border',
    indexed: 'bg-status-success-bg text-status-success-text border-status-success-border',
    pending: 'bg-status-warning-bg text-status-warning-text border-status-warning-border',
    rejected: 'bg-status-danger-bg text-status-danger-text border-status-danger-border',
    default: 'bg-raxel-surface-subtle text-raxel-ink border-raxel-border',
  };

  const defaultIcons = {
    indexed: CheckCircle2,
    pending: Clock,
    rejected: AlertCircle,
    student: User,
    faculty: FileText,
    admin: ShieldCheck,
  };

  const IconComp = CustomIcon || defaultIcons[variant];

  return (
    <span className={`${baseStyles} ${variants[variant] || variants.default} ${className}`}>
      {IconComp && <IconComp className="w-3 h-3 shrink-0" />}
      <span>{children}</span>
    </span>
  );
};

export default Badge;
