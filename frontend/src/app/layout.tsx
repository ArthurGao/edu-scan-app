import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import "mathlive/fonts.css";
import "./globals.css";
import AuthProvider from "@/components/AuthProvider";
import AppShell from "@/components/AppShell";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "EduScan - AI Homework Helper",
  description:
    "AI-powered homework helper for K12 students. Upload a photo of your homework and get step-by-step solutions.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body className={`${inter.variable} font-sans antialiased`}>
          <AuthProvider>
            <AppShell>{children}</AppShell>
          </AuthProvider>
        </body>
      </html>
    </ClerkProvider>
  );
}
