import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }) }));
vi.mock("@/lib/api", () => ({ apiMutation: vi.fn(), browserApi: vi.fn() }));

import { ChartForm } from "./ChartForm";

describe("ChartForm", () => {
  it("removes exact time and explains unknown-time omissions", () => {
    render(<ChartForm />);
    expect(screen.getByLabelText("Local birth time")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("I don't know my birth time"));
    expect(screen.queryByLabelText("Local birth time")).not.toBeInTheDocument();
    expect(screen.getByText(/Rising sign, chart angles, houses/)).toBeInTheDocument();
  });
});
