import { createFileRoute } from "@tanstack/react-router";
import { LegalPage } from "@/components/ledger/legal";

export const Route = createFileRoute("/privacy")({
  head: () => ({
    meta: [
      { title: "Privacy Policy (draft) — Impera CAM" },
      { name: "description", content: "How Impera CAM processes bank-statement data under India's DPDP Act." },
      { property: "og:title", content: "Privacy Policy (draft) — Impera CAM" },
      { property: "og:description", content: "How Impera CAM processes bank-statement data under India's DPDP Act." },
    ],
  }),
  component: () => (
    <LegalPage title="Privacy Policy">
      <p>This draft describes how Impera CAM processes personal data on behalf of lenders, in line with the Digital Personal Data Protection Act, 2023.</p>
      <h2>What we process</h2>
      <p>Bank-statement PDFs uploaded by our customers, and the account and transaction details extracted from them, solely to produce a Credit Appraisal Memo.</p>
      <h2>Retention</h2>
      <p>Uploaded files and results are deleted automatically after the retention window configured for your organisation.</p>
      <h2>Your rights</h2>
      <p>Data principals may contact the lender that collected their statement, or us, to exercise rights of access, correction and erasure.</p>
    </LegalPage>
  ),
});
