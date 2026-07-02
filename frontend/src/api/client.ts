import type { Broadcast, Scene, Schedule, Status, SchedulePreflight, BroadcastPreflight, Series } from "../types";
const BASE = `http://${window.location.hostname}:8100`;

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
  updateBroadcast: (id: number, data: Partial<Broadcast>) =>
    req<Broadcast>(`/broadcasts/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  createYoutubeEvent: (id: number) =>
    req<Broadcast>(`/broadcasts/${id}/youtube`, { method: "POST" }),
  listScenes: () => req<Scene[]>("/scenes"),
  syncScenes: () => req<{ ok: boolean }>("/scenes/sync", { method: "POST" }),
  listSchedules: () => req<Schedule[]>("/schedules"),
  createSchedule: (data: any) =>
    req<Schedule>("/schedules", { method: "POST", body: JSON.stringify(data) }),
  updateSchedule: (id: number, data: any) =>
    req<Schedule>(`/schedules/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
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
  listSeries: () => req<Series[]>("/series"),
  createSeries: (data: any) =>
    req<Series>("/series", { method: "POST", body: JSON.stringify(data) }),
  updateSeries: (id: number, data: any) =>
    req<Series>(`/series/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteSeries: (id: number) =>
    req<{ ok: boolean }>(`/series/${id}`, { method: "DELETE" }),
  listSeriesOccurrences: (id: number) =>
    req<Schedule[]>(`/series/${id}/occurrences`),
  generateSeriesNow: (id: number) =>
    req<Schedule[]>(`/series/${id}/generate`, { method: "POST" }),
};
