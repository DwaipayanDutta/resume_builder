import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup, within } from "@testing-library/react";
import { Landing } from "../src/components/Landing";

afterEach(() => cleanup());

describe("Landing page", () => {
  it("renders every section of the welcome page", () => {
    render(<Landing onGetStarted={() => {}} onSignIn={() => {}} />);
    expect(screen.getByRole("heading", { level: 1, name: "Tailor Your Resume to Every Job." })).toBeDefined();
    expect(screen.getByRole("heading", { name: "Every Resume. Every Application." })).toBeDefined();
    expect(screen.getByRole("heading", { name: "Three Steps to Your Next Application" })).toBeDefined();
    expect(screen.getByRole("heading", { name: "Ready for Your Next Application?" })).toBeDefined();
    expect(screen.getAllByRole("article")).toHaveLength(5);
    expect(screen.getByText(/All rights reserved/)).toBeDefined();
  });

  it("only states facts about the product, not invented performance claims", () => {
    render(<Landing onGetStarted={() => {}} onSignIn={() => {}} />);
    const facts = screen.getByRole("region", { name: "At a glance" });
    expect(within(facts).getByText("100+")).toBeDefined();
    const text = document.body.textContent ?? "";
    expect(text).not.toMatch(/interview rate|client rating|resumes crafted|\d+(\.\d+)?\s*★/i);
  });

  it("routes calls to action", () => {
    const onGetStarted = vi.fn();
    const onSignIn = vi.fn();
    render(<Landing onGetStarted={onGetStarted} onSignIn={onSignIn} />);
    fireEvent.click(screen.getAllByRole("button", { name: "Get started" })[0]);
    fireEvent.click(screen.getByRole("button", { name: /Create free account/ }));
    fireEvent.click(screen.getAllByRole("button", { name: "Sign in" })[0]);
    expect(onGetStarted).toHaveBeenCalledTimes(2);
    expect(onSignIn).toHaveBeenCalledTimes(1);
  });

  it("scrolls to sections from the nav", () => {
    const spy = vi.fn();
    Element.prototype.scrollIntoView = spy;
    render(<Landing onGetStarted={() => {}} onSignIn={() => {}} />);
    fireEvent.click(within(screen.getByRole("navigation", { name: "Sections" })).getByText("How it works"));
    expect(spy).toHaveBeenCalled();
    expect((spy.mock.contexts[0] as HTMLElement).id).toBe("how");
  });
});
