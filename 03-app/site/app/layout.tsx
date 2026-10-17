import type { Metadata } from "next";
import { headers } from "next/headers";
import { Fraunces, Baloo_2, DM_Sans } from "next/font/google";
import "./globals.css";

/*
 * Market Stand type, revised 2026-10-11 on the owner's reference set: Sauce TM,
 * Indigo Sky (Fenotype), Mochi Boom and Peanut Donuts. All four are commercial
 * display faces and none can ship here, but they share one unmistakable DNA —
 * chunky, rounded, retro, the lettering of a food shop. Three are bubble faces;
 * the fourth is a plush rounded serif. This pairing rebuilds that character
 * from open-licensed faces.
 *
 * This reverses the earlier "no display serif" decision, deliberately and at
 * the owner's instruction. Plus Jakarta Sans was a well-made geometric sans
 * with no point of view, which is most of why the product read as careful
 * rather than characterful.
 *
 * Fraunces carries the Indigo Sky role. Its SOFT axis plumps the serifs and
 * WONK swaps in the canted, slightly off letterforms, which is exactly the
 * retro-psychedelic wobble those references trade on — and unlike a bubble
 * face it is still a reading font at 19px, which matters when it is setting
 * five hundred farm names.
 */
const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  axes: ["SOFT", "WONK", "opsz"],
  display: "swap",
});

/*
 * Baloo 2 carries the Mochi Boom / Peanut Donuts / Sauce TM role: soft, round
 * and chunky. It is deliberately confined to numerals and very short labels —
 * counts, badges, step markers. A bubble face is a delight on "17,346" and a
 * liability on a paragraph.
 */
const baloo = Baloo_2({
  variable: "--font-baloo",
  subsets: ["latin"],
  weight: ["600", "700", "800"],
  display: "swap",
});

const dmSans = DM_Sans({
  variable: "--font-dm-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const host = requestHeaders.get("x-forwarded-host") || requestHeaders.get("host") || "localhost:3000";
  const protocol = requestHeaders.get("x-forwarded-proto") || (host.startsWith("localhost") ? "http" : "https");
  const metadataBase = new URL(`${protocol}://${host}`);
  const title = "FarmFinder — Find the farms behind your food";
  const description = "Find local farms near you across all 50 states — see what they grow, raise, catch, and make, and the confirmed way to buy from each one.";

  return {
    metadataBase,
    title,
    description,
    keywords: ["United States farm directory", "Louisiana farms", "Mississippi farms", "local food", "farmers markets", "CSA", "farm directory"],
    openGraph: {
      title,
      description,
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
    },
  };
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${dmSans.variable} ${fraunces.variable} ${baloo.variable}`}>
      <body className="antialiased">{children}</body>
    </html>
  );
}
