import type { Media } from '../types';

function absoluteFrames(tc: string, nominal: number, drop: boolean): number {
  const parts = tc.split(/[:;]/).map(Number);
  if (parts.length !== 4 || parts.some(n => !Number.isFinite(n))) return 0;
  const [h, m, s, f] = parts;
  const minutes = h * 60 + m;
  const dropped = drop ? (nominal === 60 ? 4 : 2) * (minutes - Math.floor(minutes / 10)) : 0;
  return ((h * 3600 + m * 60 + s) * nominal + f) - dropped;
}

/** Timecode labels are integers; HTML5 timestamps themselves remain approximate. */
export function frameTimecode(relative: number, media?: Media | null): string {
  if (!media) return '00:00:00:00';
  const nominal = media.nominal_fps || Math.round(media.fps_numerator / media.fps_denominator) || 25;
  let frames = Math.max(0, Math.floor(relative)) + absoluteFrames(media.start_timecode, nominal, media.drop_frame);
  if (media.drop_frame) {
    const drop = (nominal === 60 ? 4 : 2);
    const tenMinutes = nominal * 600 - drop * 9;
    const minute = nominal * 60 - drop;
    const blocks = Math.floor(frames / tenMinutes);
    const remainder = frames % tenMinutes;
    frames += drop * 9 * blocks + (remainder >= drop ? drop * Math.floor((remainder - drop) / minute) : 0);
  }
  const f = frames % nominal;
  const seconds = Math.floor(frames / nominal);
  return [Math.floor(seconds / 3600), Math.floor(seconds / 60) % 60, seconds % 60, f]
    .map(n => String(n).padStart(2, '0')).join(':').replace(/:(\d\d)$/, `${media.drop_frame ? ';' : ':'}$1`);
}

export function secondsToFrame(seconds: number, media?: Media | null): number {
  if (!media) return 0;
  return Math.max(0, Math.floor(seconds * media.fps_numerator / media.fps_denominator + 0.000001));
}
export function frameToSeconds(frame: number, media?: Media | null): number {
  return media ? frame * media.fps_denominator / media.fps_numerator : 0;
}
export function durationLabel(value: number): string {
  const seconds = Math.max(0, Math.floor(value));
  return `${Math.floor(seconds / 60).toString().padStart(2, '0')}:${(seconds % 60).toString().padStart(2, '0')}`;
}
