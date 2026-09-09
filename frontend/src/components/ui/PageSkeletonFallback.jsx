import React from 'react';
import { Skeleton } from './Skeleton';

export const PageSkeletonFallback = () => {
  return (
    <div className="w-full flex-1 flex flex-col min-h-[calc(100vh-64px)] relative bg-raxel-canvas overflow-hidden">
      {/* Top Animated Progress Bar */}
      <div className="absolute top-0 left-0 right-0 h-1 bg-raxel-canvas-soft overflow-hidden z-50">
        <div className="h-full bg-gradient-to-r from-raxel-teal-deep via-raxel-primary to-raxel-teal-deep animate-[shimmer_1.2s_infinite] w-full" />
      </div>

      <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 flex-1 flex flex-col gap-6">
        {/* Header Skeleton */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-raxel-hairline">
          <div className="space-y-2">
            <Skeleton className="h-8 w-64 rounded-lg bg-gray-200/80" />
            <Skeleton className="h-4 w-96 max-w-full rounded bg-gray-200/60" />
          </div>
          <div className="flex items-center gap-3">
            <Skeleton className="h-10 w-28 rounded-lg bg-gray-200/80" />
            <Skeleton className="h-10 w-36 rounded-lg bg-gray-200/80" />
          </div>
        </div>

        {/* Content Cards Skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 rounded-xl border border-raxel-hairline bg-white shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <Skeleton className="h-5 w-32 rounded bg-gray-200/80" />
              <Skeleton className="h-8 w-8 rounded-full bg-gray-200/70" />
            </div>
            <Skeleton className="h-10 w-24 rounded bg-gray-200/90" />
            <Skeleton className="h-3 w-full rounded bg-gray-200/60" />
          </div>

          <div className="p-6 rounded-xl border border-raxel-hairline bg-white shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <Skeleton className="h-5 w-36 rounded bg-gray-200/80" />
              <Skeleton className="h-8 w-8 rounded-full bg-gray-200/70" />
            </div>
            <Skeleton className="h-10 w-28 rounded bg-gray-200/90" />
            <Skeleton className="h-3 w-4/5 rounded bg-gray-200/60" />
          </div>

          <div className="p-6 rounded-xl border border-raxel-hairline bg-white shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <Skeleton className="h-5 w-28 rounded bg-gray-200/80" />
              <Skeleton className="h-8 w-8 rounded-full bg-gray-200/70" />
            </div>
            <Skeleton className="h-10 w-20 rounded bg-gray-200/90" />
            <Skeleton className="h-3 w-full rounded bg-gray-200/60" />
          </div>
        </div>

        {/* Main Body Table Skeleton */}
        <div className="flex-1 bg-white border border-raxel-hairline rounded-xl p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-4 border-b border-gray-100">
            <Skeleton className="h-6 w-48 rounded bg-gray-200/80" />
            <Skeleton className="h-9 w-64 rounded-lg bg-gray-200/70" />
          </div>
          <div className="space-y-3 pt-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-gray-50 gap-4">
                <Skeleton className="h-4 w-1/4 rounded bg-gray-200/70" />
                <Skeleton className="h-4 w-1/6 rounded bg-gray-200/60" />
                <Skeleton className="h-4 w-1/5 rounded bg-gray-200/60" />
                <Skeleton className="h-6 w-20 rounded-full bg-gray-200/80" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default PageSkeletonFallback;
