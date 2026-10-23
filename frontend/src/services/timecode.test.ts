import { describe, expect, it } from 'vitest';
import type { Media } from '../types';
import { frameTimecode, frameToSeconds, secondsToFrame } from './timecode';

const media = (numerator = 25, denominator = 1, drop = false, start = '00:00:00:00') => ({
  fps_numerator: numerator, fps_denominator: denominator,
  nominal_fps: Math.round(numerator / denominator), drop_frame: drop, start_timecode: start,
}) as Media;

describe('timecode del monitor sorgente', () => {
  it('converte i frame a 25 fps e applica il TC iniziale', () => {
    expect(frameTimecode(24, media())).toBe('00:00:00:24');
    expect(frameTimecode(25, media())).toBe('00:00:01:00');
    expect(frameTimecode(25, media(25, 1, false, '01:00:00:00'))).toBe('01:00:01:00');
  });
  it('salta le etichette DF al minuto conservandole al decimo minuto', () => {
    const df = media(30000, 1001, true);
    expect(frameTimecode(1799, df)).toBe('00:00:59;29');
    expect(frameTimecode(1800, df)).toBe('00:01:00;02');
    expect(frameTimecode(17982, df)).toBe('00:10:00;00');
    expect(frameTimecode(107892, df)).toBe('01:00:00;00');
    expect(frameTimecode(0, media(30000, 1001, true, '00:01:00;02'))).toBe('00:01:00;02');
  });
  it('gestisce DF a 59.94 fps', () => {
    expect(frameTimecode(3600, media(60000, 1001, true))).toBe('00:01:00;04');
    expect(frameTimecode(35964, media(60000, 1001, true))).toBe('00:10:00;00');
  });
  it('mantiene le ore oltre 24 come il backend', () => {
    expect(frameTimecode(25 * 60 * 60 * 25, media())).toBe('25:00:00:00');
    expect(frameTimecode(107892 * 25, media(30000, 1001, true))).toBe('25:00:00;00');
  });
  it('usa il frame rate razionale per i timestamp del browser', () => {
    const ntsc = media(30000, 1001);
    expect(frameToSeconds(30000, ntsc)).toBe(1001);
    expect(secondsToFrame(1001, ntsc)).toBe(30000);
    expect(secondsToFrame(60, ntsc)).toBe(1798);
  });
});
