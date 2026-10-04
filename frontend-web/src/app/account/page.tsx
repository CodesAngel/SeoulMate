import { redirect } from "next/navigation";
import { AccountPanel } from "@/components/account-panel";
import { createClient } from "@/lib/supabase/server";

export default async function AccountPage() {
  const supabase = await createClient();
  const { data, error } = await supabase.auth.getClaims();
  if (error || !data?.claims?.sub) redirect("/auth/login");

  const claims = data.claims;
  const email = typeof claims.email === "string" ? claims.email : "Signed-in user";
  const metadata = claims.user_metadata;
  const displayName =
    metadata && typeof metadata === "object" && "display_name" in metadata && typeof metadata.display_name === "string"
      ? metadata.display_name
      : email.split("@")[0];

  return (
    <>
      <section className="page-hero"><div className="shell"><span className="eyebrow">Your account</span><h1 className="display">Welcome, {displayName}</h1><p>Manage your SeoulMate session and continue shaping your K-drama taste.</p></div></section>
      <section className="shell account-page"><AccountPanel email={email} displayName={displayName} /></section>
    </>
  );
}
