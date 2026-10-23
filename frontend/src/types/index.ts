export interface Health {
  status: string; ffmpeg: boolean; ffprobe: boolean;
  transcription: { installed: boolean; model_configured: boolean; model_path?: string | null };
  assistant: { llm_available: boolean; model?: string; message?: string };
}
export interface Media {
  id: string; project_id: string; name: string; path: string;
  metadata: Record<string, unknown>;
  fps_numerator: number; fps_denominator: number; nominal_fps: number;
  drop_frame: boolean; original_timecode: string | null; start_timecode: string;
  media_duration: number; source_frame_index?: number; variable_frame_rate: boolean;
  playback_supported: boolean; proxy_path: string | null; available: boolean; warnings: string[];
}
export interface Annotation {
  id: string; project_id: string; media_id: string; start_frame: number; end_frame: number | null;
  tc_in: string; tc_out: string | null; category: string; description: string; origin: string;
  verification: string; qc_result_id: string | null; created_at: string; updated_at: string;
}
export interface Transcript {
  id: string; media_id: string; start: number; end: number; start_frame: number; end_frame: number;
  tc_in: string; tc_out: string; text: string; verification: string; uncertainty: string[];
}
export interface QCResult {
  id: string; media_id: string; test: string; status: 'PASS' | 'WARNING' | 'FAIL' | 'NOT TESTED';
  start_frame: number | null; end_frame: number | null; tc_in: string | null; tc_out: string | null;
  description: string; measured: unknown; threshold: unknown; verification: string;
}
export interface Job {
  id: string; kind: string; media_id: string; project_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'interrupted';
  progress: number; message: string; error: string | null; result: unknown;
}
export interface ChatMessage { id: string; role: 'user' | 'assistant'; content: string; created_at?: string }
export interface ProjectSummary { id: string; name: string; created_at: string; updated_at: string }
export interface Project extends ProjectSummary {
  media: Media[]; annotations: Annotation[]; transcripts: Transcript[]; qc_results: QCResult[];
  chat: ChatMessage[]; jobs: Job[];
}
export type Action = (path: string, body?: unknown, method?: string) => Promise<unknown>;
