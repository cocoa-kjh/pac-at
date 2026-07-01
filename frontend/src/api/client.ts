import type { Broadcast, Scene, Schedule, Status, SchedulePreflight, BroadcastPreflight } from "../types";
const BASE = "http://localhost:8100";

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" }, ...opts });
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json();
}

export const api = {
  listBroadcasts: () => req<Broadcast[]>("/broadcasts"),
  createBroadcast: (data: Partial<Broadcast>) =>
    req<Broadcast>("/broadcasts", { method: "POST", body: JSON.stringify(data) }),
  createYoutubeEvent: (id: number) =>
    req<Broadcast>(`/broadcasts/${id}/youtube`, { method: "POST" }),
  listScenes: () => req<Scene[]>("/scenes"),
  syncScenes: () => req<{ ok: boolean }>("/scenes/sync", { method: "POST" }),
  listSchedules: () => req<Schedule[]>("/schedules"),
  createSchedule: (data: any) =>
    req<Schedule>("/schedules", { method: "POST", body: JSON.stringify(data) }),
  deleteSchedule: (id: number) =>
    req<{ ok: boolean }>(`/schedules/${id}`, { method: "DELETE" }),
  manualGoLive: (id: number) =>
    req<{ ok: boolean }>(`/schedules/${id}/go-live`, { method: "POST" }),
  manualGoComplete: (id: number) =>
    req<{ ok: boolean }>(`/schedules/${id}/go-complete`, { method: "POST" }),
  preflightSchedule: (id: number) =>
    req<SchedulePreflight>(`/schedules/${id}/preflight`),
  preflightBroadcast: (id: number) =>
    req<BroadcastPreflight>(`/broadcasts/${id}/preflight`),
  getStatus: () => req<Status>("/status"),
};
