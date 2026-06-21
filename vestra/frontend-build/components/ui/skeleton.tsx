'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

// ─── Base Skeleton ──────────────────────────────────────────────────────────

interface SkeletonBaseProps {
  className?: string;
}

function Skeleton({ className }: SkeletonBaseProps) {
  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-xl bg-gray-200 dark:bg-gray-800',
        'before:absolute before:inset-0 before:-translate-x-full',
        'before:animate-[shimmer_2s_infinite]',
        'before:bg-gradient-to-r before:from-transparent before:via-white/20 before:to-transparent',
        className
      )}
      aria-hidden="true"
    />
  );
}

Skeleton.displayName = 'Skeleton';

// ─── SkeletonText ───────────────────────────────────────────────────────────

interface SkeletonTextProps {
  lines?: number;
  width?: string;
  className?: string;
  lastLineWidth?: string;
}

function SkeletonText({ lines = 3, width, className, lastLineWidth = '60%' }: SkeletonTextProps) {
  return (
    <div className={cn('flex flex-col gap-2.5', className)} aria-hidden="true">
      {Array.from({ length: lines }).map((_, i) => {
        const isLast = i === lines - 1;
        return (
          <Skeleton
            key={i}
            className={cn(
              'h-4 rounded-md',
              width || (isLast ? lastLineWidth : '100%')
            )}
          />
        );
      })}
    </div>
  );
}

SkeletonText.displayName = 'SkeletonText';

// ─── SkeletonCard ───────────────────────────────────────────────────────────

interface SkeletonCardProps {
  className?: string;
  imageHeight?: string;
  lines?: number;
}

function SkeletonCard({ className, imageHeight = 'h-48', lines = 3 }: SkeletonCardProps) {
  return (
    <div
      className={cn(
        'rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 overflow-hidden shadow-sm',
        className
      )}
      aria-hidden="true"
    >
      {/* Image placeholder */}
      <Skeleton className={cn('w-full rounded-none', imageHeight)} />

      {/* Content */}
      <div className="p-4 space-y-3">
        {/* Title */}
        <Skeleton className="h-5 w-3/4 rounded-md" />

        {/* Subtitle */}
        <Skeleton className="h-3.5 w-1/2 rounded-md" />

        {/* Text lines */}
        <SkeletonText lines={lines} className="mt-3" />
      </div>
    </div>
  );
}

SkeletonCard.displayName = 'SkeletonCard';

// ─── SkeletonCircle ─────────────────────────────────────────────────────────

interface SkeletonCircleProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

function SkeletonCircle({ size = 'md', className }: SkeletonCircleProps) {
  const sizes = {
    sm: 'w-8 h-8',
    md: 'w-12 h-12',
    lg: 'w-20 h-20',
  };

  return <Skeleton className={cn('rounded-full flex-shrink-0', sizes[size], className)} />;
}

SkeletonCircle.displayName = 'SkeletonCircle';

// ─── SkeletonRectangle ──────────────────────────────────────────────────────

interface SkeletonRectangleProps {
  width?: string;
  height?: string;
  className?: string;
}

function SkeletonRectangle({ width = 'w-full', height = 'h-32', className }: SkeletonRectangleProps) {
  return <Skeleton className={cn(width, height, className)} />;
}

SkeletonRectangle.displayName = 'SkeletonRectangle';

// ─── SkeletonAvatar (inline helper) ─────────────────────────────────────────

interface SkeletonAvatarProps {
  className?: string;
}

function SkeletonAvatar({ className }: SkeletonAvatarProps) {
  return (
    <div className={cn('flex items-center gap-3', className)} aria-hidden="true">
      <SkeletonCircle size="sm" />
      <div className="flex flex-col gap-2 flex-1">
        <Skeleton className="h-3.5 w-32 rounded-md" />
        <Skeleton className="h-3 w-24 rounded-md" />
      </div>
    </div>
  );
}

SkeletonAvatar.displayName = 'SkeletonAvatar';

export { Skeleton, SkeletonText, SkeletonCard, SkeletonCircle, SkeletonRectangle, SkeletonAvatar };
