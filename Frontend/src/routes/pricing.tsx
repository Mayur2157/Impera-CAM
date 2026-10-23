import { createFileRoute, Link } from "@tanstack/react-router";
import { Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PublicFooter, PublicHeader } from "@/components/ledger/brand";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/pricing")({
  head: () => ({
    meta: [
      { title: "Pricing — Impera CAM" },
      { name: "description", content: "Plans for lenders of every size: Starter, Growth and Enterprise." },
      { property: "og:title", content: "Pricing — Impera CAM" },
      { property: "og:description", content: "Plans for lenders of every size: Starter, Growth and Enterprise." },
    ],
  }),
  component: Pricing,
});

const plans = [
  { name: "Starter", for: "DSAs and small co-operative banks", features: ["Up to 3 files per job", "10 MB per file", "Portal access", "Excel export"] },
  { name: "Growth", for: "NBFCs scaling their loan book", features: ["Up to 5 files per job", "25 MB per file", "REST API keys", "Team roles", "GPU OCR for scans"], featured: true },
  { name: "Enterprise", for: "Banks and large NBFCs", features: ["Custom limits & quotas", "Custom retention", "Dedicated OCR capacity", "SSO & audit support"] },
];

function Pricing() {
  return (
    <div className="min-h-screen">
      <PublicHeader />
      <main className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
        <h1 className="font-serif text-4xl font-semibold">Pricing</h1>
        <p className="mt-3 max-w-xl text-muted-foreground">Pricing is tailored to your monthly statement volume. Talk to us for a quote.</p>
        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {plans.map((p) => (
            <div key={p.name} className={cn("flex flex-col rounded-lg border bg-card p-6 shadow-soft", p.featured && "border-primary ring-1 ring-primary")}>
              <h2 className="text-xl font-semibold">{p.name}</h2>
              <p className="mt-1 text-sm text-muted-foreground">{p.for}</p>
              <ul className="mt-6 flex-1 space-y-2 text-sm">
                {p.features.map((f) => <li key={f} className="flex gap-2"><Check className="size-4 text-tie" aria-hidden /> {f}</li>)}
              </ul>
              <Button className="mt-8" variant={p.featured ? "default" : "outline"} asChild>
                <a href="mailto:sales@impera.example">Contact sales</a>
              </Button>
            </div>
          ))}
        </div>
        <p className="mt-10 text-sm text-muted-foreground">Want to try it first? <Link to="/signup" className="text-primary underline underline-offset-4">Create a free trial account</Link>.</p>
      </main>
      <PublicFooter />
    </div>
  );
}
