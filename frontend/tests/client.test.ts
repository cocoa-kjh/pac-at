import { describe, it, expect, vi, beforeEach } from "vitest";
import { api } from "../src/api/client";

beforeEach(() => {
  global.fetch = vi.fn(async () =>
    ({ ok: true, json: async () => [{ id: 1, title: "t" }] }) as Response);
});

describe("api client", () => {
  it("listBroadcasts hits /broadcasts", async () => {
    const data = await api.listBroadcasts();
    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/broadcasts", expect.any(Object));
    expect(data[0].id).toBe(1);
  });
  it("createSchedule POSTs JSON", async () => {
    await api.createSchedule({ broadcast_id: 1, start_at: "x", end_at: "y",
      recurrence: "none", recurrence_rule: null, items: [] } as any);
    const call = (global.fetch as any).mock.calls.at(-1);
    expect(call[1].method).toBe("POST");
  });
});
