import type { Metadata } from "next";
import { ThemeScript } from "@/components/ThemeScript";
import "./globals.css";

export const metadata: Metadata = {
  title: "Wavhost",
  description: "One API for every local model. OpenAI-compatible speech. Named voices saved locally. Open source, Apache-2.0.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <head>
        <ThemeScript />
      </head>
      <body>{children}</body>
    </html>
  );
}
