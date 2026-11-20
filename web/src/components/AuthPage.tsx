import { useState, type FormEvent } from "react";
import { login, register, type User } from "../auth";

type Mode = "signin" | "register";

export type AuthMode = Mode;

export function AuthPage({ onAuthed, initialMode = "signin", onBack, onModeChange }: {
  onAuthed: (user: User) => void;
  initialMode?: Mode;
  onBack?: () => void;
  onModeChange?: (mode: Mode) => void;
}) {
  const [mode, setMode] = useState<Mode>(initialMode);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const switchMode = (m: Mode) => {
    setMode(m);
    onModeChange?.(m);
    setError(null);
    setPassword("");
    setConfirm("");
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (mode === "register") {
      if (!name.trim()) return setError("Enter your name.");
      if (password.length < 8) return setError("Use a password of at least 8 characters.");
      if (password !== confirm) return setError("The passwords don't match.");
    }
    setBusy(true);
    try {
      const user = mode === "register"
        ? await register(name.trim(), email.trim(), password)
        : await login(email.trim(), password);
      onAuthed(user);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-shell">
      <aside className="auth-brand" aria-hidden="false">
        <div className="auth-brand-top">
          <img src="/brand/resume-studio-logo-on-dark.svg" alt="Resume Studio" className="auth-logo" />
          {onBack && (
            <button type="button" className="auth-back" onClick={onBack}>
              <span aria-hidden="true">←</span> Back to home
            </button>
          )}
        </div>
        <div className="auth-pitch">
          <p className="auth-tagline">Build. Tailor. Stand out.</p>
          <h1>Your resume, tailored to every job in minutes.</h1>
          <ul className="auth-points">
            <li><span className="dot violet" />Upload your TXT resume and paste a job link</li>
            <li><span className="dot teal" />Tailor with a local or cloud AI, or just format</li>
            <li><span className="dot violet" />Download a polished 2-page PDF and Word file</li>
          </ul>
        </div>
        <p className="auth-foot">Your employers, titles and dates are never changed by the AI.</p>
      </aside>

      <main className="auth-main">
        <div className="auth-card">
          <img src="/brand/resume-studio-icon.svg" alt="" className="auth-card-icon" />
          <h2>{mode === "signin" ? "Welcome back" : "Create your account"}</h2>
          <p className="auth-sub">
            {mode === "signin" ? "Sign in to continue to Resume Studio." : "Register once, then build and tailor resumes."}
          </p>

          <div className="auth-tabs" role="tablist" aria-label="Account">
            <button type="button" role="tab" aria-selected={mode === "signin"}
              className={mode === "signin" ? "active" : ""} onClick={() => switchMode("signin")}>
              Sign in
            </button>
            <button type="button" role="tab" aria-selected={mode === "register"}
              className={mode === "register" ? "active" : ""} onClick={() => switchMode("register")}>
              Create account
            </button>
          </div>

          <form onSubmit={submit} className="auth-form" noValidate>
            {mode === "register" && (
              <label>
                <span>Full name</span>
                <input autoComplete="name" value={name} onChange={(e) => setName(e.target.value)}
                  placeholder="Alex Morgan" required />
              </label>
            )}
            <label>
              <span>Email</span>
              <input type="email" autoComplete="email" value={email}
                onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required />
            </label>
            <label>
              <span>Password</span>
              <div className="pw-row">
                <input type={showPassword ? "text" : "password"}
                  autoComplete={mode === "signin" ? "current-password" : "new-password"}
                  value={password} onChange={(e) => setPassword(e.target.value)}
                  placeholder={mode === "register" ? "At least 8 characters" : ""} required />
                <button type="button" className="pw-toggle" onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? "Hide password" : "Show password"}>
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
            </label>
            {mode === "register" && (
              <label>
                <span>Confirm password</span>
                <input type={showPassword ? "text" : "password"} autoComplete="new-password"
                  value={confirm} onChange={(e) => setConfirm(e.target.value)} required />
              </label>
            )}

            {error && <p className="auth-error" role="alert">{error}</p>}

            <button type="submit" className="btn-studio primary lg auth-submit" disabled={busy}>
              {busy ? "Please wait…" : mode === "signin" ? "Sign in" : "Create account"}
            </button>
          </form>

          <p className="auth-switch">
            {mode === "signin" ? (
              <>New to Resume Studio?{" "}
                <button type="button" onClick={() => switchMode("register")}>Create an account</button></>
            ) : (
              <>Already registered?{" "}
                <button type="button" onClick={() => switchMode("signin")}>Sign in</button></>
            )}
          </p>
          <p className="auth-privacy">
            Your account is stored on the computer running Resume Studio. Passwords are hashed, never saved as text.
          </p>
        </div>
      </main>
    </div>
  );
}
