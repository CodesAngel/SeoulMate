"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";

export default function UpdatePasswordPage() {
  const router = useRouter();
  const { supabase } = useAuth();
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    const { error } = await supabase.auth.updateUser({ password });
    setPending(false);
    if (error) {
      setMessage(error.message);
      return;
    }
    router.replace("/account");
    router.refresh();
  }

  return (
    <section className="auth-page">
      <div className="auth-card">
        <span className="eyebrow">Account recovery</span>
        <h1 className="display">Choose a new password</h1>
        <p>Use at least eight characters.</p>
        <form className="auth-form" onSubmit={submit}>
          <label><span>New password</span><input type="password" autoComplete="new-password" minLength={8} value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
          <button className="primary-button" type="submit" disabled={pending}>{pending ? "Updating…" : "Update password"}</button>
          {message && <p className="auth-message" role="alert">{message}</p>}
        </form>
      </div>
    </section>
  );
}
