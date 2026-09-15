import Link from "next/link";
import { ThemeToggle } from "./ThemeToggle";

interface NavLinkProps {
  href: string;
  children: React.ReactNode;
  current?: boolean;
}

function NavLink({ href, children, current }: NavLinkProps) {
  return (
    <Link 
      href={href}
      aria-current={current ? "page" : undefined}
    >
      {children}
    </Link>
  );
}

interface NavigationProps {
  currentPath?: string;
  variant?: "default" | "docs";
}

export function Navigation({ currentPath = "/", variant = "default" }: NavigationProps) {
  const isDocs = variant === "docs";
  
  return (
    <header className={isDocs ? "nav docs-top" : "nav"}>
      <div className={isDocs ? "docs-top-inner" : "wrap nav-inner"}>
        <Link className="wordmark" href="/">
          Wavhost
        </Link>
        <nav className={isDocs ? "docs-top-nav" : undefined} aria-label="Primary">
          {isDocs ? (
            <>
              <NavLink href="/docs" current={currentPath.startsWith("/docs")}>
                Docs
              </NavLink>
              <NavLink href="/models">Models</NavLink>
              <a href="https://github.com/smitgol/wavhost" rel="noopener noreferrer">
                GitHub
              </a>
            </>
          ) : (
            <>
              <a href="https://github.com/smitgol/wavhost" rel="noopener noreferrer">
                GitHub
              </a>
              <NavLink href="/models" current={currentPath === "/models"}>
                Models
              </NavLink>
              <NavLink href="/docs" current={currentPath.startsWith("/docs")}>
                Docs
              </NavLink>
            </>
          )}
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
