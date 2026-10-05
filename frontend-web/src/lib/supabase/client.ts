import { createBrowserClient } from "@supabase/ssr";
import { IS_MOCK_MODE } from "@/lib/data-mode";

export function createClient() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
    ?? (IS_MOCK_MODE ? "http://127.0.0.1:54321" : "");
  const publishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
    ?? (IS_MOCK_MODE ? "mock-publishable-key" : "");
  return createBrowserClient(
    supabaseUrl,
    publishableKey,
  );
}
