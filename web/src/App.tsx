import { useEffect, useRef, useState } from "react";
import { EditorLayout } from "./components/EditorLayout";
import { StudioDashboard } from "./components/StudioDashboard";
import { AuthPage, type AuthMode } from "./components/AuthPage";
import { Landing } from "./components/Landing";
import { fetchMe, logout, type User } from "./auth";
import "./index.css";
import "./studio.css";
import "./landing.css";

type Tab = "dashboard" | "editor";

type PublicView = "landing" | AuthMode;

function readTab(): Tab {
  return window.location.hash === "#editor" ? "editor" : "dashboard";
}

function readPublicView(): PublicView {
  const h = window.location.hash;
  return h === "#signin" ? "signin" : h === "#register" ? "register" : "landing";
}

function setHash(hash: string) {
  try {
    window.history.replaceState(null, "", hash || window.location.pathname);
  } catch {
    /* ignore */
  }
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] ?? "") + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase() || "?";
}

function UserMenu({ user, onSignOut }: { user: User; onSignOut: () => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", esc);
    };
  }, [open]);

  return (
    <div className="user-menu" ref={ref}>
      <button type="button" className="user-trigger" aria-haspopup="menu" aria-expanded={open}
        onClick={() => setOpen((v) => !v)} aria-label={`Account menu for ${user.name}`}>
        <span className="avatar" aria-hidden="true">{initials(user.name)}</span>
        <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
          <path d="M3 4.5l3 3 3-3" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        </svg>
      </button>
      {open && (
        <div className="user-dropdown" role="menu">
          <div className="user-info">
            <strong>{user.name}</strong>
            <span>{user.email}</span>
          </div>
          <button type="button" role="menuitem" onClick={onSignOut}>Sign out</button>
        </div>
      )}
    </div>
  );
}

export function App() {
  const [tab, setTab] = useState<Tab>(readTab);
  // undefined = still checking the session, null = signed out
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [publicView, setPublicView] = useState<PublicView>(readPublicView);

  const showPublic = (v: PublicView) => {
    setPublicView(v);
    setHash(v === "landing" ? "" : `#${v}`);
  };

  useEffect(() => {
    const onHash = () => {
      setTab(readTab());
      setPublicView(readPublicView());
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchMe()
      .then((u) => !cancelled && setUser(u))
      .catch(() => !cancelled && setUser(null));
    return () => {
      cancelled = true;
    };
  }, []);

  // If the session expires mid-use, any API call returns 401: send the user back to sign in.
  useEffect(() => {
    if (!user) return;
    const original = window.fetch;
    const wrapped: typeof fetch = async (input, init) => {
      const res = await original(input, init);
      const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
      if (res.status === 401 && url.includes("/api/") && !url.includes("/api/auth/")) {
        setPublicView("signin"); // session expired: go straight to sign in
        setUser(null);
      }
      return res;
    };
    window.fetch = wrapped;
    return () => {
      if (window.fetch === wrapped) window.fetch = original;
    };
  }, [user]);

  const go = (t: Tab) => {
    setTab(t);
    setHash(t === "editor" ? "#editor" : "");
  };

  const onAuthed = (u: User) => {
    setUser(u);
    setTab("dashboard");
    setHash("");
  };

  const signOut = async () => {
    try {
      await logout();
    } finally {
      showPublic("landing");
      setUser(null);
    }
  };

  if (user === undefined) {
    return (
      <div className="app-splash" aria-busy="true">
        <img src="/brand/resume-studio-icon.svg" alt="Resume Studio" width="56" height="56" />
      </div>
    );
  }

  if (user === null) {
    if (publicView === "landing") {
      return <Landing onGetStarted={() => showPublic("register")} onSignIn={() => showPublic("signin")} />;
    }
    return (
      <AuthPage
        key={publicView}
        initialMode={publicView}
        onAuthed={onAuthed}
        onBack={() => showPublic("landing")}
        onModeChange={(m) => setHash(`#${m}`)}
      />
    );
  }

  return (
    <div className="app-shell">
      <nav className="app-nav" aria-label="Main">
        <a className="app-logo" href="#" onClick={(e) => { e.preventDefault(); go("dashboard"); }}>
          <img src="/brand/resume-studio-logo-on-light.svg" alt="Resume Studio" className="logo-full" />
          <img src="/brand/resume-studio-icon.svg" alt="Resume Studio" className="logo-icon" />
        </a>
        <div className="app-tabs" role="tablist">
          <button type="button" role="tab" aria-selected={tab === "dashboard"}
            className={`app-tab ${tab === "dashboard" ? "active" : ""}`} onClick={() => go("dashboard")}>
            Dashboard
          </button>
          <button type="button" role="tab" aria-selected={tab === "editor"}
            className={`app-tab ${tab === "editor" ? "active" : ""}`} onClick={() => go("editor")}>
            Guided editor
          </button>
        </div>
        <div className="app-nav-right">
          <UserMenu user={user} onSignOut={signOut} />
        </div>
      </nav>
      <main className="app-main">
        {tab === "dashboard" ? <StudioDashboard onOpenEditor={() => go("editor")} /> : <EditorLayout />}
      </main>
    </div>
  );
}

export default App;
