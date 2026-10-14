import type { Metadata } from "next";
import "./globals.css";
import { AuthGate } from "@/components/auth-gate";
import { brand } from "@/lib/brand";

export const metadata: Metadata = {
  title: { default: brand.name, template: `%s | ${brand.name}` },
  applicationName: brand.name,
  description: brand.description,
  icons: { icon: "/icon.svg", shortcut: "/icon.svg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en" className="dark"><body className="bg-background text-foreground antialiased"><AuthGate>{children}</AuthGate></body></html>;
}
