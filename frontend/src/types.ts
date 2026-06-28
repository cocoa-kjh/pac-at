export interface Broadcast {
  id: number; title: string; description: string; privacy: string;
  youtube_broadcast_id: string | null; status: string;
}
export interface Scene { id: number; name: string; obs_scene_name: string; note: string; }
export interface SequenceItem { scene_id: number; order_index: number; duration_seconds: number | null; }
export interface Schedule {
  id: number; broadcast_id: number; start_at: string; end_at: string;
  recurrence: string; status: string;
}
export interface Status {
  obs_connected: boolean; youtube_authed: boolean;
  next_schedule: { id: number; start_at: string } | null; live: boolean;
}
