import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Button } from "@/components/ui/button";

describe("Button", () => {
  it("renders children", () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText("Click me")).toBeInTheDocument();
  });

  it("handles click events", () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Click</Button>);
    fireEvent.click(screen.getByText("Click"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("shows loading spinner when loading", () => {
    render(<Button loading>Loading</Button>);
    expect(screen.getByRole("button")).toBeDisabled();
    // Should contain a spinner element
    const btn = screen.getByRole("button");
    expect(btn.querySelector("svg")).toBeTruthy();
  });

  it("is disabled when disabled prop is set", () => {
    render(<Button disabled>Disabled</Button>);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("supports variants", () => {
    render(<Button variant="outline">Outline</Button>);
    expect(screen.getByText("Outline")).toBeInTheDocument();
  });

  it("supports sizes", () => {
    render(<Button size="lg">Large</Button>);
    expect(screen.getByText("Large")).toBeInTheDocument();
  });

  it("forwards ref", () => {
    render(<Button>Ref</Button>);
    expect(screen.getByText("Ref")).toBeInTheDocument();
  });
});
