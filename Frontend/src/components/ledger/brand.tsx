import { Link } from "@tanstack/react-router";

export function Logo() {
  return (
    <Link to="/" className="inline-flex items-center gap-2 font-semibold tracking-tight">
      <span aria-hidden className="grid size-7 place-items-center rounded-md bg-primary font-mono text-sm text-primary-foreground">Σ</span>
      <span>Impera <span className="text-muted-foreground font-normal">CAM</span></span>
    </Link>
  );
}

export function PublicHeader() {
  return (
    <header className="sticky top-0 z-30 border-b bg-background/85 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Logo />
        <nav className="flex items-center gap-1 text-sm sm:gap-4">
          <Link to="/pricing" className="rounded-md px-2 py-1.5 text-muted-foreground hover:text-foreground">Pricing</Link>
          <Link to="/login" search={{ next: undefined }} className="rounded-md px-2 py-1.5 text-muted-foreground hover:text-foreground">Sign in</Link>
          <Link to="/signup" className="rounded-md bg-primary px-3 py-1.5 font-medium text-primary-foreground hover:bg-primary/90">Get started</Link>
        </nav>
      </div>
    </header>
  );
}

export function PublicFooter() {
  return (
    <footer className="border-t">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-8 text-sm text-muted-foreground sm:flex-row sm:justify-between sm:px-6">
        <span>© {new Date().getFullYear()} Impera CAM</span>
        <div className="flex gap-4">
          <Link to="/privacy" className="hover:text-foreground">Privacy</Link>
          <Link to="/terms" className="hover:text-foreground">Terms</Link>
          <Link to="/pricing" className="hover:text-foreground">Pricing</Link>
        </div>
      </div>
    </footer>
  );
}
