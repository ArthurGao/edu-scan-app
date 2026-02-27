import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

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
    <html lang="en">
      <body className={`${inter.variable} font-sans antialiased`}>
        <div className="flex h-screen overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-y-auto">
            <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
