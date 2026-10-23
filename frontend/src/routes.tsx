import { Suspense } from "react";
import { Navigate, Outlet, type RouteObject } from "react-router";

import { RequireAuth, RequireRole } from "@/auth/guards";
import { LoadingState } from "@/components/states";
import { ComingSoon, NotFoundPage } from "@/features/misc/pages";
import {
  AppShell,
  JobPage,
  LoginPage,
  NewAnalysisPage,
  PrivacyPage,
  SignupPage,
  StatementsPage,
  TermsPage,
} from "@/lazyPages";

const pageFallback = (
  <div className="mx-auto max-w-3xl p-6">
    <LoadingState label="Loading page" rows={3} />
  </div>
);

const appRoutes: RouteObject[] = [
  { path: "/", element: <Navigate to="/app" replace /> },
  { path: "/login", element: <LoginPage /> },
  { path: "/signup", element: <SignupPage /> },
  { path: "/privacy", element: <PrivacyPage /> },
  { path: "/terms", element: <TermsPage /> },
  {
    path: "/app",
    element: <RequireAuth />,
    children: [
      {
        element: <AppShell />,
        children: [
          {
            index: true,
            element: (
              <ComingSoon title="Dashboard">
                Your organisation's statements this month, quota and recent results will appear here.
              </ComingSoon>
            ),
          },
          { path: "new", element: <NewAnalysisPage /> },
          { path: "statements", element: <StatementsPage /> },
          { path: "statements/:jobId", element: <JobPage /> },
          {
            path: "statements/:jobId/files/:index",
            element: (
              <ComingSoon title="Analysis">
                The full CAM dashboard for this statement is on its way. Until then, download the Excel
                workbook from the upload's page.
              </ComingSoon>
            ),
          },
          {
            path: "usage",
            element: (
              <ComingSoon title="Usage">Statements and pages processed, by day, user and API key.</ComingSoon>
            ),
          },
          {
            path: "api-keys",
            element: (
              <RequireRole roles={["owner", "admin"]}>
                <ComingSoon title="API keys">
                  Create keys so your loan system can send statements directly.
                </ComingSoon>
              </RequireRole>
            ),
          },
          {
            path: "team",
            element: (
              <RequireRole roles={["owner", "admin"]}>
                <ComingSoon title="Team">Invite colleagues and manage their roles.</ComingSoon>
              </RequireRole>
            ),
          },
          {
            path: "settings",
            element: (
              <ComingSoon title="Settings">
                Organisation details, data retention and your password.
              </ComingSoon>
            ),
          },
          {
            path: "admin",
            element: (
              <RequireRole superuser>
                <ComingSoon title="Impera admin">Tenants, plans and platform health.</ComingSoon>
              </RequireRole>
            ),
          },
        ],
      },
    ],
  },
  { path: "*", element: <NotFoundPage /> },
];

export const routes: RouteObject[] = [
  {
    element: (
      <Suspense fallback={pageFallback}>
        <Outlet />
      </Suspense>
    ),
    children: appRoutes,
  },
];
