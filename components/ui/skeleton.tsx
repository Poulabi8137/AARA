'use client'

import { cn } from '@/lib/utils'

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-xl bg-gradient-to-r from-muted via-muted/80 to-muted bg-[length:400%_100%] animate-shimmer',
        className
      )}
      {...props}
    />
  )
}

function SkeletonCard() {
  return (
    <div className="rounded-xl border border-border/50 bg-card/50 backdrop-blur-sm p-6 space-y-4">
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-3 w-1/2" />
      <Skeleton className="h-20 w-full" />
      <div className="flex gap-2">
        <Skeleton className="h-8 w-20" />
        <Skeleton className="h-8 w-20" />
      </div>
    </div>
  )
}

function SkeletonLine({ width = '100%' }: { width?: string }) {
  return <Skeleton className={`h-3 w-[${width}]`} />
}

export { Skeleton, SkeletonCard, SkeletonLine }
