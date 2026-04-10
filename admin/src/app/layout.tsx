import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";
import AuthProvider from "@/components/AuthProvider";
import Sidebar from "@/components/Sidebar";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "EduScan Admin",
  description: "Admin panel for EduScan — manage users, exams, and questions.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body className={`${inter.variable} font-sans antialiased`}>
          <AuthProvider>
            <div className="flex min-h-screen">
              <Sidebar />
              <main className="flex-1 p-6 lg:p-8 overflow-auto">{children}</main>
            </div>
          </AuthProvider>
        </body>
      </html>
    </ClerkProvider>
  );
}
