import { Suspense } from "react";
import { AuthForm } from "@/components/auth-form";

export default function SignUpPage() {
  return (
    <section className="auth-page">
      <div className="auth-card">
        <span className="eyebrow">Your watch journey</span>
        <h1 className="display">Create your account</h1>
        <p>Keep your identity connected while SeoulMate learns your taste.</p>
        <Suspense fallback={<p className="muted">Loading…</p>}>
          <AuthForm mode="signup" />
        </Suspense>
      </div>
    </section>
  );
}
