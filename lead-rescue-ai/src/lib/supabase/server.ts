import { cookies } from "next/headers";
import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { createClient } from "@supabase/supabase-js";
import type { Database } from "./types";

/**
 * Server Component / Route Handler client. Runs as the signed-in user and
 * is subject to RLS, so it's the right choice for anything rendered on
 * behalf of a logged-in tenant user.
 */
export async function createSupabaseServerClient() {
  const cookieStore = await cookies();

  return createServerClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet: { name: string; value: string; options: CookieOptions }[]) {
          for (const { name, value, options } of cookiesToSet) {
            cookieStore.set(name, value, options);
          }
        },
      },
    },
  );
}

/**
 * Service-role client. Bypasses RLS entirely, so it must only be used from
 * trusted server code (webhook handlers, background jobs) that does its own
 * tenant-scoping in the query — never from a code path that echoes a
 * caller-supplied tenant_id without verifying it first. Never import this
 * from a Client Component or expose SUPABASE_SERVICE_ROLE_KEY to the browser.
 */
export function createSupabaseServiceRoleClient() {
  return createClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false } },
  );
}
