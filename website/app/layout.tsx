import type { Metadata } from "next";
import { ThemeScript } from "@/components/ThemeScript";
import "./globals.css";
import { Geist } from "next/font/google";
import { cn } from "@/lib/utils";

const geist = Geist({subsets:['latin'],variable:'--font-sans'});

export const metadata: Metadata = {
  title: "Wavhost",
  description: "One API for every local model. OpenAI-compatible speech. Named voices saved locally. Open source, Apache-2.0.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={cn("font-sans", geist.variable)}>
      <head>
        <ThemeScript />
      </head>
      <body>{children}</body>
    </html>
  );
}
