"use client";

import { useEffect, useState } from "react";
import { MoonIcon, SunIcon } from "lucide-react";
import { Button } from "@/components/ui/button";

const STORAGE_KEY = "wavhost-theme";

function applyTheme(theme: "light" | "dark") {
  document.documentElement.setAttribute("data-theme", theme);
  document.documentElement.classList.toggle("dark", theme === "dark");
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // ignore quota / private mode
  }
}

function readTheme(): "light" | "dark" {
  if (typeof document === "undefined") return "light";
  return (
    (document.documentElement.getAttribute("data-theme") as "light" | "dark") ||
    "light"
  );
}

export function ThemeToggle() {
  const [theme, setThemeState] = useState<"light" | "dark">("light");

  useEffect(() => {
    setThemeState(readTheme());
  }, []);

  const nextTheme = theme === "dark" ? "light" : "dark";

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon-sm"
      aria-label={`Switch to ${nextTheme} theme`}
      onClick={() => {
        applyTheme(nextTheme);
        setThemeState(nextTheme);
      }}
    >
      {theme === "light" ? <MoonIcon /> : <SunIcon />}
    </Button>
  );
}
