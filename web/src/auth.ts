export interface User {
  id: number;
  email: string;
  name: string;
}

export class AuthError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function post(url: string, body?: unknown): Promise<Response> {
  return fetch(url, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    credentials: "same-origin",
  });
}

async function asUser(res: Response): Promise<User> {
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (typeof data?.detail === "string") detail = data.detail;
      else if (Array.isArray(data?.detail)) detail = "Please check the form fields.";
    } catch {
      /* keep default */
    }
    throw new AuthError(detail, res.status);
  }
  return res.json();
}

/** Returns the signed-in user, or null if there is no valid session. */
export async function fetchMe(): Promise<User | null> {
  const res = await fetch("/api/auth/me", { credentials: "same-origin" });
  if (res.status === 401) return null;
  return asUser(res);
}

export const register = (name: string, email: string, password: string) =>
  post("/api/auth/register", { name, email, password }).then(asUser);

export const login = (email: string, password: string) =>
  post("/api/auth/login", { email, password }).then(asUser);

export async function logout(): Promise<void> {
  await post("/api/auth/logout");
}
