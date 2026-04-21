import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Stock To Me",
  description: "SEC filing intelligence for small-cap traders. Monitor dilution risk, financing setups, and pump-before-offering patterns.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
