import { Typography } from "@atlas/ui/ui/components/typography/index";
import { cn } from "@/lib/utils";

export function AtlasLogo({
  collapsed = false,
  className,
  markClassName,
}: AtlasLogoProps) {
  return (
    <div className={cn("flex min-w-0 items-center gap-2", className)}>
      <span
        aria-hidden
        className={cn(
          "relative grid h-10 w-10 shrink-0 place-items-center overflow-hidden rounded-2xl",
          "bg-[#1f1b2d]",
          "shadow-[0_14px_32px_rgba(31,27,45,0.28)] ring-1 ring-white/10",
          markClassName,
        )}
      >
        <span className="absolute left-1/2 top-1 h-5 w-3 -translate-x-1/2 rounded-full bg-[#9096df]" />
        <span className="absolute bottom-1 left-1/2 h-5 w-3 -translate-x-1/2 rounded-full bg-white" />
        <span className="absolute left-[0.72rem] top-1/2 h-5 w-3 -translate-y-1/2 rotate-[-26deg] rounded-full bg-[#bfc4ed]" />
        <span className="absolute right-[0.72rem] top-1/2 h-5 w-3 -translate-y-1/2 rotate-[26deg] rounded-full bg-[#f6f7ff]" />
      </span>

      {!collapsed && (
        <div className="flex min-w-0 flex-col leading-none">
          <Typography className="truncate font-bold text-[1rem] uppercase leading-[0.95] tracking-[0.08em] text-inherit">
            Atlas
          </Typography>
          <Typography className="truncate text-[0.68rem] uppercase leading-[1.1] tracking-[0.14em] text-current/60">
            Usama Aslam
          </Typography>
        </div>
      )}
    </div>
  );
}

interface AtlasLogoProps {
  className?: string;
  collapsed?: boolean;
  markClassName?: string;
}
