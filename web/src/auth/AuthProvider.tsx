import { useCallback, useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { clearToken, getToken, setToken } from "../api/client";
import * as endpoints from "../api/endpoints";
import type { User } from "../api/types";
import { AuthContext } from "./auth-context";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setLoading] = useState(true);
  const queryClient = useQueryClient();

  const logout = useCallback(() => {
    clearToken();
    queryClient.clear();
    setUser(null);
  }, [queryClient]);

  // On mount, if a token exists, resolve the current user. A 401 here triggers
  // the interceptor's "pf-unauthorized" event handled below.
  useEffect(() => {
    let active = true;
    async function bootstrap() {
      if (!getToken()) {
        setLoading(false);
        return;
      }
      try {
        const me = await endpoints.fetchMe();
        if (active) setUser(me);
      } catch {
        if (active) clearToken();
      } finally {
        if (active) setLoading(false);
      }
    }
    bootstrap();
    return () => {
      active = false;
    };
  }, []);

  // A 401 anywhere clears the session and returns to login.
  useEffect(() => {
    const handler = () => {
      queryClient.clear();
      setUser(null);
    };
    window.addEventListener("pf-unauthorized", handler);
    return () => window.removeEventListener("pf-unauthorized", handler);
  }, [queryClient]);

  const login = useCallback(async (username: string, password: string) => {
    const token = await endpoints.login(username, password);
    setToken(token.access_token);
    setUser(await endpoints.fetchMe());
  }, []);

  const signup = useCallback(async (username: string, password: string) => {
    const token = await endpoints.signup(username, password);
    setToken(token.access_token);
    setUser(await endpoints.fetchMe());
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        signup,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
