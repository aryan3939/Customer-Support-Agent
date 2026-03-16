/**
 * useAuth — React hook for Supabase authentication state.
 *
 * Provides:
 *  - user: current Supabase User or null
 *  - session: current Supabase Session or null
 *  - role: "admin" | "customer" extracted from user_metadata
 *  - loading: true while checking initial auth state
 *  - signOut: convenience function to sign out
 */

"use client";

import { useEffect, useState, useCallback } from "react";
import type { User, Session } from "@supabase/supabase-js";
import { getSupabaseBrowserClient } from "@/lib/supabase";

export interface AuthState {
  user: User | null;
  session: Session | null;
  role: "admin" | "customer";
  loading: boolean;
  signOut: () => Promise<void>;
}

export function useAuth(): AuthState {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const supabase = getSupabaseBrowserClient();

    // Get the initial session
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      setSession(s);
      setUser(s?.user ?? null);
      setLoading(false);
    });

    // Listen for auth changes (login, logout, token refresh)
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, s) => {
      setSession(s);
      setUser(s?.user ?? null);
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  const signOut = useCallback(async () => {
    const supabase = getSupabaseBrowserClient();
    await supabase.auth.signOut();
    setUser(null);
    setSession(null);
  }, []);

  const role =
    (user?.user_metadata?.role as "admin" | "customer") ?? "customer";

  return { user, session, role, loading, signOut };
}
