import { createFileRoute } from "@tanstack/react-router";
import { LegalPage } from "@/components/ledger/legal";

export const Route = createFileRoute("/terms")({
  head: () => ({
    meta: [
      { title: "Terms of Service (draft) — Impera CAM" },
      { name: "description", content: "Terms governing use of the Impera CAM portal and API." },
      { property: "og:title", content: "Terms of Service (draft) — Impera CAM" },
      { property: "og:description", content: "Terms governing use of the Impera CAM portal and API." },
    ],
  }),
  component: () => (
    <LegalPage title="Terms of Service">
      <p>These draft terms govern access to the Impera CAM portal and REST API by lending organisations.</p>
      <h2>Use of the service</h2>
      <p>You confirm you have obtained the borrower's consent to process their bank statements for credit assessment.</p>
      <h2>API keys</h2>
      <p>Keep API keys secret. You are responsible for all requests made with your organisation's keys.</p>
      <h2>No credit decision</h2>
      <p>The CAM is decision support. Final credit decisions remain with the lender.</p>
    </LegalPage>
  ),
});
