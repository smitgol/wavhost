import Link from "next/link";

export function Footer() {
  return (
    <footer className="footer">
      <div className="wrap footer-inner">
        <span>Wavhost</span>
        <span className="footer-links">
          <a href="https://github.com/smitgol/wavhost" rel="noopener noreferrer">
            GitHub
          </a>
          <Link href="/docs">Docs</Link>
          <a href="https://github.com/smitgol/wavhost/blob/main/LICENSE" rel="noopener noreferrer">
            Apache-2.0
          </a>
        </span>
      </div>
    </footer>
  );
}
