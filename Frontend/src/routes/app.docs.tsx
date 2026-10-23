import { createFileRoute, Link } from "@tanstack/react-router";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageHeader } from "@/components/ledger/states";
import { CodeBlock } from "@/components/ledger/code";
import { useOrg } from "@/lib/api/hooks";
import { API_BASE_DISPLAY, ENDPOINTS, ERROR_CODES, LANGS, SNIPPETS } from "@/lib/api/snippets";
import { formatNumber } from "@/lib/format";

export const Route = createFileRoute("/app/docs")({
  head: () => ({ meta: [{ title: "API docs — Impera CAM" }, { name: "description", content: "Quickstart, code samples and reference for the Impera CAM REST API." }] }),
  component: DocsPage,
});

const SECTIONS = [["quickstart", "Quickstart"], ["samples", "Code samples"], ["reference", "Reference"], ["errors", "Errors"], ["limits", "Limits & retention"], ["security", "Security"]] as const;

function DocsPage() {
  return (
    <>
      <PageHeader
        title="API documentation"
        description={<>Base URL <span className="font-mono">{API_BASE_DISPLAY}</span>. Authenticate every request with the <span className="font-mono">X-API-Key</span> header.</>}
        actions={<><Button asChild variant="outline"><Link to="/app/playground">Try it in the playground</Link></Button><Button asChild><Link to="/app/api-keys">Get API key</Link></Button></>}
      />
      <div className="grid grid-cols-[minmax(0,1fr)] gap-10 lg:grid-cols-[180px_minmax(0,1fr)]">
        <nav aria-label="On this page" className="hidden lg:block">
          <ul className="sticky top-6 space-y-1 text-sm">
            {SECTIONS.map(([id, l]) => <li key={id}><a href={`#${id}`} className="block rounded px-2 py-1 text-muted-foreground hover:bg-muted hover:text-foreground">{l}</a></li>)}
          </ul>
        </nav>
        <div className="min-w-0 space-y-14">
          <section id="quickstart" aria-labelledby="h-qs">
            <H id="h-qs">Quickstart</H>
            <ol className="grid gap-3 sm:grid-cols-2">
              {[
                ["Create a key", <>An owner or admin creates a key on <Link to="/app/api-keys" className="underline">API keys</Link> with <span className="font-mono">jobs:write</span> and <span className="font-mono">jobs:read</span>.</>],
                ["Upload", <><span className="font-mono">POST /api/v1/jobs</span> with the PDF as <span className="font-mono">files[]</span>. You get a <span className="font-mono">job_id</span>.</>],
                ["Poll", <><span className="font-mono">GET /api/v1/jobs/{"{job_id}"}</span> every 2–10 s until status is <span className="font-mono">done</span> or <span className="font-mono">error</span>.</>],
                ["Fetch the result", <><span className="font-mono">GET …/files/{"{index}"}/result</span> for the CAM JSON, or <span className="font-mono">…/download</span> for Excel.</>],
              ].map(([t, d], i) => (
                <li key={i} className="rounded-lg border bg-card p-4">
                  <div className="mb-1 flex items-center gap-2"><span className="flex size-6 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground tabular-nums">{i + 1}</span><span className="font-medium">{t}</span></div>
                  <p className="text-sm text-muted-foreground">{d}</p>
                </li>
              ))}
            </ol>
          </section>

          <section id="samples" aria-labelledby="h-s">
            <H id="h-s">Code samples</H>
            <p className="mb-4 text-sm text-muted-foreground">Upload, poll with backoff (honouring <span className="font-mono">Retry-After</span>), fetch the CamResult and download the workbook.</p>
            <Tabs defaultValue="curl">
              <TabsList>{LANGS.map((l) => <TabsTrigger key={l.id} value={l.id}>{l.label}</TabsTrigger>)}</TabsList>
              {LANGS.map((l) => <TabsContent key={l.id} value={l.id}><CodeBlock code={SNIPPETS[l.id]} label={l.label} /></TabsContent>)}
            </Tabs>
          </section>

          <section id="reference" aria-labelledby="h-r" className="space-y-6">
            <H id="h-r">Reference</H>
            {ENDPOINTS.map((e) => (
              <article key={e.method + e.path} className="min-w-0 rounded-lg border bg-card p-5" aria-label={`${e.method} ${e.path}`}>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge className="font-mono">{e.method}</Badge>
                  <code className="font-mono text-sm break-all">{e.path}</code>
                  <Badge variant="secondary" className="ml-auto font-mono text-[11px] font-normal">{e.scope}</Badge>
                </div>
                <p className="mt-2 text-sm">{e.summary}</p>
                {e.params && (
                  <table className="mt-4 w-full text-sm">
                    <caption className="sr-only">Parameters</caption>
                    <thead><tr className="border-b text-left text-xs text-muted-foreground"><th className="py-1.5 pr-3 font-medium">Parameter</th><th className="py-1.5 pr-3 font-medium">In</th><th className="py-1.5 font-medium">Description</th></tr></thead>
                    <tbody>{e.params.map((p) => <tr key={p.name} className="border-b last:border-0"><td className="py-1.5 pr-3 font-mono text-xs">{p.name}</td><td className="py-1.5 pr-3 text-muted-foreground">{p.where}</td><td className="py-1.5">{p.desc}</td></tr>)}</tbody>
                  </table>
                )}
                <div className="mt-4 grid grid-cols-[minmax(0,1fr)] gap-3 xl:grid-cols-2">
                  <CodeBlock code={e.request} label="Request" />
                  <CodeBlock code={e.response} label="Response" />
                </div>
                <p className="mt-3 text-xs text-muted-foreground">Errors: {e.errors.map((c) => <a key={c} href="#errors" className="mr-2 font-mono underline-offset-2 hover:underline">{c}</a>)}</p>
              </article>
            ))}
          </section>

          <section id="errors" aria-labelledby="h-e">
            <H id="h-e">Error codes</H>
            <dl className="divide-y rounded-lg border bg-card">
              {Object.entries(ERROR_CODES).map(([c, d]) => <div key={c} className="grid grid-cols-[4rem_1fr] gap-3 p-3 text-sm"><dt className="font-mono">{c}</dt><dd>{d}</dd></div>)}
            </dl>
            <p className="mt-3 text-sm text-muted-foreground">Error bodies are JSON with a human-readable <span className="font-mono">detail</span> message. On 429, wait the number of seconds in <span className="font-mono">Retry-After</span>.</p>
          </section>

          <section id="limits" aria-labelledby="h-l"><H id="h-l">Limits & retention</H><Limits /></section>

          <section id="security" aria-labelledby="h-sec">
            <H id="h-sec">Security best practices</H>
            <ul className="list-disc space-y-2 pl-5 text-sm">
              <li><strong>Keep keys server-side.</strong> Never put a key in a browser, mobile app, or public repository.</li>
              <li><strong>One key per system.</strong> Name it after the system so you know what a revoke will affect.</li>
              <li><strong>Least privilege.</strong> Give a key only the scopes it needs — read-only reporting needs only <span className="font-mono">jobs:read</span>.</li>
              <li><strong>Rotate regularly.</strong> Create the new key, deploy it, then revoke the old one.</li>
              <li><strong>Revoke on leak.</strong> If a key may have been exposed, revoke it at once — it stops working immediately.</li>
              <li><strong>Don't log personal data.</strong> Statements contain borrower data; keep it out of your logs and URLs.</li>
            </ul>
          </section>
        </div>
      </div>
    </>
  );
}

function H({ id, children }: { id: string; children: React.ReactNode }) {
  return <h2 id={id} className="mb-4 font-serif text-2xl font-semibold tracking-tight">{children}</h2>;
}

function Limits() {
  const org = useOrg();
  if (org.isLoading) return <Skeleton className="h-24" />;
  if (!org.data) return <p className="text-sm text-muted-foreground">Your plan limits couldn't be loaded.</p>;
  const o = org.data;
  const items = [
    ["Plan", o.plan], ["Files per job", formatNumber(o.max_files)], ["Max file size", `${formatNumber(o.max_upload_mb)} MB`],
    ["Results kept for", `${formatNumber(o.retention_hours)} hours`],
  ];
  return (
    <>
      <dl className="grid gap-3 sm:grid-cols-4">{items.map(([k, v]) => <div key={k} className="rounded-lg border bg-card p-4"><dt className="text-xs text-muted-foreground">{k}</dt><dd className="mt-1 text-lg font-semibold tabular-nums">{v}</dd></div>)}</dl>
      <p className="mt-3 text-sm text-muted-foreground">After the retention period, result endpoints return <span className="font-mono">410</span> and the PDF and parsed data are deleted. Upload again if you need the result later.</p>
    </>
  );
}
