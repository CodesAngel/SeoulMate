// Plain-language versions of the Supabase Auth errors people actually hit.
export function authErrorMessage(error: unknown, fallback = "Something went wrong. Please try again.") {
  if (!(error instanceof Error)) return fallback;
  const status = "status" in error ? (error as { status?: number }).status : undefined;
  const text = error.message.toLowerCase();
  if (status === 429 || text.includes("rate limit") || text.includes("security purposes")) {
    return "Too many emails were requested. Please wait a minute and try again.";
  }
  if (text.includes("invalid login credentials")) return "That email and password don't match.";
  if (text.includes("email not confirmed")) {
    return "Please confirm your email first. Use the link we sent you, or sign up again to get a new one.";
  }
  if (text.includes("user already registered")) return "An account with this email already exists. Try signing in.";
  if (text.includes("should be different")) return "Choose a password that's different from your old one.";
  if (text.includes("password should be at least")) return "Use at least 8 characters.";
  if (text.includes("auth session missing")) return "This reset link has expired. Please ask for a new one.";
  return error.message || fallback;
}
