import { useEffect, useState } from "react";
import { Monitor, Moon, Sun } from "lucide-react";
import { Field, Select } from "./ui";

type Theme = "system" | "light" | "dark";

export function ThemeControl() {
  const [theme, setTheme] = useState<Theme>(() => {
    const value = document.documentElement.dataset.theme;
    return value === "light" || value === "dark" ? value : "system";
  });
  useEffect(() => {
    const update = (event: StorageEvent) => {
      if (event.key !== "retrievec.theme" && event.key !== null) return;
      const value = event.newValue;
      setTheme(value === "light" || value === "dark" ? value : "system");
    };
    window.addEventListener("storage", update);
    return () => window.removeEventListener("storage", update);
  }, []);
  useEffect(() => {
    if (theme === "system") delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = theme;
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const updateChrome = () => {
      const color = getComputedStyle(document.documentElement).backgroundColor;
      document
        .querySelector('meta[name="theme-color"]')
        ?.setAttribute("content", color);
    };
    updateChrome();
    media.addEventListener("change", updateChrome);
    return () => media.removeEventListener("change", updateChrome);
  }, [theme]);
  const Icon = theme === "dark" ? Moon : theme === "light" ? Sun : Monitor;
  return (
    <div className="theme-control">
      <Icon size={16} aria-hidden="true" />
      <Field label="Appearance">
        <Select
          value={theme}
          onChange={(event) => {
            const value = event.target.value as Theme;
            setTheme(value);
            try {
              if (value === "system")
                localStorage.removeItem("retrievec.theme");
              else localStorage.setItem("retrievec.theme", value);
            } catch {
              /* This tab still honors the user's choice. */
            }
          }}
        >
          <option value="system">System</option>
          <option value="light">Light</option>
          <option value="dark">Dark</option>
        </Select>
      </Field>
    </div>
  );
}
