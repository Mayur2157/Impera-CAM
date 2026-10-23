import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router";
import { z } from "zod";

import { ApiError, request } from "@/api/client";
import type { TokenOut } from "@/api/types";
import { useAuth } from "@/auth/AuthProvider";
import { safeNext } from "@/auth/next";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Alert } from "@/components/ui/misc";

import { AuthLayout } from "./AuthLayout";
import { PasswordToggle } from "./PasswordToggle";

const schema = z.object({
  email: z
    .string()
    .trim()
    .min(1, "Enter your email address")
    .email("Enter a valid email address, like name@company.com"),
  password: z.string().min(1, "Enter your password"),
});
type Values = z.infer<typeof schema>;

export function LoginPage() {
  const { status, signIn } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));
  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const { register, handleSubmit, formState } = useForm<Values>({ resolver: zodResolver(schema) });

  if (status === "signed-in") return <Navigate to={next} replace />;

  const onSubmit = handleSubmit(async ({ email, password }) => {
    setFormError(null);
    try {
      const out = await request<TokenOut>("/api/auth/login", {
        form: new URLSearchParams({ username: email, password }),
        auth: false,
      });
      await signIn(out.access_token);
      navigate(next, { replace: true });
    } catch (e) {
      setFormError(
        e instanceof ApiError && e.status === 401
          ? "That email and password don't match an account. Check them and try again."
          : e instanceof Error
            ? e.message
            : "Sign-in failed. Try again.",
      );
    }
  });

  return (
    <AuthLayout
      title="Sign in"
      subtitle="Bank statement analysis and CAM reports for your credit team."
      footer={
        <>
          New to Impera CAM?{" "}
          <Link to="/signup" className="font-medium text-primary underline-offset-2 hover:underline">
            Create an organisation account
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        {formError && <Alert tone="break">{formError}</Alert>}
        <Field
          label="Email"
          type="email"
          autoComplete="username"
          error={formState.errors.email?.message}
          {...register("email")}
        />
        <Field
          label="Password"
          type={showPassword ? "text" : "password"}
          autoComplete="current-password"
          error={formState.errors.password?.message}
          trailing={<PasswordToggle shown={showPassword} onToggle={() => setShowPassword((s) => !s)} />}
          {...register("password")}
        />
        <Button type="submit" className="w-full" loading={formState.isSubmitting}>
          Sign in
        </Button>
      </form>
    </AuthLayout>
  );
}
