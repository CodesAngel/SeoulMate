"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useAuth } from "@/components/auth-provider";

export default function ForgotPasswordPage() {
  const { supabase } = useAuth();
  const [email, setEmail] = useState("");
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setMessage("");
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/auth/confirm?next=/auth/update-password`,
    });
    setPending(false);
    setMessage(error ? error.message : "Check your email for the reset link.");
  }

  return (
    <section className="auth-page">
      <div className="auth-card">
        <span className="eyebrow">Account recovery</span>
        <h1 className="display">Reset your password</h1>
        <p>We will send a secure recovery link to your email.</p>
        <form className="auth-form" onSubmit={submit}>
          <label><span>Email</span><input type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
          <button className="primary-button" type="submit" disabled={pending}>{pending ? "Sending…" : "Send reset link"}</button>
          {message && <p className="auth-message" role="status">{message}</p>}
          <p className="auth-switch"><Link href="/auth/login">Back to sign in</Link></p>
        </form>
      </div>
    </section>
  );
}
