import type { ReactNode } from "react";
import { Link } from "react-router";

import { Brand } from "@/components/Brand";
import { Alert } from "@/components/ui/misc";

// DRAFT wording for legal review. Keep the version and date in step with any
// change, and never describe the product as "DPDP compliant" here.
const NOTICE_VERSION = "draft-2026-10-23";

function LegalLayout({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <Link to="/login" aria-label="Impera CAM — sign in">
        <Brand />
      </Link>
      <main className="mt-8 space-y-5 leading-relaxed [&_h2]:mt-8 [&_h2]:text-lg [&_h2]:font-semibold [&_li]:ml-5 [&_li]:list-disc">
        <h1 className="text-2xl font-semibold">{title}</h1>
        <Alert tone="warn" title="Draft">
          This text is a draft awaiting legal review (version {NOTICE_VERSION}). It describes what the
          software does today.
        </Alert>
        {children}
      </main>
    </div>
  );
}

export function PrivacyPage() {
  return (
    <LegalLayout title="Privacy notice">
      <h2>What we collect, and why</h2>
      <ul>
        <li>
          <strong>Your account:</strong> your email address, organisation name and a hashed password — to sign
          you in and keep your organisation's work separate from everyone else's.
        </li>
        <li>
          <strong>Bank statements you upload</strong> and the details printed on them (account holder, account
          number, transactions) — only to produce the credit analysis and Excel workbook you asked for.
        </li>
        <li>
          <strong>Usage records:</strong> how many statements and pages your organisation processed, and when
          — to show usage against your plan.
        </li>
      </ul>
      <h2>How long we keep it</h2>
      <ul>
        <li>
          Uploaded PDFs, the generated workbooks and analyses are deleted automatically after your
          organisation's retention period (6 hours by default).
        </li>
        <li>
          To link statements of the same borrower, the account holder's name, account number and contact
          details printed on a statement are kept in a registry private to your organisation. They are not yet
          deleted automatically.
        </li>
        <li>Usage records are kept for billing. Your account stays until it is closed.</li>
      </ul>
      <h2>What we show and share</h2>
      <ul>
        <li>Account numbers are masked on screen and in the API, except the last four digits.</li>
        <li>
          We don't sell data or use it for advertising. Statements are not sent to any outside AI service.
        </li>
      </ul>
      <h2>Your rights</h2>
      <p>
        You can ask to see, correct or erase your personal data, withdraw consent, or raise a grievance. Until
        these requests are available in the product, contact your Impera CAM account manager.
      </p>
    </LegalLayout>
  );
}

export function TermsPage() {
  return (
    <LegalLayout title="Terms of service">
      <p>
        Impera CAM reads bank statements you are authorised to process and produces a credit assessment to
        support — not replace — your own credit decision. Check every result before relying on it: the balance
        check shows how much of each statement was verified.
      </p>
      <p>
        You are responsible for having the borrower's permission to upload their statements, for the accounts
        in your organisation, and for keeping API keys secret.
      </p>
    </LegalLayout>
  );
}
