import React from 'react';
import { FolderOpen } from 'lucide-react';

export const EmptyState = ({
  icon: Icon = FolderOpen,
  title = 'No items found',
  description = 'There are currently no records available to display.',
  action = null,
  className = '',
}) => {
  return (
    <div className={`flex flex-col items-center justify-center p-8 sm:p-12 text-center bg-white border border-raxel-border rounded-lg shadow-sm ${className}`}>
      <div className="w-12 h-12 rounded-full bg-raxel-surface-subtle border border-raxel-border flex items-center justify-center text-raxel-muted mb-3">
        <Icon className="w-6 h-6" />
      </div>
      <h3 className="text-base font-semibold text-raxel-indigo mb-1">{title}</h3>
      <p className="text-xs sm:text-sm text-raxel-muted max-w-md mb-4">{description}</p>
      {action}
    </div>
  );
};

export default EmptyState;
