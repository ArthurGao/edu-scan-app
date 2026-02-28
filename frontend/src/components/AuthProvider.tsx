"use client";

import { useAuth } from "@clerk/nextjs";
import { useEffect } from "react";
import { setAuthTokenProvider } from "@/lib/api";

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const { getToken } = useAuth();

  useEffect(() => {
    setAuthTokenProvider(() => getToken());
  }, [getToken]);

  return <>{children}</>;
}
