import { createBrowserClient } from "@supabase/ssr";
import type { Database } from "./types";

/**
 * Browser client for use in Client Components. Only ever uses the public
 * anon key — RLS is what keeps this safe, not secrecy of the key.
 */
export function createSupabaseBrowserClient() {
  return createBrowserClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
}
