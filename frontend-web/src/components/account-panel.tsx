"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { LogOut } from "lucide-react";
import { useAuth } from "@/components/auth-provider";

export function AccountPanel({ email, displayName }: { email: string; displayName: string }) {
  const router = useRouter();
  const { signOut } = useAuth();
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");

  async function logout() {
    setPending(true);
    setMessage("");
    try {
      await signOut();
      router.replace("/");
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not sign out.");
      setPending(false);
    }
  }

  return (
    <div className="account-card">
      <div className="account-avatar" aria-hidden="true">{displayName.charAt(0).toUpperCase()}</div>
      <div>
        <span className="eyebrow">Signed in</span>
        <h2>{displayName}</h2>
        <p>{email}</p>
      </div>
      <button className="secondary-button account-logout" type="button" onClick={logout} disabled={pending}>
        <LogOut size={17} /> {pending ? "Signing out…" : "Sign out"}
      </button>
      {message && <p className="auth-message" role="alert">{message}</p>}
    </div>
  );
}
