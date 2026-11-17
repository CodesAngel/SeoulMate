import { connection } from "next/server";
import { redirect } from "next/navigation";
import { defaultWrappedYear } from "@/lib/wrapped";

// /wrapped opens the current Wrapped year (last year until 15 January).
export default async function WrappedIndex() {
  await connection();
  redirect(`/wrapped/${defaultWrappedYear()}`);
}
