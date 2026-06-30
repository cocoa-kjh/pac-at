import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import Broadcasts from "../src/pages/Broadcasts";
import { api } from "../src/api/client";

vi.mock("../src/api/client");

beforeEach(() => {
  (api.listBroadcasts as any) = vi.fn(async () => [
    { id: 1, title: "내 방송", description: "", privacy: "private",
      youtube_broadcast_id: null, status: "draft" }]);
});

describe("Broadcasts page", () => {
  it("renders broadcast titles", async () => {
    render(<Broadcasts />);
    await waitFor(() => expect(screen.getByText("내 방송")).toBeDefined());
  });
});
