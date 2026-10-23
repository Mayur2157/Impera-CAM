import type { ReactNode } from "react";
import { Link } from "react-router";

import { Brand } from "@/components/Brand";
import { Card } from "@/components/ui/misc";

export function AuthLayout({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center px-4 py-10">
      <main className="w-full max-w-md">
        <div className="mb-8 flex justify-center">
          <Brand />
        </div>
        <Card className="p-6 sm:p-8">
          <h1 className="text-xl font-semibold">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
          <div className="mt-6">{children}</div>
        </Card>
        {footer && <div className="mt-6 text-center text-sm text-muted">{footer}</div>}
      </main>
      <footer className="mt-10 flex gap-4 text-xs text-muted">
        <Link to="/privacy" className="underline-offset-2 hover:underline">
          Privacy notice
        </Link>
        <Link to="/terms" className="underline-offset-2 hover:underline">
          Terms
        </Link>
      </footer>
    </div>
  );
}
