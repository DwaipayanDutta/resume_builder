import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup, act } from "@testing-library/react";
import { App } from "../src/App";

const USER = { id: 7, email: "alex@example.com", name: "Alex Morgan" };
const CONFIG = { default_backend: null, default_model: null, backends: [] };

function res(data: unknown, status = 200) {
  return Promise.resolve({ ok: status < 400, status, json: async () => data } as Response);
}

type Handler = (init?: RequestInit) => Promise<Response>;

function mockFetch(routes: Record<string, Handler>) {
  const fn = vi.fn((url: string, init?: RequestInit) => {
    const h = routes[url];
    if (!h) throw new Error(`Unexpected fetch ${url}`);
    return h(init);
  });
  globalThis.fetch = fn as unknown as typeof fetch;
  window.fetch = globalThis.fetch;
  return fn;
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  window.history.replaceState(null, "", "/");
});

describe("Authentication gate", () => {
  it("shows the welcome page when there is no session", async () => {
    mockFetch({ "/api/auth/me": () => res({ detail: "Not signed in." }, 401) });
    render(<App />);
    expect(await screen.findByRole("heading", { level: 1, name: "Tailor Your Resume to Every Job." })).toBeDefined();
    expect(screen.queryByRole("tab", { name: "Dashboard" })).toBeNull();
    expect(screen.getAllByAltText("Resume Studio").length).toBeGreaterThan(0);
  });

  it("goes from the welcome page to sign in and back", async () => {
    mockFetch({ "/api/auth/me": () => res({}, 401) });
    render(<App />);
    fireEvent.click((await screen.findAllByRole("button", { name: "Sign in" }))[0]);
    expect(screen.getByRole("heading", { name: "Welcome back" })).toBeDefined();
    expect(window.location.hash).toBe("#signin");
    fireEvent.click(screen.getByRole("button", { name: /Back to home/ }));
    expect(screen.getByRole("heading", { level: 1, name: "Tailor Your Resume to Every Job." })).toBeDefined();
  });

  it("registers a new account and enters the app", async () => {
    const fetchMock = mockFetch({
      "/api/auth/me": () => res({ detail: "Not signed in." }, 401),
      "/api/auth/register": () => res(USER, 201),
      "/api/studio/config": () => res(CONFIG),
    });
    render(<App />);
    fireEvent.click((await screen.findAllByRole("button", { name: "Get started" }))[0]);
    expect(screen.getByRole("heading", { name: "Create your account" })).toBeDefined();
    fireEvent.change(screen.getByLabelText("Full name"), { target: { value: "Alex Morgan" } });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "alex@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "longenough1" } });
    fireEvent.change(screen.getByLabelText("Confirm password"), { target: { value: "longenough1" } });
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByRole("tab", { name: "Dashboard" })).toBeDefined();
    const [, init] = fetchMock.mock.calls.find(([u]) => u === "/api/auth/register")!;
    expect(JSON.parse(init!.body as string)).toEqual({
      name: "Alex Morgan", email: "alex@example.com", password: "longenough1",
    });
    expect(screen.getByLabelText("Account menu for Alex Morgan").textContent).toContain("AM");
  });

  it("validates the registration form before calling the server", async () => {
    const fetchMock = mockFetch({ "/api/auth/me": () => res({}, 401) });
    render(<App />);
    fireEvent.click((await screen.findAllByRole("button", { name: "Get started" }))[0]);
    fireEvent.change(screen.getByLabelText("Full name"), { target: { value: "Alex" } });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "a@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "longenough1" } });
    fireEvent.change(screen.getByLabelText("Confirm password"), { target: { value: "different1" } });
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));
    expect(screen.getByRole("alert").textContent).toMatch(/don't match/);
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "short" } });
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));
    expect(screen.getByRole("alert").textContent).toMatch(/at least 8/);
    expect(fetchMock).toHaveBeenCalledTimes(1); // only /api/auth/me
  });

  it("shows the server's error for a wrong password", async () => {
    mockFetch({
      "/api/auth/me": () => res({}, 401),
      "/api/auth/login": () => res({ detail: "Incorrect email or password." }, 401),
    });
    render(<App />);
    fireEvent.click((await screen.findAllByRole("button", { name: "Sign in" }))[0]);
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "alex@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "wrongpass" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect((await screen.findByRole("alert")).textContent).toBe("Incorrect email or password.");
  });

  it("signs out from the account menu", async () => {
    const fetchMock = mockFetch({
      "/api/auth/me": () => res(USER),
      "/api/studio/config": () => res(CONFIG),
      "/api/auth/logout": () => Promise.resolve({ ok: true, status: 204, json: async () => ({}) } as Response),
    });
    render(<App />);
    fireEvent.click(await screen.findByLabelText("Account menu for Alex Morgan"));
    expect(screen.getByText("alex@example.com")).toBeDefined();
    fireEvent.click(screen.getByRole("menuitem", { name: "Sign out" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Tailor Your Resume to Every Job." })).toBeDefined();
    expect(fetchMock).toHaveBeenCalledWith("/api/auth/logout", expect.objectContaining({ method: "POST" }));
  });

  it("returns to sign-in when the session expires mid-use", async () => {
    let expired = false;
    mockFetch({
      "/api/auth/me": () => res(USER),
      "/api/studio/config": () => (expired ? res({ detail: "Sign in to continue." }, 401) : res(CONFIG)),
    });
    render(<App />);
    await screen.findByRole("tab", { name: "Dashboard" });
    expired = true;
    await act(async () => {
      await window.fetch("/api/studio/config");
    });
    await waitFor(() => expect(screen.getByRole("heading", { name: "Welcome back" })).toBeDefined());
  });
});
