import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';
import type { Action, Media } from '../types';
import { durationLabel, frameTimecode, secondsToFrame } from '../services/timecode';
import { request } from '../services/api';
import Icon from './Icon';

export interface PlayerHandle { seek: (seconds: number) => void }
interface Props {
  media: Media | null; position: number; onPosition: (seconds: number) => void;
  inFrame: number | null; outFrame: number | null; onSetIn: () => void; onSetOut: () => void;
  onMarker: () => void; action: Action; onError: (message: string) => void;
}
const Player = forwardRef<PlayerHandle, Props>(function Player({ media, position, onPosition, inFrame, outFrame, onSetIn, onSetOut, onMarker, action, onError }, ref) {
  const video = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);
  const [volume, setVolume] = useState(1);
  const [muted, setMuted] = useState(false);
  const [rate, setRate] = useState(1);
  const [jumpTC, setJumpTC] = useState('');
  const [startTC, setStartTC] = useState('00:00:00:00');
  const [dropFrame, setDropFrame] = useState(false);
  const [playbackError, setPlaybackError] = useState(false);
  const playable = Boolean(media && media.available && (media.playback_supported || media.proxy_path));
  const duration = media?.media_duration ?? 0;
  const frame = secondsToFrame(position, media);
  const fps = media ? media.fps_numerator / media.fps_denominator : 25;
  const seek = (value: number) => {
    if (!video.current || !media) return;
    const safe = Math.max(0, Math.min(value, duration));
    video.current.currentTime = safe;
    onPosition(safe);
  };
  const play = () => { video.current?.play().catch(error => onError(`Riproduzione non disponibile: ${error.message}. Prova a generare il proxy.`)); };
  const toggle = () => { if (video.current?.paused) play(); else video.current?.pause(); };
  useImperativeHandle(ref, () => ({ seek }));
  useEffect(() => { setStartTC(media?.start_timecode ?? '00:00:00:00'); setDropFrame(media?.drop_frame ?? false); }, [media?.id, media?.start_timecode, media?.drop_frame]);
  useEffect(() => { setPlaying(false); setPlaybackError(false); setJumpTC(''); }, [media?.id, media?.proxy_path]);
  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      if (!playable || event.altKey || event.ctrlKey || event.metaKey || target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON'].includes(target.tagName)) return;
      const command = event.key.toLowerCase();
      if (![' ', 'arrowleft', 'arrowright', 'j', 'k', 'l', 'i', 'o', 'm'].includes(command)) return;
      event.preventDefault();
      const current = video.current?.currentTime ?? position;
      if (command === ' ') toggle();
      if (command === 'arrowleft') { video.current?.pause(); seek(current - 1 / fps); }
      if (command === 'arrowright') { video.current?.pause(); seek(current + 1 / fps); }
      if (command === 'j') seek(current - 1);
      if (command === 'k') video.current?.pause();
      if (command === 'l') play();
      if (command === 'i') onSetIn();
      if (command === 'o') onSetOut();
      if (command === 'm') onMarker();
    };
    window.addEventListener('keydown', key);
    return () => window.removeEventListener('keydown', key);
  });
  const applyTimecode = async () => {
    if (!media) return;
    try { await action(`/api/media/${media.id}/timecode`, { start_timecode: startTC, drop_frame: dropFrame }, 'PATCH'); }
    catch { /* action reports errors. */ }
  };
  const goTimecode = async () => {
    if (!media) return;
    try {
      const result = await request<{ seconds: number }>(`/api/media/${media.id}/seek`, { timecode: jumpTC });
      seek(result.seconds);
    } catch (error) { onError((error as Error).message); }
  };
  return <section className="player-panel panel">
    <div className="panel-heading"><span><Icon name="film" /> MONITOR SORGENTE</span><span className="tiny-tag">{media?.proxy_path ? 'PROXY' : 'ORIGINALE'}</span></div>
    <div className="video-stage">
      {playable && <video key={`${media!.id}-${media!.proxy_path ?? ''}`} ref={video} src={`/api/media/${media!.id}/stream`} preload="metadata" playsInline
        onTimeUpdate={e => onPosition(e.currentTarget.currentTime)} onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)} onError={() => setPlaybackError(true)}
        onLoadedMetadata={e => { e.currentTarget.volume = volume; e.currentTarget.muted = muted; e.currentTarget.playbackRate = rate; }} />}
      {(!playable || playbackError) && <div className="video-empty"><div className="film-outline"><Icon name="film" size={37} /></div><strong>{!media ? 'Il tuo prossimo progetto inizia qui' : !media.available ? 'File sorgente non disponibile' : 'Il codec richiede un proxy'}</strong><p>{!media ? 'Crea un progetto e importa un video per iniziare.' : !media.available ? 'Ricollega il file originale dalle impostazioni del media.' : 'Genera un MP4 H.264/AAC per riprodurre questo media.'}</p>
        {media?.available && <button className="button accent" onClick={() => { void action(`/api/media/${media.id}/proxy`, {}).catch(() => {}); }}>Genera proxy locale</button>}
      </div>}
      {media && <div className="monitor-label"><span className="record-dot" />{media.name}</div>}
    </div>
    <div className="timecode-row"><div><span className="eyebrow">TIMECODE</span><output className="timecode">{frameTimecode(frame, media)}</output></div><div className="tc-mode"><span>{media ? `${media.fps_numerator}/${media.fps_denominator} fps · ${media.drop_frame ? 'DF' : 'NDF'}` : '— fps'}</span><small>Player HTML5 · navigazione approssimata</small></div></div>
    <div className="timeline-wrap"><div className="timeline-labels"><span>{frameTimecode(0, media)}</span><span>{durationLabel(duration)}</span></div><input aria-label="Posizione del video" className="timeline" type="range" min="0" max={duration || 1} step={1 / fps} value={Math.min(position, duration)} disabled={!playable} onChange={e => seek(Number(e.target.value))} /><div className="selection-label">IN <b>{inFrame === null ? '—' : frameTimecode(inFrame, media)}</b><span>OUT <b>{outFrame === null ? '—' : frameTimecode(outFrame, media)}</b></span></div></div>
    <div className="transport" role="group" aria-label="Controlli di riproduzione">
      <button className="icon-button" title="Indietro 5 secondi" aria-label="Indietro 5 secondi" disabled={!playable} onClick={() => seek(position - 5)}>−5</button>
      <button className="icon-button" title="Indietro 1 secondo (J)" aria-label="Indietro 1 secondo" disabled={!playable} onClick={() => seek(position - 1)}>−1</button>
      <button className="icon-button" title="Fotogramma precedente (←), approssimato" aria-label="Fotogramma precedente" disabled={!playable} onClick={() => { video.current?.pause(); seek(position - 1 / fps); }}><Icon name="backward" /></button>
      <button className="play-button" title="Play/Pausa (Spazio)" aria-label={playing ? 'Pausa' : 'Riproduci'} disabled={!playable} onClick={toggle}><Icon name={playing ? 'pause' : 'play'} size={19} /></button>
      <button className="icon-button" title="Stop" aria-label="Stop" disabled={!playable} onClick={() => { video.current?.pause(); seek(0); }}><Icon name="stop" size={13} /></button>
      <button className="icon-button" title="Fotogramma successivo (→), approssimato" aria-label="Fotogramma successivo" disabled={!playable} onClick={() => { video.current?.pause(); seek(position + 1 / fps); }}><Icon name="forward" /></button>
      <button className="icon-button" title="Avanti 1 secondo" aria-label="Avanti 1 secondo" disabled={!playable} onClick={() => seek(position + 1)}>+1</button>
      <button className="icon-button" title="Avanti 5 secondi" aria-label="Avanti 5 secondi" disabled={!playable} onClick={() => seek(position + 5)}>+5</button>
    </div>
    <div className="secondary-controls"><button className="icon-button" title="Mute" aria-label={muted ? 'Attiva audio' : 'Disattiva audio'} disabled={!playable} onClick={() => { if (video.current) video.current.muted = !muted; setMuted(!muted); }}><Icon name={muted ? 'muted' : 'volume'} /></button><input aria-label="Volume" type="range" min="0" max="1" step="0.01" value={volume} disabled={!playable} onChange={e => { const value = Number(e.target.value); setVolume(value); if (video.current) video.current.volume = value; }} /><select aria-label="Velocità riproduzione" value={rate} onChange={e => { const value = Number(e.target.value); setRate(value); if (video.current) video.current.playbackRate = value; }}>{[0.25, 0.5, 0.75, 1, 1.5, 2].map(n => <option key={n} value={n}>{n}×</option>)}</select><button className="icon-button" aria-label="Schermo intero" disabled={!playable} onClick={() => { video.current?.requestFullscreen().catch(error => onError((error as Error).message)); }}><Icon name="fullscreen" /></button></div>
    <div className="mark-controls"><button className="button small" disabled={!media} onClick={onSetIn}><kbd>I</kbd> Imposta IN</button><button className="button small" disabled={!media} onClick={onSetOut}><kbd>O</kbd> Imposta OUT</button><button className="button small" disabled={!media} onClick={onMarker}><kbd>M</kbd> Marker</button></div>
    <form className="jump-form" onSubmit={e => { e.preventDefault(); void goTimecode(); }}><input aria-label="Timecode di destinazione" placeholder="HH:MM:SS:FF" value={jumpTC} disabled={!media} onChange={e => setJumpTC(e.target.value)} /><button className="button small" disabled={!media || !jumpTC}>Vai al TC</button></form>
    {media && <details className="media-details"><summary>Informazioni tecniche <span>{media.metadata.width ? `${media.metadata.width} × ${media.metadata.height}` : ''}</span></summary><dl><dt>Contenitore</dt><dd>{String(media.metadata.container ?? '—')}</dd><dt>Codec video / audio</dt><dd>{String(media.metadata.video_codec ?? '—')} / {String(media.metadata.audio_codec ?? '—')}</dd><dt>Audio</dt><dd>{String(media.metadata.sample_rate ?? '—')} Hz · {String(media.metadata.channels ?? '—')} canali</dd><dt>Tracce audio</dt><dd>{Array.isArray(media.metadata.audio_tracks) ? media.metadata.audio_tracks.length : String(media.metadata.audio_tracks ?? '—')}</dd><dt>Bitrate</dt><dd>{String(media.metadata.bit_rate ?? '—')}</dd><dt>Pixel / campi</dt><dd>{String(media.metadata.pixel_format ?? '—')} / {String(media.metadata.field_order ?? '—')}</dd><dt>TC origine</dt><dd>{media.original_timecode ?? 'Non presente'}</dd><dt>Percorso</dt><dd className="path-value">{media.path}</dd></dl>
      <label>TC iniziale<input value={startTC} onChange={e => setStartTC(e.target.value)} /></label><label className="check-label"><input type="checkbox" checked={dropFrame} onChange={e => setDropFrame(e.target.checked)} /> Drop Frame</label><button className="button small" onClick={() => { void applyTimecode(); }}>Salva impostazioni TC</button>
      <p className="help-text">Il TC usa il frame rate razionale del flusso; il seek del browser non garantisce precisione al fotogramma. J sposta indietro di 1 secondo.</p>
      {media.warnings?.map((warning, index) => <p className="inline-warning" key={index}>{warning}</p>)}
      <button className="button small" onClick={() => { void action(`/api/media/${media.id}/proxy`, {}).catch(() => {}); }}>Rigenera proxy</button>
    </details>}
  </section>;
});
export default Player;
