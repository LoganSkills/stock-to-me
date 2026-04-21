"use client";

import { useState } from "react";
import { api, setTokenGetter } from "@/lib/api";
import { useRouter } from "next/navigation";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}

export function useAuth() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  const login = async (email: string, password: string) => {
    setLoading(true);
    try {
      const res = await api.login(email, password);
      if (res.access_token) {
        localStorage.setItem("token", res.access_token);
        setTokenGetter(() => Promise.resolve(res.access_token));
        router.push("/dashboard");
      } else {
        throw new Error(res.detail || "Login failed");
      }
    } finally {
      setLoading(false);
    }
  };

  const register = async (email: string, password: string) => {
    setLoading(true);
    try {
      await api.register(email, password);
      await login(email, password);
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem("token");
    setTokenGetter(() => Promise.resolve(null));
    router.push("/login");
  };

  return { login, register, logout, loading };
}
