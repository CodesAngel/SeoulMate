"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { IS_MOCK_MODE } from "@/lib/data-mode";

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
      ? "That sign-in link is invalid or has expired. Please try again."
      : "",
  );

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setMessage("");

    try {
      if (IS_MOCK_MODE) {
        signInMock(email || undefined, displayName.trim() || undefined);
        router.replace("/account");
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
        if (!data.session) {
          setMessage("Check your email to confirm your account.");
          return;
        }
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
      }

      router.replace("/account");
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Authentication failed.");
    } finally {
      setPending(false);
    }
  }

  const signingUp = mode === "signup";
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
