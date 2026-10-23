import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, Navigate, useNavigate } from "react-router";
import { z } from "zod";

import { ApiError, request } from "@/api/client";
import type { TokenOut } from "@/api/types";
import { useAuth } from "@/auth/AuthProvider";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Alert } from "@/components/ui/misc";

import { AuthLayout } from "./AuthLayout";
import { PasswordToggle } from "./PasswordToggle";

// mirrors app/auth/schemas.py RegisterIn; the server is the check that counts
const schema = z.object({
  org_name: z.string().trim().min(1, "Enter your organisation's name"),
  email: z
    .string()
    .trim()
    .min(1, "Enter your work email")
    .email("Enter a valid email address, like name@company.com"),
  password: z.string().min(8, "Use at least 8 characters"),
  accept_terms: z.boolean().refine((v) => v, "Tick the box to agree before creating the account"),
});
type Values = z.infer<typeof schema>;
const FIELDS = ["org_name", "email", "password", "accept_terms"] as const;

export function SignupPage() {
  const { status, signIn } = useAuth();
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const { register, handleSubmit, setError, formState } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { org_name: "", email: "", password: "", accept_terms: false },
  });
  const errors = formState.errors;

  if (status === "signed-in") return <Navigate to="/app" replace />;

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      const out = await request<TokenOut>("/api/auth/register", { json: values, auth: false });
      await signIn(out.access_token);
      navigate("/app", { replace: true });
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setError(
          "email",
          { message: "An account already uses this email. Sign in instead." },
          { shouldFocus: true },
        );
        return;
      }
      if (e instanceof ApiError && Object.keys(e.fields).length) {
        for (const f of FIELDS) if (e.fields[f]) setError(f, { message: e.fields[f] }, { shouldFocus: true });
        return;
      }
      setFormError(e instanceof Error ? e.message : "The account couldn't be created. Try again.");
    }
  });

  return (
    <AuthLayout
      title="Create your organisation account"
      subtitle="You'll be the owner and can invite your team later."
      footer={
        <>
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-primary underline-offset-2 hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        {formError && <Alert tone="break">{formError}</Alert>}
        <Field
          label="Organisation name"
          autoComplete="organization"
          error={errors.org_name?.message}
          {...register("org_name")}
        />
        <Field
          label="Work email"
          type="email"
          autoComplete="email"
          error={errors.email?.message}
          {...register("email")}
        />
        <Field
          label="Password"
          type={showPassword ? "text" : "password"}
          autoComplete="new-password"
          hint="At least 8 characters."
          error={errors.password?.message}
          trailing={<PasswordToggle shown={showPassword} onToggle={() => setShowPassword((s) => !s)} />}
          {...register("password")}
        />

        <div className="space-y-1.5">
          <div className="flex items-start gap-3">
            <input
              id="accept_terms"
              type="checkbox"
              className="mt-0.5 size-5 shrink-0 accent-(--primary)"
              aria-invalid={errors.accept_terms ? true : undefined}
              aria-describedby={errors.accept_terms ? "accept_terms-error" : undefined}
              {...register("accept_terms")}
            />
            <label htmlFor="accept_terms" className="text-sm">
              I agree to the{" "}
              <Link
                to="/terms"
                target="_blank"
                rel="noopener"
                className="text-primary underline underline-offset-2"
              >
                terms of service<span className="sr-only"> (opens in a new tab)</span>
              </Link>{" "}
              and consent to Impera CAM processing the statements I upload as the{" "}
              <Link
                to="/privacy"
                target="_blank"
                rel="noopener"
                className="text-primary underline underline-offset-2"
              >
                privacy notice<span className="sr-only"> (opens in a new tab)</span>
              </Link>{" "}
              describes.
            </label>
          </div>
          {errors.accept_terms && (
            <p id="accept_terms-error" className="text-sm text-break">
              {errors.accept_terms.message}
            </p>
          )}
        </div>

        <Button type="submit" className="w-full" loading={formState.isSubmitting}>
          Create account
        </Button>
      </form>
    </AuthLayout>
  );
}
