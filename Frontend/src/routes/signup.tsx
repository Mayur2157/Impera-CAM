import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { AuthLayout, FieldError } from "@/components/ledger/auth-layout";
import { PasswordStrength } from "@/components/ledger/password-strength";
import { register as registerApi } from "@/lib/api/hooks";
import { errorMessage } from "@/lib/api/client";
import { useAuth } from "@/lib/auth";

export const Route = createFileRoute("/signup")({
  head: () => ({
    meta: [
      { title: "Create an account — Impera CAM" },
      { name: "description", content: "Start turning bank statements into verified CAMs." },
      { property: "og:title", content: "Create an account — Impera CAM" },
      { property: "og:description", content: "Start turning bank statements into verified CAMs." },
    ],
  }),
  component: SignupPage,
});

const schema = z.object({
  org_name: z.string().trim().min(2, "Enter your organisation's name"),
  email: z.string().email("Enter a valid work email"),
  password: z.string().min(8, "Use at least 8 characters"),
  accept: z.literal(true, { errorMap: () => ({ message: "Please accept the Privacy Policy and Terms" }) }),
});

function SignupPage() {
  const nav = useNavigate();
  const { signIn } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);
  const { register, handleSubmit, watch, setValue, formState: { errors, isSubmitting } } = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema), defaultValues: { accept: false as unknown as true },
  });
  const pw = watch("password") ?? "";
  const accept = watch("accept");

  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      const r = await registerApi({ email: v.email, password: v.password, org_name: v.org_name, accept_terms: true });
      signIn(r.access_token);
      nav({ to: "/app" });
    } catch (e) {
      setFormError(errorMessage(e));
    }
  });

  return (
    <AuthLayout title="Create your account" subtitle="Set up your lending organisation in under a minute." footer={<>Already have an account? <Link to="/login" search={{ next: undefined }} className="font-medium text-primary underline-offset-4 hover:underline">Sign in</Link></>}>
      <form method="post" onSubmit={onSubmit} className="space-y-4" noValidate>
        <div className="space-y-1.5">
          <Label htmlFor="org">Organisation name</Label>
          <Input id="org" autoComplete="organization" aria-invalid={!!errors.org_name} aria-describedby="org-err" {...register("org_name")} />
          <FieldError id="org-err" message={errors.org_name?.message} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="email">Work email</Label>
          <Input id="email" type="email" autoComplete="email" aria-invalid={!!errors.email} aria-describedby="email-err" {...register("email")} />
          <FieldError id="email-err" message={errors.email?.message} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="password">Password</Label>
          <Input id="password" type="password" autoComplete="new-password" aria-invalid={!!errors.password} aria-describedby="pw-strength pw-err" {...register("password")} />
          <PasswordStrength id="pw-strength" value={pw} />
          <FieldError id="pw-err" message={errors.password?.message} />
        </div>
        <div className="flex items-start gap-2.5">
          <Checkbox id="accept" checked={!!accept} onCheckedChange={(c) => setValue("accept", (c === true) as true, { shouldValidate: true })} aria-describedby="accept-err" className="mt-0.5" />
          <Label htmlFor="accept" className="text-sm font-normal leading-snug">
            I agree to the <Link to="/privacy" className="text-primary underline underline-offset-4">Privacy Policy</Link> and <Link to="/terms" className="text-primary underline underline-offset-4">Terms of Service</Link>, and consent to processing of statement data as described.
          </Label>
        </div>
        <FieldError id="accept-err" message={errors.accept?.message} />
        {formError && <p role="alert" className="rounded-md border border-break/30 bg-break-soft px-3 py-2 text-sm text-break">{formError}</p>}
        <Button type="submit" className="w-full" disabled={isSubmitting}>{isSubmitting ? "Creating account…" : "Create account"}</Button>
      </form>
    </AuthLayout>
  );
}
