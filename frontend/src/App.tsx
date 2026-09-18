import { type KeyboardEvent, useRef, useState } from "react";
import { AboutPage } from "./about/AboutPage";
import { ChatPage } from "./chat/ChatPage";
import { ui } from "./i18n/text";
import { LabPage } from "./lab/LabPage";
import { type Theme, useTheme } from "./shell/useTheme";

const TABS = ["chat", "lab", "about"] as const;
type Tab = (typeof TABS)[number];

export function App() {
  const [tab, setTab] = useState<Tab>("chat");
  const [theme, setTheme] = useTheme();
  const tabRefs = useRef<Record<Tab, HTMLButtonElement | null>>({
    chat: null,
    lab: null,
    about: null,
  });

  function onTabKey(event: KeyboardEvent<HTMLDivElement>) {
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (!step) return;
    event.preventDefault();
    const next = TABS[(TABS.indexOf(tab) + step + TABS.length) % TABS.length] ?? "chat";
    setTab(next);
    tabRefs.current[next]?.focus();
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand__mark" aria-hidden="true">
            🪰
          </span>
          <div>
            <h1 className="brand__title">{ui.app_title}</h1>
            <p className="brand__subtitle">{ui.app_subtitle}</p>
          </div>
        </div>

        <div className="tabs" role="tablist" aria-label={ui.app_title} onKeyDown={onTabKey}>
          {TABS.map((key) => (
            <button
              key={key}
              ref={(el) => {
                tabRefs.current[key] = el;
              }}
              type="button"
              role="tab"
              id={`sekme-${key}`}
              aria-selected={tab === key}
              aria-controls={`panel-${key}`}
              tabIndex={tab === key ? 0 : -1}
              className="tab"
              onClick={() => setTab(key)}
            >
              {ui.tabs[key]}
            </button>
          ))}
        </div>

        <label className="theme">
          <span className="visually-hidden">{ui.theme.label}</span>
          <select value={theme} onChange={(event) => setTheme(event.target.value as Theme)}>
            <option value="system">{ui.theme.system}</option>
            <option value="light">{ui.theme.light}</option>
            <option value="dark">{ui.theme.dark}</option>
          </select>
        </label>
      </header>

      <main id={`panel-${tab}`} role="tabpanel" aria-labelledby={`sekme-${tab}`} className="main">
        {tab === "chat" && <ChatPage />}
        {tab === "lab" && <LabPage />}
        {tab === "about" && <AboutPage />}
      </main>
    </div>
  );
}
