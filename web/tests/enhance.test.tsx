import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { EnhanceBulletModal } from "../src/components/EnhanceBulletModal";

describe("EnhanceBulletModal", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders with original bullet and default local disclosure", () => {
    render(
      <EnhanceBulletModal
        isOpen={true}
        bullet="Led backend migration to microservices"
        jobDescription="Senior backend engineer"
        onAccept={vi.fn()}
        onClose={vi.fn()}
      />
    );

    expect(screen.getByText("✨ Contextual Bullet Enhancement")).toBeDefined();
    expect(screen.getByText("Led backend migration to microservices")).toBeDefined();
    expect(
      screen.getByText(/Content is processed locally on your machine via Ollama/)
    ).toBeDefined();
  });

  it("switches to cloud disclosure when Claude backend is selected", () => {
    render(
      <EnhanceBulletModal
        isOpen={true}
        bullet="Led backend migration"
        jobDescription="Senior engineer"
        onAccept={vi.fn()}
        onClose={vi.fn()}
      />
    );

    const select = screen.getByRole("combobox");
    fireEvent.change(select, { target: { value: "claude" } });

    expect(
      screen.getByText(/transmitted externally to Anthropic Claude/)
    ).toBeDefined();
  });

  it("generates variations and accepts a selected variation", async () => {
    const onAcceptMock = vi.fn();
    const onCloseMock = vi.fn();

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        original: "Led backend migration",
        variations: [
          "Architected and executed migration to microservices improving reliability by 25%.",
          "Spearheaded distributed system refactoring across core services.",
        ],
        backend_used: "ollama",
        disclosure: "Private: Content processed locally",
      }),
    } as any);

    render(
      <EnhanceBulletModal
        isOpen={true}
        bullet="Led backend migration"
        jobDescription="Senior engineer"
        onAccept={onAcceptMock}
        onClose={onCloseMock}
      />
    );

    const generateBtn = screen.getByText("Generate Variations");
    fireEvent.click(generateBtn);

    await waitFor(() => {
      expect(
        screen.getByText(
          "Architected and executed migration to microservices improving reliability by 25%."
        )
      ).toBeDefined();
    });

    const acceptBtn = screen.getByText("Accept Variation");
    fireEvent.click(acceptBtn);

    expect(onAcceptMock).toHaveBeenCalledWith(
      "Architected and executed migration to microservices improving reliability by 25%."
    );
    expect(onCloseMock).toHaveBeenCalled();
  });

  it("rejects enhancement when user cancels", () => {
    const onAcceptMock = vi.fn();
    const onCloseMock = vi.fn();

    render(
      <EnhanceBulletModal
        isOpen={true}
        bullet="Led backend migration"
        jobDescription="Senior engineer"
        onAccept={onAcceptMock}
        onClose={onCloseMock}
      />
    );

    const cancelBtn = screen.getByText("Cancel");
    fireEvent.click(cancelBtn);

    expect(onAcceptMock).not.toHaveBeenCalled();
    expect(onCloseMock).toHaveBeenCalled();
  });

  it("displays error message on backend failure", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 502,
      json: async () => ({ detail: "Ollama connection failed: service offline" }),
    } as any);

    render(
      <EnhanceBulletModal
        isOpen={true}
        bullet="Led backend migration"
        jobDescription="Senior engineer"
        onAccept={vi.fn()}
        onClose={vi.fn()}
      />
    );

    const generateBtn = screen.getByText("Generate Variations");
    fireEvent.click(generateBtn);

    await waitFor(() => {
      expect(
        screen.getByText("Ollama connection failed: service offline")
      ).toBeDefined();
    });
  });
});
