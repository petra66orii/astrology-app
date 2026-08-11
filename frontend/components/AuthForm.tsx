"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { apiMutation } from "@/lib/api";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      await apiMutation(`/auth/${mode}/`, "POST", { email: form.get("email"), password: form.get("password") });
      router.push("/dashboard");
      router.refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to continue.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card formCard" onSubmit={submit}>
      <label>Email<input name="email" type="email" autoComplete="email" required /></label>
      <label>Password<input name="password" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} minLength={10} required /></label>
      {error && <p className="error" role="alert">{error}</p>}
      <button className="button" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}</button>
      <p className="muted">{mode === "login" ? <>New here? <Link href="/register">Create an account</Link></> : <>Already registered? <Link href="/login">Sign in</Link></>}</p>
    </form>
  );
}
