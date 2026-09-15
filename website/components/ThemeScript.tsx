export function ThemeScript() {
  return (
    <script
      dangerouslySetInnerHTML={{
        __html: `
(function () {
  try {
    var stored = localStorage.getItem("wavhost-theme");
    var theme = stored || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    document.documentElement.setAttribute("data-theme", theme);
  } catch (e) {
    document.documentElement.setAttribute("data-theme", "light");
  }
})();
        `.trim(),
      }}
    />
  );
}
