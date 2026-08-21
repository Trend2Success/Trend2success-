import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Lead Rescue AI",
  description: "Turn missed calls and web leads into booked appointments.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
