import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CustomerApp } from "../routes/CustomerApp";

class MockWebSocket {
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: (() => void) | null = null;
  close() {}
}

describe("customer route", () => {
  beforeEach(() => {
    vi.stubGlobal("WebSocket", MockWebSocket);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        customer_name: "Emma Lindberg",
        identity_status: "not_identified",
        document: { name: null, status: "not_uploaded" },
        transcript: [],
        meeting: null,
        card: null,
      }),
    }));
  });

  it("renders the customer upload workflow", async () => {
    render(<CustomerApp />);
    expect(await screen.findByRole("heading", { name: "Welcome, Emma" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Add your latest payslip" })).toBeInTheDocument();
    expect(screen.queryByText(/credit score/i)).not.toBeInTheDocument();
  });
});