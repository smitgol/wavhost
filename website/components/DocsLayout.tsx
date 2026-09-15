import Link from "next/link";

interface DocsLayoutProps {
  children: React.ReactNode;
  breadcrumb: string;
  currentPath: string;
  toc?: Array<{ id: string; label: string }>;
}

export function DocsLayout({ children, breadcrumb, currentPath, toc }: DocsLayoutProps) {
  return (
    <div className="docs-shell">
      <aside className="docs-side" aria-label="Documentation">
        <p className="docs-side-label">Guides</p>
        <ul className="docs-side-list">
          <li>
            <Link href="/docs" aria-current={currentPath === "/docs" ? "page" : undefined}>
              Getting started
            </Link>
          </li>
        </ul>
        <p className="docs-side-label">Reference</p>
        <ul className="docs-side-list">
          <li>
            <Link href="/docs/cli" aria-current={currentPath === "/docs/cli" ? "page" : undefined}>
              CLI
            </Link>
          </li>
          <li>
            <Link href="/docs/api" aria-current={currentPath === "/docs/api" ? "page" : undefined}>
              API
            </Link>
          </li>
        </ul>
        <p className="docs-side-label">Site</p>
        <ul className="docs-side-list">
          <li>
            <Link href="/">Home</Link>
          </li>
          <li>
            <Link href="/models">Models</Link>
          </li>
        </ul>
      </aside>

      <div className="docs-main-col">
        <main id="main" className="docs-article">
          <nav className="docs-crumb" aria-label="Breadcrumb">
            <Link href="/docs">Docs</Link>
            <span aria-hidden="true">/</span>
            <span>{breadcrumb}</span>
          </nav>
          {children}
        </main>

        {toc && toc.length > 0 && (
          <aside className="docs-toc" aria-label="On this page">
            <p className="docs-toc-title">On this page</p>
            <ul>
              {toc.map((item) => (
                <li key={item.id}>
                  <a href={`#${item.id}`}>{item.label}</a>
                </li>
              ))}
            </ul>
          </aside>
        )}
      </div>
    </div>
  );
}
