import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { geistSans, geistMono, jakarta } from "@/lib/fonts";

export const metadata: Metadata = {
  title: "Multi-Agent Financial System",
  description: "AI-driven stock analysis powered by a team of agents.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${jakarta.variable} h-full antialiased dark`}
    >
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
