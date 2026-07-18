import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/Nav";

export const metadata: Metadata = {
  title: "CodeAtlas",
  description:
    "Chat with your codebase — grounded answers with exact file paths and line ranges.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-paper text-ink antialiased">
        <div className="flex min-h-screen">
          <aside className="flex w-52 shrink-0 flex-col border-r border-line bg-panel px-5 py-6">
            <div className="mb-8">
              <span className="font-display text-xl font-semibold tracking-tight">
                Code<span className="text-accent">Atlas</span>
              </span>
              <p className="mt-1 text-xs leading-snug text-ink-soft">
                Chat with your codebase
              </p>
            </div>
            <Nav />
            <p className="mt-auto text-[11px] leading-relaxed text-ink-soft">
              Answers cite exact file paths and line ranges from your indexed code.
            </p>
          </aside>
          <main className="min-w-0 flex-1">{children}</main>
        </div>
      </body>
    </html>
  );
}
