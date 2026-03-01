"use client";

import { useUser } from "@clerk/nextjs";
import Sidebar from "@/components/Sidebar";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { isSignedIn, isLoaded } = useUser();

  if (!isLoaded) return null;

  // Unauthenticated: full-width, no sidebar
  if (!isSignedIn) {
    return <>{children}</>;
  }

  // Authenticated: sidebar + content layout
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </div>
      </main>
    </div>
  );
}
