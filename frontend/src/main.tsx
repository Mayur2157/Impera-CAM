import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter } from "react-router";
import { RouterProvider } from "react-router/dom";
import { Toaster } from "sonner";

import { ApiError } from "@/api/client";
import { AuthProvider } from "@/auth/AuthProvider";
import { routes } from "@/routes";

import "./styles.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // retry network blips and 5xx, never 4xx: those answers won't change
      retry: (count, error) =>
        count < 2 && !(error instanceof ApiError && error.status >= 400 && error.status < 500),
      refetchOnWindowFocus: false,
    },
  },
});

const router = createBrowserRouter(routes);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <RouterProvider router={router} />
        <Toaster position="top-right" closeButton theme="system" />
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
);
