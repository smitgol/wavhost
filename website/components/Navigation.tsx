import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "./ThemeToggle";

interface NavigationProps {
  currentPath?: string;
  variant?: "default" | "docs";
}

export function Navigation({
  currentPath = "/",
  variant = "default",
}: NavigationProps) {
  const isDocs = variant === "docs";

  return (
    <header className={isDocs ? "nav docs-top" : "nav"}>
      <div className={isDocs ? "docs-top-inner" : "wrap nav-inner"}>
        <Link className="wordmark" href="/">
          Wavhost
        </Link>
        <nav
          className={
            isDocs
              ? "docs-top-nav flex items-center gap-1"
              : "flex items-center gap-1"
          }
          aria-label="Primary"
        >
          {isDocs ? (
            <>
              <Button
                asChild
                variant="ghost"
                size="sm"
                aria-current={currentPath.startsWith("/docs") ? "page" : undefined}
              >
                <Link href="/docs">Docs</Link>
              </Button>
              <Button asChild variant="ghost" size="sm">
                <Link href="/models">Models</Link>
              </Button>
              <Button asChild variant="ghost" size="sm">
                <a
                  href="https://github.com/smitgol/wavhost"
                  rel="noopener noreferrer"
                >
                  GitHub
                </a>
              </Button>
            </>
          ) : (
            <>
              <Button asChild variant="ghost" size="sm">
                <a
                  href="https://github.com/smitgol/wavhost"
                  rel="noopener noreferrer"
                >
                  GitHub
                </a>
              </Button>
              <Button
                asChild
                variant="ghost"
                size="sm"
                aria-current={currentPath === "/models" ? "page" : undefined}
              >
                <Link href="/models">Models</Link>
              </Button>
              <Button
                asChild
                variant="ghost"
                size="sm"
                aria-current={
                  currentPath.startsWith("/docs") ? "page" : undefined
                }
              >
                <Link href="/docs">Docs</Link>
              </Button>
            </>
          )}
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
