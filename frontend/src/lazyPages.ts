import { lazy } from "react";

// Each page is its own chunk, so signing in doesn't download the app,
// and later chart-heavy pages don't weigh down the rest.
export const LoginPage = lazy(() =>
  import("@/features/auth/LoginPage").then((m) => ({ default: m.LoginPage })),
);
export const SignupPage = lazy(() =>
  import("@/features/auth/SignupPage").then((m) => ({ default: m.SignupPage })),
);
export const PrivacyPage = lazy(() =>
  import("@/features/legal/LegalPages").then((m) => ({ default: m.PrivacyPage })),
);
export const TermsPage = lazy(() =>
  import("@/features/legal/LegalPages").then((m) => ({ default: m.TermsPage })),
);
export const AppShell = lazy(() =>
  import("@/features/shell/AppShell").then((m) => ({ default: m.AppShell })),
);
export const NewAnalysisPage = lazy(() =>
  import("@/features/upload/NewAnalysisPage").then((m) => ({ default: m.NewAnalysisPage })),
);
export const StatementsPage = lazy(() =>
  import("@/features/jobs/StatementsPage").then((m) => ({ default: m.StatementsPage })),
);
export const JobPage = lazy(() => import("@/features/jobs/JobPage").then((m) => ({ default: m.JobPage })));
