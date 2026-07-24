import { THEME_OPTIONS, useTheme, type ThemeId } from "../state/theme";

export function ThemeSwitcher() {
  const { theme, setTheme } = useTheme();
  return (
    <div className="theme-switcher" role="group" aria-label="Theme">
      {THEME_OPTIONS.map((opt) => (
        <button
          key={opt.id}
          type="button"
          className={theme === opt.id ? "active" : ""}
          aria-pressed={theme === opt.id}
          onClick={() => setTheme(opt.id as ThemeId)}
          title={opt.label}
        >
          {opt.label.replace("Minimal ", "")}
        </button>
      ))}
    </div>
  );
}
