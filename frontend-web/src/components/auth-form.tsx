"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { authErrorMessage } from "@/lib/auth-errors";
import { IS_MOCK_MODE } from "@/lib/data-mode";

// Supabase lets the same address get a new confirmation email once a minute.
const RESEND_WAIT_MS = 60_000;

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { supabase, signInMock } = useAuth();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState(
    searchParams.get("error") === "auth_callback"
      ? "That link is invalid or has expired. If you were confirming your email, sign in or sign up again to get a new link."
      : "",
  );
  // After sign-up: the address the confirmation went to, and when "Resend" unlocks.
  const [sentTo, setSentTo] = useState("");
  const [cooldownUntil, setCooldownUntil] = useState(0);
  const [now, setNow] = useState(() => Date.now());

  function startCooldown() {
    const start = Date.now();
    setNow(start);
    setCooldownUntil(start + RESEND_WAIT_MS);
  }

  useEffect(() => {
    if (cooldownUntil <= Date.now()) return;
    const timer = setInterval(() => {
      setNow(Date.now());
      if (Date.now() >= cooldownUntil) clearInterval(timer);
    }, 1000);
    return () => clearInterval(timer);
  }, [cooldownUntil]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setMessage("");

    try {
      const returnUrl = searchParams.get("returnUrl") || "/account";
      if (IS_MOCK_MODE) {
        signInMock(email || undefined, displayName.trim() || undefined);
        router.replace(returnUrl);
        router.refresh();
        return;
      }
      if (mode === "signup") {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: { display_name: displayName.trim() },
            emailRedirectTo: `${window.location.origin}/auth/confirm`,
          },
        });
        if (error) throw error;
        // Supabase answers a sign-up for an existing, confirmed email with a user that has no identities.
        if (data.user && data.user.identities?.length === 0) {
          setMessage("An account with this email already exists. Try signing in, or reset your password.");
          return;
        }
        if (!data.session) {
          setSentTo(email);
          startCooldown();
          return;
        }
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
      }

      router.replace(returnUrl);
      router.refresh();
    } catch (error) {
      setMessage(authErrorMessage(error, "Authentication failed."));
    } finally {
      setPending(false);
    }
  }

  async function resend() {
    if (!sentTo) return;
    setPending(true);
    setMessage("");
    const { error } = await supabase.auth.resend({
      type: "signup",
      email: sentTo,
      options: { emailRedirectTo: `${window.location.origin}/auth/confirm` },
    });
    setPending(false);
    if (error) {
      setMessage(authErrorMessage(error));
      return;
    }
    startCooldown();
    setMessage("A new confirmation email is on its way.");
  }

  const signingUp = mode === "signup";

  if (signingUp && sentTo) {
    const waitSeconds = Math.max(0, Math.ceil((cooldownUntil - now) / 1000));
    return (
      <div className="auth-form auth-sent" role="status">
        <p className="auth-sent-lead">
          We sent a confirmation link to <strong>{sentTo}</strong>.
        </p>
        <p className="auth-sent-note">
          Open it to finish creating your account. It can take a minute to arrive; check your spam
          or promotions folder too. The link works on any device.
        </p>
        <button
          className="secondary-button"
          type="button"
          onClick={resend}
          disabled={pending || waitSeconds > 0}
        >
          {pending ? "Sending…" : waitSeconds > 0 ? `Resend email in ${waitSeconds}s` : "Resend email"}
        </button>
        {message && <p className="auth-message">{message}</p>}
        <p className="auth-switch">
          Wrong email?{" "}
          <button
            type="button"
            className="auth-text-button"
            onClick={() => {
              setSentTo("");
              setMessage("");
            }}
          >
            Start again
          </button>
        </p>
      </div>
    );
  }

  return (
    <form className="auth-form" onSubmit={submit}>
      {signingUp && (
        <label>
          <span>Display name</span>
          <input
            name="displayName"
            autoComplete="name"
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
            maxLength={100}
            required
          />
        </label>
      )}
      <label>
        <span>Email</span>
        <input
          type="email"
          name="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />
      </label>
      <label>
        <span>Password</span>
        <input
          type="password"
          name="password"
          autoComplete={signingUp ? "new-password" : "current-password"}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          minLength={8}
          required
        />
      </label>
      {!signingUp && (
        <Link className="auth-small-link" href="/auth/forgot-password">
          Forgot your password?
        </Link>
      )}
      <button className="primary-button" type="submit" disabled={pending}>
        {pending ? "Please wait…" : signingUp ? "Create account" : "Sign in"}
      </button>
      {message && <p className="auth-message" role="status">{message}</p>}
      <p className="auth-switch">
        {signingUp ? "Already have an account?" : "New to SeoulMate?"}{" "}
        <Link href={signingUp ? "/auth/login" : "/auth/sign-up"}>
          {signingUp ? "Sign in" : "Create an account"}
        </Link>
      </p>
    </form>
  );
}
