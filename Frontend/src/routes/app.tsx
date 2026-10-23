import { createFileRoute, Link, Outlet, useLocation, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { BookOpen, FlaskConical, ChartColumn, FileText, KeyRound, LayoutDashboard, LogOut, Menu, Monitor, Moon, Settings, Shield, Sun, Users, KeySquare, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuRadioGroup, DropdownMenuRadioItem,
  DropdownMenuSeparator, DropdownMenuSub, DropdownMenuSubContent, DropdownMenuSubTrigger, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Logo } from "@/components/ledger/brand";
import { ChangePasswordDialog } from "@/components/ledger/change-password";
import { ErrorState } from "@/components/ledger/states";
import { useAuth } from "@/lib/auth";
import { useTheme, type ThemePref } from "@/lib/theme";
import { useMe } from "@/lib/api/hooks";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/app")({
  ssr: false, // token lives in sessionStorage; guard runs client-side
  head: () => ({ meta: [{ name: "robots", content: "noindex" }] }),
  component: AppLayout,
});

type Nav = { to: "/app" | "/app/statements" | "/app/api-keys" | "/app/usage" | "/app/team" | "/app/settings" | "/app/docs" | "/app/playground" | "/admin"; label: string; icon: typeof FileText; exact?: boolean };
const NAV: Nav[] = [
  { to: "/app", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { to: "/app/statements", label: "Statements", icon: FileText },
  { to: "/app/api-keys", label: "API keys", icon: KeyRound },
  { to: "/app/usage", label: "Usage", icon: ChartColumn },
  { to: "/app/team", label: "Team", icon: Users },
  { to: "/app/settings", label: "Settings", icon: Settings },
  { to: "/app/docs", label: "Docs", icon: BookOpen },
  { to: "/app/playground", label: "Playground", icon: FlaskConical },
];

function AppLayout() {
  const { ready, token, signOut } = useAuth();
  const me = useMe(ready && !!token);
  const nav = useNavigate();
  const loc = useLocation();
  const [open, setOpen] = useState(false);
  const [pwOpen, setPwOpen] = useState(false);
  const { theme, setTheme } = useTheme();

  useEffect(() => {
    if (ready && !token && window.location.pathname.startsWith("/app")) nav({ to: "/login", search: { next: window.location.pathname + window.location.search }, replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, token]);
  useEffect(() => setOpen(false), [loc.pathname]);

  if (!ready || !token || me.isLoading) {
    return (
      <div className="flex min-h-screen" aria-busy="true">
        <div className="hidden w-64 border-r bg-sidebar p-4 md:block"><Skeleton className="h-8 w-32" /></div>
        <div className="flex-1 space-y-4 p-8"><Skeleton className="h-10 w-64" /><Skeleton className="h-40 w-full" /></div>
      </div>
    );
  }
  if (me.error || !me.data) return <div className="p-8"><ErrorState error={me.error} onRetry={() => me.refetch()} /></div>;

  const user = me.data;
  const items = user.is_superuser ? [...NAV, { to: "/admin", label: "Staff console", icon: Shield } as Nav] : NAV;

  const handleSignOut = async () => {
    await signOut();
    nav({ to: "/login", search: { next: undefined }, replace: true });
  };

  const sidebar = (
    <nav aria-label="Main" className="flex flex-col gap-0.5 p-3">
      {items.map((it) => {
        const active = it.exact ? loc.pathname === it.to : loc.pathname.startsWith(it.to);
        const Icon = it.icon;
        return (
          <Link key={it.to} to={it.to} aria-current={active ? "page" : undefined}
            className={cn("flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
              active ? "bg-sidebar-accent font-medium text-sidebar-accent-foreground" : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground")}>
            <Icon className="size-4" aria-hidden />
            {it.label}
          </Link>
        );
      })}
    </nav>
  );

  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r bg-sidebar md:flex">
        <div className="flex h-16 items-center border-b px-5"><Logo /></div>
        {sidebar}
      </aside>
      {open && (
        <div className="fixed inset-0 z-40 md:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
          <div className="absolute inset-0 bg-foreground/30" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-64 border-r bg-sidebar shadow-soft">
            <div className="flex h-16 items-center justify-between border-b px-5">
              <Logo />
              <Button variant="ghost" size="icon" onClick={() => setOpen(false)} aria-label="Close menu"><X className="size-5" /></Button>
            </div>
            {sidebar}
          </aside>
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b bg-background/90 px-4 backdrop-blur sm:px-6">
          <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setOpen(true)} aria-label="Open menu"><Menu className="size-5" /></Button>
          <div className="flex min-w-0 items-center gap-2">
            <span className="truncate font-medium">{user.org_name}</span>
            <span className="rounded-full border px-2 py-0.5 text-xs text-muted-foreground">{user.plan}</span>
          </div>
          <div className="ml-auto">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="gap-2" aria-label="Account menu">
                  <span className="grid size-7 place-items-center rounded-full bg-accent text-xs font-semibold uppercase text-accent-foreground">{user.email[0]}</span>
                  <span className="hidden max-w-40 truncate text-sm sm:inline">{user.email}</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel className="font-normal">
                  <p className="truncate text-sm">{user.email}</p>
                  <p className="text-xs capitalize text-muted-foreground">{user.role}{user.is_superuser ? " · Impera staff" : ""}</p>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onSelect={() => setPwOpen(true)}><KeySquare className="size-4" /> Change password</DropdownMenuItem>
                <DropdownMenuSub>
                  <DropdownMenuSubTrigger>{theme === "dark" ? <Moon className="size-4" /> : theme === "light" ? <Sun className="size-4" /> : <Monitor className="size-4" />} Theme</DropdownMenuSubTrigger>
                  <DropdownMenuSubContent>
                    <DropdownMenuRadioGroup value={theme} onValueChange={(v) => setTheme(v as ThemePref)}>
                      <DropdownMenuRadioItem value="system">System</DropdownMenuRadioItem>
                      <DropdownMenuRadioItem value="light">Light</DropdownMenuRadioItem>
                      <DropdownMenuRadioItem value="dark">Dark</DropdownMenuRadioItem>
                    </DropdownMenuRadioGroup>
                  </DropdownMenuSubContent>
                </DropdownMenuSub>
                <DropdownMenuSeparator />
                <DropdownMenuItem onSelect={handleSignOut}><LogOut className="size-4" /> Sign out</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>
        {user.org_status === "suspended" && (
          <div role="status" className="border-b border-warn/30 bg-warn-soft px-6 py-2.5 text-sm text-warn">
            Your organisation is suspended. The portal is read-only — contact Impera support to restore access.
          </div>
        )}
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
          <Outlet />
        </main>
      </div>
      <ChangePasswordDialog open={pwOpen} onOpenChange={setPwOpen} />
    </div>
  );
}
