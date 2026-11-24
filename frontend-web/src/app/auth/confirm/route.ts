import type { EmailOtpType } from "@supabase/supabase-js";
import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

// Email links land here. Two kinds are accepted:
// - `?token_hash=…&type=…` (our email templates): checked with verifyOtp, so the
//   link works in any browser or device, not only the one that asked for the email.
// - `?code=…` (Supabase's default links): exchanged for a session; this only works
//   in the browser that started the sign-up or reset, because of the PKCE cookie.
const EMAIL_LINK_TYPES = new Set<EmailOtpType>([
  "signup",
  "email",
  "recovery",
  "email_change",
  "invite",
  "magiclink",
]);

function safePath(value: string | null, fallback: string) {
  return value && value.startsWith("/") && !value.startsWith("//") ? value : fallback;
}

export async function GET(request: Request) {
  const requestUrl = new URL(request.url);
  const code = requestUrl.searchParams.get("code");
  const tokenHash = requestUrl.searchParams.get("token_hash");
  const type = requestUrl.searchParams.get("type") as EmailOtpType | null;
  const isRecovery = type === "recovery";
  const next = safePath(
    requestUrl.searchParams.get("next"),
    isRecovery ? "/auth/update-password" : "/account",
  );
  const redirectTo = (path: string) => NextResponse.redirect(new URL(path, requestUrl.origin));

  const supabase = await createClient();
  if (tokenHash && type && EMAIL_LINK_TYPES.has(type)) {
    const { error } = await supabase.auth.verifyOtp({ token_hash: tokenHash, type });
    if (!error) return redirectTo(next);
  } else if (code) {
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) return redirectTo(next);
  }

  // A used or expired reset link goes back to "Reset your password" so a new one is one click away.
  if (isRecovery || next === "/auth/update-password") {
    return redirectTo("/auth/forgot-password?error=link_expired");
  }
  return redirectTo("/auth/login?error=auth_callback");
}
