import React from 'react';

export const Skeleton = ({ className = '', ...props }) => {
  return (
    <div
      className={`animate-pulse bg-raxel-border/60 rounded ${className}`}
      {...props}
    />
  );
};

export const TableSkeleton = ({ rows = 4, cols = 5 }) => {
  return (
    <div className="w-full border border-raxel-border rounded-lg overflow-hidden bg-white shadow-sm">
      <div className="bg-raxel-soft-white border-b border-raxel-border p-3 flex gap-4">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-4 flex-1" />
        ))}
      </div>
      <div className="divide-y divide-raxel-border-subtle">
        {Array.from({ length: rows }).map((_, r) => (
          <div key={r} className="p-3.5 flex gap-4 items-center">
            {Array.from({ length: cols }).map((_, c) => (
              <Skeleton key={c} className="h-4 flex-1" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
};

export default Skeleton;
