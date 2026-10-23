import * as Dialog from "@radix-ui/react-dialog";
import * as Menu from "@radix-ui/react-dropdown-menu";
import {
  ChartColumn,
  ChevronDown,
  FilePlus2,
  Files,
  KeyRound,
  LayoutDashboard,
  LogOut,
  Menu as MenuIcon,
  Moon,
  Settings,
  ShieldCheck,
  Sun,
  Users,
  X,
} from "lucide-react";
import { Suspense, useState } from "react";
import { NavLink, Outlet } from "react-router";

import type { Me } from "@/api/types";
import { useAuth } from "@/auth/AuthProvider";
import { Brand } from "@/components/Brand";
import { LoadingState } from "@/components/states";
import { Alert } from "@/components/ui/misc";
import { cn } from "@/lib/cn";
import { currentTheme, setTheme, type Theme } from "@/lib/theme";

interface NavItem {
  to: string;
  label: string;
  Icon: typeof Files;
  end?: boolean;
  show?: (me: Me) => boolean;
}

const manager = (me: Me) => me.role === "owner" || me.role === "admin";

const NAV: NavItem[] = [
  { to: "/app", label: "Dashboard", Icon: LayoutDashboard, end: true },
  { to: "/app/new", label: "New analysis", Icon: FilePlus2 },
  { to: "/app/statements", label: "Statements", Icon: Files },
  { to: "/app/usage", label: "Usage", Icon: ChartColumn },
  { to: "/app/api-keys", label: "API keys", Icon: KeyRound, show: manager },
  { to: "/app/team", label: "Team", Icon: Users, show: manager },
  { to: "/app/settings", label: "Settings", Icon: Settings },
  { to: "/app/admin", label: "Impera admin", Icon: ShieldCheck, show: (me) => me.is_superuser },
];

function NavList({ me, onNavigate }: { me: Me; onNavigate?: () => void }) {
  return (
    <ul className="space-y-1">
      {NAV.filter((n) => !n.show || n.show(me)).map(({ to, label, Icon, end }) => (
        <li key={to}>
          <NavLink
            to={to}
            end={end}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                "flex min-h-10 items-center gap-3 rounded-md px-3 text-sm font-medium",
                isActive ? "bg-primary/10 text-primary" : "text-muted hover:bg-surface-2 hover:text-text",
              )
            }
          >
            <Icon className="size-4.5 shrink-0" aria-hidden />
            {label}
          </NavLink>
        </li>
      ))}
    </ul>
  );
}

function UserMenu({ me }: { me: Me }) {
  const { signOut } = useAuth();
  const [theme, setThemeState] = useState<Theme>(currentTheme);
  const next: Theme = theme === "dark" ? "light" : "dark";
  return (
    <Menu.Root>
      <Menu.Trigger className="flex min-h-10 max-w-56 items-center gap-2 rounded-md px-2 text-sm hover:bg-surface-2">
        <span
          className="grid size-8 shrink-0 place-items-center rounded-full bg-surface-2 font-semibold uppercase"
          aria-hidden
        >
          {me.email.charAt(0)}
        </span>
        <span className="hidden truncate sm:inline">{me.email}</span>
        <ChevronDown className="size-4 shrink-0 text-muted" aria-hidden />
        <span className="sr-only">Account menu</span>
      </Menu.Trigger>
      <Menu.Portal>
        <Menu.Content
          align="end"
          sideOffset={6}
          className="z-50 min-w-56 rounded-md border border-border bg-surface p-1 text-sm shadow-lg"
        >
          <div className="px-3 py-2">
            <p className="truncate font-medium">{me.email}</p>
            <p className="text-xs text-muted capitalize">{me.role}</p>
          </div>
          <Menu.Separator className="my-1 h-px bg-border" />
          <Menu.Item
            onSelect={() => {
              setTheme(next);
              setThemeState(next);
            }}
            className="flex min-h-9 cursor-pointer items-center gap-2 rounded px-3 outline-none data-highlighted:bg-surface-2"
          >
            {next === "dark" ? (
              <Moon className="size-4" aria-hidden />
            ) : (
              <Sun className="size-4" aria-hidden />
            )}
            {next === "dark" ? "Dark theme" : "Light theme"}
          </Menu.Item>
          <Menu.Item
            onSelect={signOut}
            className="flex min-h-9 cursor-pointer items-center gap-2 rounded px-3 outline-none data-highlighted:bg-surface-2"
          >
            <LogOut className="size-4" aria-hidden /> Sign out
          </Menu.Item>
        </Menu.Content>
      </Menu.Portal>
    </Menu.Root>
  );
}

export function AppShell() {
  const { me } = useAuth();
  const [drawerOpen, setDrawerOpen] = useState(false);

  if (!me) return null; // RequireAuth renders the shell only once the account is loaded

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[15rem_1fr]">
      <a
        href="#main"
        className="sr-only z-50 rounded-md bg-primary px-4 py-2 text-primary-fg focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
      >
        Skip to main content
      </a>

      <aside className="hidden border-r border-border bg-surface lg:block">
        <div className="sticky top-0 flex h-dvh flex-col gap-6 p-4">
          <Brand />
          <nav aria-label="Main">
            <NavList me={me} />
          </nav>
        </div>
      </aside>

      <div className="flex min-w-0 flex-col">
        <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-border bg-surface/95 px-4 backdrop-blur sm:px-6">
          <Dialog.Root open={drawerOpen} onOpenChange={setDrawerOpen}>
            <Dialog.Trigger className="grid size-10 place-items-center rounded-md hover:bg-surface-2 lg:hidden">
              <MenuIcon className="size-5" aria-hidden />
              <span className="sr-only">Open navigation</span>
            </Dialog.Trigger>
            <Dialog.Portal>
              <Dialog.Overlay className="fixed inset-0 z-40 bg-black/40" />
              <Dialog.Content className="fixed inset-y-0 left-0 z-50 flex w-72 max-w-[85vw] flex-col gap-6 bg-surface p-4 shadow-xl">
                <div className="flex items-center justify-between">
                  <Dialog.Title asChild>
                    <span>
                      <Brand />
                    </span>
                  </Dialog.Title>
                  <Dialog.Close className="grid size-10 place-items-center rounded-md hover:bg-surface-2">
                    <X className="size-5" aria-hidden />
                    <span className="sr-only">Close navigation</span>
                  </Dialog.Close>
                </div>
                <Dialog.Description className="sr-only">Pages of the Impera CAM portal</Dialog.Description>
                <nav aria-label="Main">
                  <NavList me={me} onNavigate={() => setDrawerOpen(false)} />
                </nav>
              </Dialog.Content>
            </Dialog.Portal>
          </Dialog.Root>

          <div className="flex min-w-0 flex-1 items-center gap-2">
            <span className="truncate font-medium">{me.org_name}</span>
            <span className="shrink-0 rounded-full bg-surface-2 px-2 py-0.5 text-xs font-medium text-muted capitalize">
              {me.plan} plan
            </span>
          </div>
          <UserMenu me={me} />
        </header>

        <main
          id="main"
          tabIndex={-1}
          className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 outline-none sm:px-6 lg:py-8"
        >
          {me.org_status === "suspended" && (
            <Alert tone="warn" title="Your organisation is suspended" className="mb-6">
              You can read existing results, but uploads are paused. Contact Impera CAM support to reinstate
              it.
            </Alert>
          )}
          <Suspense fallback={<LoadingState label="Loading page" rows={3} />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </div>
  );
}
