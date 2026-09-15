"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "wavhost-theme";

function getTheme(): "light" | "dark" {
  if (typeof document === "undefined") return "light";
  return (document.documentElement.getAttribute("data-theme") as "light" | "dark") || "light";
}

function setTheme(theme: "light" | "dark") {
  document.documentElement.setAttribute("data-theme", theme);
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch (e) {
    // ignore quota / private mode
  }
}

export function ThemeToggle() {
  const [theme, setThemeState] = useState<"light" | "dark">("light");

  useEffect(() => {
    setThemeState(getTheme());
  }, []);

  const handleToggle = () => {
    const newTheme = theme === "dark" ? "light" : "dark";
    setTheme(newTheme);
    setThemeState(newTheme);
  };

  const nextTheme = theme === "dark" ? "light" : "dark";
  const label = nextTheme === "dark" ? "Dark" : "Light";

  return (
    <button
      type="button"
      className="theme-toggle"
      id="theme-toggle"
      aria-label={`Switch to ${nextTheme} theme`}
      onClick={handleToggle}
    >
      {label}
    </button>
  );
}
