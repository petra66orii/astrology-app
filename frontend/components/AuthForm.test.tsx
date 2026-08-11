import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
const refresh = vi.fn();
const mutation = vi.fn();

vi.mock("next/navigation", () => ({ useRouter: () => ({ push, refresh }) }));
vi.mock("@/lib/api", () => ({ apiMutation: (...args: unknown[]) => mutation(...args) }));

import { AuthForm } from "./AuthForm";

describe("AuthForm", () => {
  beforeEach(() => { mutation.mockReset(); push.mockReset(); refresh.mockReset(); });

  it("submits registration and navigates to the dashboard", async () => {
    mutation.mockResolvedValue({ user: { id: "1" } });
    render(<AuthForm mode="register" />);
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "person@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "a-secure-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));
    await waitFor(() => expect(mutation).toHaveBeenCalledWith("/auth/register/", "POST", { email: "person@example.com", password: "a-secure-password" }));
    expect(push).toHaveBeenCalledWith("/dashboard");
  });
});
