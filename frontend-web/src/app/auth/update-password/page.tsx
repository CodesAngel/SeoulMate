"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import { authErrorMessage } from "@/lib/auth-errors";
import { IS_MOCK_MODE } from "@/lib/data-mode";

export default function UpdatePasswordPage() {
  const router = useRouter();
  const { supabase, user, loading } = useAuth();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  const [done, setDone] = useState(false);

  // After success, show the confirmation briefly, then go to the account page.
  useEffect(() => {
    if (!done) return;
    const timer = setTimeout(() => {
      router.replace("/account");
      router.refresh();
    }, 1800);
    return () => clearTimeout(timer);
  }, [done, router]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    if (password !== confirm) {
      setMessage("The two passwords don't match.");
      return;
    }
    setPending(true);
    if (IS_MOCK_MODE) {
      await new Promise((resolve) => setTimeout(resolve, 180));
      setPending(false);
      setDone(true);
      return;
    }
    const { error } = await supabase.auth.updateUser({ password });
    setPending(false);
    if (error) {
      setMessage(authErrorMessage(error));
      return;
    }
    setDone(true);
  }

  let body;
  if (!IS_MOCK_MODE && loading) {
    body = <p className="muted">Checking your reset link…</p>;
  } else if (!IS_MOCK_MODE && !user && !done) {
    // Opened without a valid link (expired, already used, or typed in by hand).
    body = (
      <div className="auth-form">
        <p className="auth-message auth-message-warn" role="alert">
          This reset link has expired or was already used.
        </p>
        <Link className="primary-button auth-button-link" href="/auth/forgot-password">
          Get a new reset link
        </Link>
        <p className="auth-switch"><Link href="/auth/login">Back to sign in</Link></p>
      </div>
    );
  } else if (done) {
    body = (
      <p className="auth-message auth-message-ok" role="status">
        Your password has been changed. Taking you to your account…
      </p>
    );
  } else {
    body = (
      <form className="auth-form" onSubmit={submit}>
        {user?.email && (
          <p className="auth-sent-note">
            Changing the password for <strong>{user.email}</strong>.
          </p>
        )}
        <label>
          <span>New password</span>
          <input
            type="password"
            autoComplete="new-password"
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        <label>
          <span>Repeat new password</span>
          <input
            type="password"
            autoComplete="new-password"
            minLength={8}
            value={confirm}
            onChange={(event) => setConfirm(event.target.value)}
            required
          />
        </label>
        <button className="primary-button" type="submit" disabled={pending}>
          {pending ? "Updating…" : "Update password"}
        </button>
        {message && <p className="auth-message" role="alert">{message}</p>}
      </form>
    );
  }

  return (
    <section className="auth-page">
      <div className="auth-card">
        <span className="eyebrow">Account recovery</span>
        <h1 className="display">Choose a new password</h1>
        <p>Use at least eight characters.</p>
        {body}
      </div>
    </section>
  );
}
