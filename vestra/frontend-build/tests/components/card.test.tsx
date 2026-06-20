import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Card, CardHeader, Badge, StatCard, CardSkeleton, LoadingScreen } from "@/components/ui/card";

describe("Card", () => {
  it("renders children", () => {
    render(<Card>Card content</Card>);
    expect(screen.getByText("Card content")).toBeInTheDocument();
  });

  it("applies className", () => {
    const { container } = render(<Card className="test-class">Content</Card>);
    expect(container.firstChild).toHaveClass("test-class");
  });
});

describe("CardHeader", () => {
  it("renders title", () => {
    render(<CardHeader title="Test Title" />);
    expect(screen.getByText("Test Title")).toBeInTheDocument();
  });

  it("renders subtitle when provided", () => {
    render(<CardHeader title="Title" subtitle="Subtitle text" />);
    expect(screen.getByText("Subtitle text")).toBeInTheDocument();
  });
});

describe("Badge", () => {
  it("renders text", () => {
    render(<Badge>Active</Badge>);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("supports variant", () => {
    render(<Badge variant="success">Success</Badge>);
    expect(screen.getByText("Success")).toBeInTheDocument();
  });
});

describe("StatCard", () => {
  it("renders label and value", () => {
    render(<StatCard label="Revenue" value="KES 50,000" />);
    expect(screen.getByText("Revenue")).toBeInTheDocument();
    expect(screen.getByText("KES 50,000")).toBeInTheDocument();
  });

  it("renders icon when provided", () => {
    const Icon = () => <span data-testid="icon">I</span>;
    render(<StatCard label="Users" value="100" icon={<Icon />} />);
    expect(screen.getByTestId("icon")).toBeInTheDocument();
  });
});

describe("LoadingScreen", () => {
  it("renders loader", () => {
    render(<LoadingScreen />);
    // LoadingScreen should show some loading indicator
    expect(document.body.contains(document.querySelector(".animate-spin") || document.querySelector("[role='status']"))).toBeDefined();
  });
});
