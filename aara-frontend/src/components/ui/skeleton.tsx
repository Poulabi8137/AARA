import { cn } from "@/lib/utils";

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "text" | "card" | "avatar" | "image" | "button";
}

function Skeleton({ className, variant, ...props }: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-muted",
        variant === "avatar" && "rounded-full",
        variant === "image" && "aspect-video",
        variant === "text" && "h-4 w-3/4",
        variant === "card" && "h-32 w-full",
        variant === "button" && "h-10 w-24",
        className,
      )}
      {...props}
    />
  );
}

interface SkeletonTextProps {
  lines?: number;
  className?: string;
}

function SkeletonText({ lines = 3, className }: SkeletonTextProps) {
  return (
    <div className="space-y-2">
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton
          key={index}
          variant="text"
          className={cn(
            "h-4",
            index === lines - 1 ? "w-3/4" : "w-full",
            className,
          )}
        />
      ))}
    </div>
  );
}

interface SkeletonCardProps {
  showImage?: boolean;
  showContent?: boolean;
  className?: string;
}

function SkeletonCard({
  showImage = true,
  showContent = true,
  className,
}: SkeletonCardProps) {
  return (
    <div className={cn("rounded-lg border bg-card p-6 shadow-sm", className)}>
      {showImage && <Skeleton variant="image" className="mb-4" />}
      {showContent && (
        <div className="space-y-3">
          <Skeleton variant="text" className="h-5 w-3/4" />
          <SkeletonText lines={2} className="mt-2" />
          <div className="pt-4">
            <Skeleton variant="button" className="h-9 w-24" />
          </div>
        </div>
      )}
    </div>
  );
}

export { Skeleton, SkeletonText, SkeletonCard };
