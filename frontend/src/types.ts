export interface Broadcast {
  id: number;
  title: string;
  description: string;
  privacy: string;
  youtube_broadcast_id: string | null;
  status: string;
}
export interface Scene {
  id: number;
  name: string;
  obs_scene_name: string;
  note: string;
  active: boolean;
}
export interface SequenceItem {
  scene_id: number;
  order_index: number;
  duration_seconds: number | null;
}
export interface Schedule {
  id: number;
  broadcast_id: number;
  series_id: number | null;
  start_at: string;
  end_at: string;
  recurrence: string;
  recurrence_rule: string | null;
  status: string;
  items: SequenceItem[];
}
export interface Series {
  id: number;
  first_start_at: string;
  duration_seconds: number;
  recurrence_rule: string;
  title_template: string;
  description_template: string;
  privacy: string;
  lead_time_days: number;
  active: boolean;
  youtube_stream_id: string | null;
  last_generated_start: string | null;
  generation_error: string | null;
  items: SequenceItem[];
}
export interface Status {
  obs_connected: boolean;
  youtube_authed: boolean;
  next_schedule: { id: number; start_at: string } | null;
  live: boolean;
}
export interface SchedulePreflightItem {
  order_index: number;
  scene_name: string | null;
  exists: boolean;
  role: "first" | "mid";
}
export interface SchedulePreflight {
  ok: boolean;
  obs_connected: boolean;
  youtube_authed: boolean;
  broadcast_ready: boolean;
  first_scene_ok: boolean;
  items: SchedulePreflightItem[];
  problems: string[];
}
export interface BroadcastPreflight {
  ok: boolean;
  youtube_authed: boolean;
  has_event: boolean;
  has_key: boolean;
  problems: string[];
}
