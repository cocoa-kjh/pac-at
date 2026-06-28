import { describe, it, expect, vi, beforeEach } from "vitest";
import { api } from "../src/api/client";

beforeEach(() => {
  globalThis.fetch = vi.fn(async () =>
    ({ ok: true, json: async () => [{ id: 1, title: "t" }] }) as Response);
});

describe("api client", () => {
  it("listBroadcasts hits /broadcasts", async () => {
    const data = await api.listBroadcasts();
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/broadcasts", expect.any(Object));
    expect(data[0].id).toBe(1);
  });
  it("createSchedule POSTs JSON", async () => {
    await api.createSchedule({ broadcast_id: 1, start_at: "x", end_at: "y",
      recurrence: "none", recurrence_rule: null, items: [] } as any);
    const call = (globalThis.fetch as any).mock.calls.at(-1);
    expect(call[1].method).toBe("POST");
  });
  it("deleteSchedule uses DELETE", async () => {
    await api.deleteSchedule(7);
    const call = (globalThis.fetch as any).mock.calls.at(-1);
    expect(call[0]).toBe("http://localhost:8000/schedules/7");
    expect(call[1].method).toBe("DELETE");
  });
  it("createBroadcast POSTs body", async () => {
    await api.createBroadcast({ title: "방송" } as any);
    const call = (globalThis.fetch as any).mock.calls.at(-1);
    expect(call[0]).toBe("http://localhost:8000/broadcasts");
    expect(call[1].method).toBe("POST");
    expect(JSON.parse(call[1].body).title).toBe("방송");
  });
  it("getStatus hits /status", async () => {
    await api.getStatus();
    const call = (globalThis.fetch as any).mock.calls.at(-1);
    expect(call[0]).toBe("http://localhost:8000/status");
  });
});
