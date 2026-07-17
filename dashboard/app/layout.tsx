import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Arion Command Deck",
  description:
    "SaaS-grade control deck for the Arion 52-agent company runpack — company brains, teams, gates, and logs.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-display antialiased">
        <div className="aurora-stage" aria-hidden>
          <div className="aurora-blob one" />
          <div className="aurora-blob two" />
          <div className="aurora-blob three" />
        </div>
        <div className="grid-floor" aria-hidden />
        {children}
      </body>
    </html>
  );
}
