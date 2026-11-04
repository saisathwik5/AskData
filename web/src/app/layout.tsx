import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AskData | Guarded AI Analytics",
  description: "Enterprise conversational Text-to-SQL platform powered by AST Query Guard.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased text-slate-900 bg-slate-50 font-sans">
        {children}
      </body>
    </html>
  );
}
