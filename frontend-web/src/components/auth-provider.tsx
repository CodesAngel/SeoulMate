"use client";

import type { SupabaseClient, User } from "@supabase/supabase-js";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { createClient } from "@/lib/supabase/client";
import { IS_MOCK_MODE } from "@/lib/data-mode";
import { MOCK_USER_EMAIL, MOCK_USER_ID, MOCK_USER_NAME } from "@/lib/mock-data";

type AuthContextValue = {
  supabase: SupabaseClient;
  user: User | null;
  loading: boolean;
  signOut: () => Promise<void>;
  signInMock: (email?: string, displayName?: string) => void;
  getAccessToken: () => Promise<string | null>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const supabase = useMemo(() => createClient(), []);
  const createMockUser = useCallback((email = MOCK_USER_EMAIL, displayName = MOCK_USER_NAME) => ({
    id: MOCK_USER_ID,
    aud: "authenticated",
    role: "authenticated",
    email,
    created_at: "2026-01-12T09:30:00.000Z",
    app_metadata: { provider: "mock", providers: ["mock"] },
    user_metadata: { display_name: displayName },
  }) as User, []);
  const [user, setUser] = useState<User | null>(() => IS_MOCK_MODE ? createMockUser() : null);
  const [loading, setLoading] = useState(!IS_MOCK_MODE);

  useEffect(() => {
    if (IS_MOCK_MODE) return;
    let active = true;
    void supabase.auth.getUser().then(({ data }) => {
      if (active) {
        setUser(data.user);
        setLoading(false);
      }
    });

    const { data } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      setLoading(false);
    });

    return () => {
      active = false;
      data.subscription.unsubscribe();
    };
  }, [supabase]);

  const signOut = useCallback(async () => {
    if (IS_MOCK_MODE) {
      setUser(null);
      return;
    }
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
  }, [supabase]);

  const getAccessToken = useCallback(async () => {
    if (IS_MOCK_MODE) return user ? "mock-access-token" : null;
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? null;
  }, [supabase, user]);

  const signInMock = useCallback((email?: string, displayName?: string) => {
    if (IS_MOCK_MODE) setUser(createMockUser(email, displayName));
  }, [createMockUser]);

  const value = useMemo(
    () => ({ supabase, user, loading, signOut, signInMock, getAccessToken }),
    [getAccessToken, loading, signInMock, signOut, supabase, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
