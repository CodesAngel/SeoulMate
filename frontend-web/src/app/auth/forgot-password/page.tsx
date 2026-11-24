"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { authErrorMessage } from "@/lib/auth-errors";
import { IS_MOCK_MODE } from "@/lib/data-mode";

function ForgotPasswordForm() {
  const { supabase } = useAuth();
  const searchParams = useSearchParams();
  const linkExpired = searchParams.get("error") === "link_expired";
  const [email, setEmail] = useState("");
  const [pending, setPending] = useState(false);
  const [sentTo, setSentTo] = useState("");
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setMessage("");
    if (IS_MOCK_MODE) {
      await new Promise((resolve) => setTimeout(resolve, 180));
      setPending(false);
      setMessage("Mock recovery email sent. No email service was contacted.");
      return;
    }
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/auth/confirm?next=/auth/update-password`,
    });
    setPending(false);
    if (error) {
      setMessage(authErrorMessage(error));
      return;
    }
    setSentTo(email);
  }

  if (sentTo) {
    return (
      <div className="auth-form auth-sent" role="status">
        <p className="auth-sent-lead">
          If an account exists for <strong>{sentTo}</strong>, a reset link is on its way.
        </p>
        <p className="auth-sent-note">
          It can take a minute to arrive; check your spam or promotions folder too. The link works
          once, on any device. Only the newest link works if you ask more than once.
        </p>
        <p className="auth-switch">
          <button type="button" className="auth-text-button" onClick={() => setSentTo("")}>
            Send it again
          </button>
          {" · "}
          <Link href="/auth/login">Back to sign in</Link>
        </p>
      </div>
    );
  }

  return (
    <form className="auth-form" onSubmit={submit}>
      {linkExpired && (
        <p className="auth-message auth-message-warn" role="alert">
          That reset link has expired or was already used. Enter your email to get a new one.
        </p>
      )}
      <label>
        <span>Email</span>
        <input
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />
      </label>
      <button className="primary-button" type="submit" disabled={pending}>
        {pending ? "Sending…" : "Send reset link"}
      </button>
      {message && <p className="auth-message" role="status">{message}</p>}
      <p className="auth-switch"><Link href="/auth/login">Back to sign in</Link></p>
    </form>
  );
}

export default function ForgotPasswordPage() {
  return (
    <section className="auth-page">
      <div className="auth-card">
        <span className="eyebrow">Account recovery</span>
        <h1 className="display">Reset your password</h1>
        <p>We will send a secure recovery link to your email.</p>
        <Suspense fallback={<p className="muted">Loading…</p>}>
          <ForgotPasswordForm />
        </Suspense>
      </div>
    </section>
  );
}
