import { cva } from "class-variance-authority";

export const buttonStyles = cva(
  "inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-4 text-sm font-medium whitespace-nowrap " +
    "transition-colors disabled:cursor-not-allowed disabled:opacity-60",
  {
    variants: {
      variant: {
        primary: "bg-primary text-primary-fg hover:bg-primary-hover",
        secondary: "border border-border bg-surface text-text hover:bg-surface-2",
        ghost: "text-text hover:bg-surface-2",
        danger: "bg-break text-white hover:opacity-90 dark:text-bg",
      },
      size: { md: "", sm: "min-h-9 px-3", icon: "size-10 px-0" },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export const inputStyles =
  "block w-full min-h-10 rounded-md border bg-surface px-3 text-sm text-text placeholder:text-muted " +
  "border-border aria-[invalid=true]:border-break";
