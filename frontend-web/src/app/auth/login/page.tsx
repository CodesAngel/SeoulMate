import { Suspense } from "react";
import { AuthForm } from "@/components/auth-form";

export default function LoginPage() {
  return (
    <section className="auth-page">
      <div className="auth-card">
        <span className="eyebrow">Welcome back</span>
        <h1 className="display">Sign in to SeoulMate</h1>
        <p>Keep your account and taste profile connected across sessions.</p>
        <Suspense fallback={<p className="muted">Loading…</p>}>
          <AuthForm mode="login" />
        </Suspense>
      </div>
    </section>
  );
}
