import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthLayout, FieldError } from "@/components/ledger/auth-layout";
import { login } from "@/lib/api/hooks";
import { errorMessage, USE_MOCKS } from "@/lib/api/client";
import { safeNext, useAuth } from "@/lib/auth";

export const Route = createFileRoute("/login")({
  validateSearch: (s: Record<string, unknown>) => ({ next: typeof s["next"] === "string" ? (s["next"] as string) : undefined }),
  head: () => ({
    meta: [
      { title: "Sign in — Impera CAM" },
      { name: "description", content: "Sign in to the Impera CAM portal." },
      { property: "og:title", content: "Sign in — Impera CAM" },
      { property: "og:description", content: "Sign in to the Impera CAM portal." },
    ],
  }),
  component: LoginPage,
});

const schema = z.object({ email: z.string().email("Enter a valid email"), password: z.string().min(1, "Enter your password") });

function LoginPage() {
  const { next } = Route.useSearch();
  const nav = useNavigate();
  const { signIn, token, ready } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema) });

  useEffect(() => {
    if (ready && token) nav({ to: safeNext(next), replace: true });
  }, [ready, token, next, nav]);

  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      const r = await login(v.email, v.password);
      signIn(r.access_token);
    } catch (e) {
      setFormError(errorMessage(e));
    }
  });

  return (
    <AuthLayout title="Sign in" subtitle="Welcome back to your underwriting desk." footer={<>New to Impera CAM? <Link to="/signup" className="font-medium text-primary underline-offset-4 hover:underline">Create an account</Link></>}>
      <form method="post" onSubmit={onSubmit} className="space-y-4" noValidate>
        <div className="space-y-1.5">
          <Label htmlFor="email">Work email</Label>
          <Input id="email" type="email" autoComplete="email" aria-invalid={!!errors.email} aria-describedby="email-err" {...register("email")} />
          <FieldError id="email-err" message={errors.email?.message} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="password">Password</Label>
          <Input id="password" type="password" autoComplete="current-password" aria-invalid={!!errors.password} aria-describedby="pw-err" {...register("password")} />
          <FieldError id="pw-err" message={errors.password?.message} />
        </div>
        {formError && <p role="alert" className="rounded-md border border-break/30 bg-break-soft px-3 py-2 text-sm text-break">{formError}</p>}
        <Button type="submit" className="w-full" disabled={isSubmitting}>{isSubmitting ? "Signing in…" : "Sign in"}</Button>
        {USE_MOCKS && (
          <p className="rounded-md border bg-muted px-3 py-2 text-xs text-muted-foreground">
            Demo mode: <span className="font-mono">demo@impera.test</span> / <span className="font-mono">demo1234</span> (owner) · <span className="font-mono">member@impera.test</span> · <span className="font-mono">staff@impera.test</span>
          </p>
        )}
      </form>
    </AuthLayout>
  );
}
