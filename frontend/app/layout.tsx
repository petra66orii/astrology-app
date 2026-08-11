import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "True Sky", template: "%s · True Sky" },
  description: "Private, reproducible natal charts with honest unknown-time handling.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <header className="siteHeader">
          <Link className="brand" href="/">True Sky</Link>
          <nav aria-label="Primary navigation">
            <Link href="/dashboard">Dashboard</Link>
            <Link className="button buttonSmall" href="/chart/new">New chart</Link>
          </nav>
        </header>
        <main>{children}</main>
        <footer>Built for clarity, privacy, and reproducible calculations.</footer>
      </body>
    </html>
  );
}
