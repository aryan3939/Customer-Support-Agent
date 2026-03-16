/**
 * Supabase browser client — used in client components for auth.
 *
 * Creates a singleton Supabase client configured for the browser
 * (session stored in cookies via @supabase/ssr).
 */

import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";

let client: SupabaseClient | null = null;

export function getSupabaseBrowserClient(): SupabaseClient {
  if (client) return client;

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !anonKey) {
    throw new Error(
      "Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY. " +
        "Set SUPABASE_URL and SUPABASE_ANON_KEY in the root .env file."
    );
  }

  client = createBrowserClient(url, anonKey);
  return client;
}
