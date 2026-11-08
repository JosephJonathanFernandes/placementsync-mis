import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

const cn = (...classes: string[]) => twMerge(clsx(classes));

export function Panel({
  children,
  className = "",
}: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("panel p-6", className)}>
      {children}
    </div>
  );
}
