import { Construction } from "lucide-react";
import { Link } from "react-router";

import { PageHeader } from "@/components/states";
import { buttonStyles } from "@/components/ui/styles";
import { Card } from "@/components/ui/misc";

/** A page that is planned but not built yet (customer-portal phases 3–6). */
export function ComingSoon({ title, children }: { title: string; children: string }) {
  return (
    <>
      <PageHeader title={title} />
      <Card className="flex flex-col items-center gap-3 px-6 py-12 text-center">
        <Construction className="size-8 text-muted" aria-hidden />
        <h2 className="text-base font-semibold">Coming soon</h2>
        <p className="max-w-md text-sm text-muted">{children}</p>
        <div className="flex flex-wrap justify-center gap-2">
          <Link to="/app/new" className={buttonStyles()}>
            New analysis
          </Link>
          <Link to="/app/statements" className={buttonStyles({ variant: "secondary" })}>
            View statements
          </Link>
        </div>
      </Card>
    </>
  );
}

export function NotFoundPage() {
  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col items-center justify-center gap-4 px-4 text-center">
      <p className="text-sm font-medium text-muted">404</p>
      <h1 className="text-2xl font-semibold">This page doesn't exist</h1>
      <p className="text-sm text-muted">Check the address, or go back to your statements.</p>
      <Link to="/app" className={buttonStyles()}>
        Go to Impera CAM
      </Link>
    </main>
  );
}
