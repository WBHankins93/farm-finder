import type { Metadata } from "next";
import { headers } from "next/headers";
import { Geist, Newsreader } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const newsreader = Newsreader({
  variable: "--font-newsreader",
  subsets: ["latin"],
  display: "swap",
});

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const host = requestHeaders.get("x-forwarded-host") || requestHeaders.get("host") || "localhost:3000";
  const protocol = requestHeaders.get("x-forwarded-proto") || (host.startsWith("localhost") ? "http" : "https");
  const metadataBase = new URL(`${protocol}://${host}`);
  const title = "FarmFinder — Find farms across Louisiana & Mississippi";
  const description = "Ask questions, browse products, read detailed profiles, and map 311 independent farms across Louisiana and Mississippi.";

  return {
    metadataBase,
    title,
    description,
    keywords: ["Louisiana farms", "Mississippi farms", "local food", "farmers markets", "CSA", "farm directory"],
    openGraph: {
      title,
      description,
      type: "website",
      images: [{ url: "/og-v2.png", width: 1200, height: 630, alt: "FarmFinder — Who grows what near me? Ask the Gulf South field guide." }],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: ["/og-v2.png"],
    },
  };
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${newsreader.variable}`}>
      <body className="antialiased">{children}</body>
    </html>
  );
}
