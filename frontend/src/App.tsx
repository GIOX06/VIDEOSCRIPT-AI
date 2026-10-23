import { useCallback, useEffect, useRef, useState } from 'react';
import type { CSSProperties } from 'react';
import type { Action, Health, Media, Project, ProjectSummary } from './types';
import { request } from './services/api';
import { frameToSeconds, secondsToFrame } from './services/timecode';
import Player from './components/Player';
import type { PlayerHandle } from './components/Player';
import Editor from './components/Editor';
import Assistant from './components/Assistant';
import Icon from './components/Icon';
import Modal from './components/Modal';

type Dialog = 'new' | 'open' | 'import' | 'export' | 'settings' | 'relink' | null;
export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [connected, setConnected] = useState(false);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [project, setProject] = useState<Project | null>(null);
  const [mediaId, setMediaId] = useState<string | null>(null);
  const [position, setPosition] = useState(0);
  const [inFrame, setInFrame] = useState<number | null>(null);
  const [outFrame, setOutFrame] = useState<number | null>(null);
  const [dialog, setDialog] = useState<Dialog>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(0);
  const [projectName, setProjectName] = useState('');
  const [filePath, setFilePath] = useState('');
  const [importMode, setImportMode] = useState<'path' | 'file'>('path');
  const [file, setFile] = useState<File | null>(null);
  const [showJobs, setShowJobs] = useState(false);
  const [playerWidth, setPlayerWidth] = useState(Number(localStorage.getItem('vs-player-width')) || 35);
  const [assistantWidth, setAssistantWidth] = useState(Number(localStorage.getItem('vs-assistant-width')) || 292);
  const player = useRef<PlayerHandle>(null);
  const activeProjectId = useRef<string | null>(null);
  const media = project?.media.find(item => item.id === mediaId) ?? project?.media[0] ?? null;
  const jobs = project?.jobs ?? [];
  const activeJobs = jobs.filter(job => ['queued', 'running'].includes(job.status));
  const loadProjects = useCallback(async () => {
    const rows = await request<ProjectSummary[]>('/api/projects');
    setProjects(rows);
    return rows;
  }, []);
  const loadProject = useCallback(async (id: string, select = false) => {
    if (select) activeProjectId.current = id;
    const current = await request<Project>(`/api/projects/${id}`);
    if (activeProjectId.current !== id) return;
    setProject(current);
    localStorage.setItem('vs-project-id', id);
    if (select) { setMediaId(current.media[0]?.id ?? null); setPosition(0); setInFrame(null); setOutFrame(null); }
  }, []);
  const refreshHealth = useCallback(async () => {
    try { const value = await request<Health>('/api/health'); setHealth(value); setConnected(true); }
    catch { setConnected(false); }
  }, []);
  useEffect(() => {
    void refreshHealth();
    void loadProjects().then(async rows => {
      const previous = localStorage.getItem('vs-project-id');
      if (previous && rows.some(row => row.id === previous)) await loadProject(previous, true);
    }).catch(err => setError((err as Error).message));
  }, [refreshHealth, loadProject, loadProjects]);
  useEffect(() => {
    if (!project?.id || !activeJobs.length) return;
    const id = project.id;
    const interval = window.setInterval(() => { void loadProject(id).catch(err => setError((err as Error).message)); }, 1000);
    return () => window.clearInterval(interval);
  }, [project?.id, activeJobs.length, loadProject]);
  useEffect(() => { if (!notice) return; const timer = window.setTimeout(() => setNotice(''), 6500); return () => window.clearTimeout(timer); }, [notice]);
  useEffect(() => { localStorage.setItem('vs-player-width', String(playerWidth)); }, [playerWidth]);
  useEffect(() => { localStorage.setItem('vs-assistant-width', String(assistantWidth)); }, [assistantWidth]);
  const action: Action = async (path, body, method) => {
    setBusy(value => value + 1);
    try {
      const result = await request(path, body, method);
      const id = activeProjectId.current;
      if (id) await loadProject(id);
      await loadProjects();
      return result;
    } catch (err) { setError((err as Error).message); throw err; }
    finally { setBusy(value => value - 1); }
  };
  const selectMedia = (id: string) => { setMediaId(id); setPosition(0); setInFrame(null); setOutFrame(null); };
  const seekFrame = (frame: number) => { const seconds = frameToSeconds(frame, media); player.current?.seek(seconds); setPosition(seconds); };
  const setIn = () => setInFrame(secondsToFrame(position, media));
  const setOut = () => setOutFrame(secondsToFrame(position, media));
  const addMarker = () => {
    if (!project || !media) return;
    void action(`/api/projects/${project.id}/annotations`, { media_id: media.id, start_frame: secondsToFrame(position, media), end_frame: null, category: 'General Note', description: 'Marker', origin: 'manual', verification: 'Da verificare', qc_result_id: null }).then(() => setNotice('Marker aggiunto al timecode corrente.')).catch(() => {});
  };
  const createProject = async () => {
    setBusy(value => value + 1);
    try {
      const created = await request<ProjectSummary>('/api/projects', { name: projectName.trim() });
      await loadProjects(); await loadProject(created.id, true);
      setProjectName(''); setDialog(null); setNotice('Progetto creato. Importa il primo media per iniziare.');
    } catch (err) { setError((err as Error).message); }
    finally { setBusy(value => value - 1); }
  };
  const importMedia = async () => {
    if (!project) return;
    try {
      let result: Media;
      if (importMode === 'file') {
        if (!file) return;
        const form = new FormData(); form.append('project_id', project.id); form.append('file', file);
        result = await action('/api/media/upload', form) as Media;
      } else result = await action('/api/media/import', { project_id: project.id, path: filePath.trim() }) as Media;
      selectMedia(result.id); setDialog(null); setFilePath(''); setFile(null); setNotice('Media importato. Il file sorgente resta invariato.');
      if (!result.playback_supported) await action(`/api/media/${result.id}/proxy`, {});
    } catch { /* action reports errors */ }
  };
  const relink = async () => {
    if (!media) return;
    try { await action(`/api/media/${media.id}/relink`, { path: filePath.trim() }); setDialog(null); setFilePath(''); setNotice('Media ricollegato.'); }
    catch { /* action reports errors */ }
  };
  return <main className="studio-shell">
    <header className="app-header">
      <div className="brand"><div className="brand-mark" aria-hidden="true">V<span>›</span></div><div><h1>VideoScript <span>AI STUDIO</span></h1><small>LOCAL POST-PRODUCTION WORKSPACE</small></div></div>
      <nav className="main-toolbar" aria-label="Azioni progetto">
        <button className="button" onClick={() => setDialog('new')}><Icon name="plus" />Nuovo progetto</button>
        <button className="button" onClick={() => { void loadProjects().catch(err => setError((err as Error).message)); setDialog('open'); }}><Icon name="folder" />Apri</button>
        <span className="toolbar-divider" />
        <button className="button accent" disabled={!project || busy > 0} onClick={() => setDialog('import')}><Icon name="upload" />Importa video</button>
        <button className="button" disabled={!project || busy > 0} onClick={() => { if (project) void action(`/api/projects/${project.id}/save`, {}).then(() => setNotice('Progetto salvato su SQLite.')).catch(() => {}); }}><Icon name="save" /><span className="hide-medium">Salva</span></button>
        <button className="button" disabled={!project} onClick={() => setDialog('export')}><Icon name="download" /><span className="hide-medium">Esporta</span></button>
        <button className="icon-button" aria-label="Impostazioni" title="Impostazioni" onClick={() => { void refreshHealth(); setDialog('settings'); }}><Icon name="settings" size={19} /></button>
      </nav>
    </header>
    <div className="project-strip"><div className="project-breadcrumb"><Icon name="folder" size={14} /><span>PROGETTO</span><strong>{project?.name ?? 'Nessun progetto aperto'}</strong>{project && <span className="autosave-label">● Salvataggio automatico</span>}</div><div className="project-media"><label className="sr-only" htmlFor="active-media">Media attivo</label><select id="active-media" value={media?.id ?? ''} onChange={e => selectMedia(e.target.value)} disabled={!project?.media.length}><option value="" disabled>Seleziona un media</option>{project?.media.map(item => <option value={item.id} key={item.id}>{item.name}{!item.available ? ' · mancante' : ''}</option>)}</select>{media && <button className="text-button" onClick={() => setDialog('relink')}>Ricollega</button>}<span className="local-badge"><span className="status-dot active" /> SOLO LOCALE</span></div></div>
    {error && <div className="error-banner" role="alert"><Icon name="info" /><span>{error}</span><button className="icon-button" aria-label="Chiudi errore" onClick={() => setError('')}><Icon name="close" /></button></div>}
    {notice && <div className="notice-banner" role="status"><Icon name="check" /><span>{notice}</span><button className="icon-button" aria-label="Chiudi messaggio" onClick={() => setNotice('')}><Icon name="close" /></button></div>}
    <div className="workbench" style={{ '--player-width': `${playerWidth}%`, '--assistant-width': `${assistantWidth}px` } as CSSProperties}>
      <Player ref={player} media={media} position={position} onPosition={setPosition} inFrame={inFrame} outFrame={outFrame} onSetIn={setIn} onSetOut={setOut} onMarker={addMarker} action={action} onError={setError} />
      {project ? <Editor project={project} media={media} position={position} inFrame={inFrame} outFrame={outFrame} onSeek={seekFrame} onSetIn={setIn} onSetOut={setOut} action={action} onError={setError} /> : <section className="empty-workspace panel"><span className="eyebrow">IL TUO STUDIO, IL TUO FLUSSO</span><h2>Ogni dettaglio.<br /><span>Al suo timecode.</span></h2><p>Annota, trascrivi e verifica i tuoi contenuti audiovisivi. Un ambiente di lavoro locale, progettato per tenere tutto sotto controllo.</p><button className="button accent" onClick={() => setDialog('new')}><Icon name="plus" />Crea il primo progetto</button><div className="workflow-steps"><div><b>01</b><span>Importa il tuo media</span></div><div><b>02</b><span>Annota e analizza</span></div><div><b>03</b><span>Esporta il tuo lavoro</span></div></div><div className="privacy-note"><Icon name="info" /><span>Nessun media o trascrizione viene inviato automaticamente a servizi esterni.</span></div></section>}
      <Assistant llmAvailable={health?.assistant?.llm_available ?? false} project={project} media={media} position={position} inFrame={inFrame} outFrame={outFrame} action={action} />
    </div>
    {showJobs && <section className="jobs-drawer" aria-label="Elaborazioni"><div className="jobs-title"><strong>Elaborazioni del progetto</strong><button className="icon-button" aria-label="Chiudi elaborazioni" onClick={() => setShowJobs(false)}><Icon name="close" /></button></div>{!jobs.length && <p className="help-text">Nessuna elaborazione avviata.</p>}{[...jobs].reverse().map(job => <div key={job.id} className="job-row"><span className={`status-dot ${job.status === 'completed' ? 'active' : ''}`} /><strong>{job.kind}</strong><span>{job.message || job.status}</span><progress value={job.progress} max={100} /><small>{Math.round(job.progress)}% · {job.status}</small>{['queued', 'running'].includes(job.status) && <button className="button small" onClick={() => { void action(`/api/jobs/${job.id}/cancel`, {}).catch(() => {}); }}>Annulla</button>}{job.error && <p className="job-error">{job.error}</p>}</div>)}</section>}
    <footer className="status-bar"><div><span className={`status-dot ${connected ? 'active' : ''}`} /><span>{connected ? 'Backend locale connesso' : 'Backend non raggiungibile'}</span><button className="text-button" onClick={() => { void refreshHealth(); void loadProjects().catch(err => setError((err as Error).message)); }}>Riconnetti</button></div><button className="jobs-toggle" onClick={() => setShowJobs(!showJobs)}>{activeJobs.length > 0 && <span className="spinner" />}{activeJobs.length ? `${activeJobs.length} elaborazioni in corso` : 'Elaborazioni'}<span>{showJobs ? '⌄' : '⌃'}</span></button><span>{busy ? 'Salvataggio / caricamento…' : project ? `${project.annotations.length} annotazioni · ${project.media.length} media` : 'Pronto per un nuovo progetto'}</span></footer>
    {dialog === 'new' && <Modal error={error} title="Nuovo progetto" onClose={() => setDialog(null)}><form onSubmit={e => { e.preventDefault(); void createProject(); }}><p className="modal-description">Il progetto conserva annotazioni, trascrizioni e risultati QC nel database locale.</p><label>Nome del progetto<input autoFocus maxLength={160} required value={projectName} onChange={e => setProjectName(e.target.value)} placeholder="Es. Episodio 01 · Revisione italiana" /></label><div className="modal-actions"><button type="button" className="button" onClick={() => setDialog(null)}>Annulla</button><button className="button accent" disabled={!projectName.trim() || busy > 0}>Crea progetto</button></div></form></Modal>}
    {dialog === 'open' && <Modal error={error} title="Apri progetto" onClose={() => setDialog(null)}><p className="modal-description">Progetti salvati su questo computer.</p><div className="project-list">{projects.length === 0 && <p>Nessun progetto salvato. Crea il primo progetto per iniziare.</p>}{projects.map(item => <button key={item.id} onClick={() => { void loadProject(item.id, true).then(() => setDialog(null)).catch(err => setError((err as Error).message)); }}><Icon name="folder" size={21} /><span><strong>{item.name}</strong><small>{new Date(item.updated_at).toLocaleString('it-IT')}</small></span><span>↗</span></button>)}</div></Modal>}
    {dialog === 'import' && <Modal error={error} title="Importa video" onClose={() => setDialog(null)}><p className="modal-description">Formati supportati: MP4, MOV, MXF, WebM. Il file sorgente non viene modificato.</p><div className="segmented"><button className={importMode === 'path' ? 'active' : ''} onClick={() => setImportMode('path')}>Percorso locale · senza copia</button><button className={importMode === 'file' ? 'active' : ''} onClick={() => setImportMode('file')}>Seleziona file · copia locale</button></div><form onSubmit={e => { e.preventDefault(); void importMedia(); }}>{importMode === 'path' ? <label>Percorso assoluto del video<input autoFocus required value={filePath} onChange={e => setFilePath(e.target.value)} placeholder="C:\Video\filmato.mp4 oppure /Users/nome/Video/filmato.mov" /></label> : <label className="file-drop"><Icon name="upload" size={26} /><strong>Scegli un video dal computer</strong><input aria-label="File video da importare" type="file" accept=".mp4,.mov,.mxf,.webm" required onChange={e => setFile(e.target.files?.[0] ?? null)} /><small>Il browser copia il file nell’archivio locale dell’app. Per evitare la copia, usa il percorso assoluto.</small></label>}<p className="help-text">Avvia l’app sul tuo computer per usare i tuoi media. La selezione di un file trasferisce i dati al backend di questa istanza dell’app.</p><div className="modal-actions"><button className="button" type="button" onClick={() => setDialog(null)}>Annulla</button><button className="button accent" disabled={busy > 0 || (importMode === 'path' ? !filePath.trim() : !file)}>{busy ? 'Importazione…' : 'Importa video'}</button></div></form></Modal>}
    {dialog === 'relink' && <Modal error={error} title="Ricollega file sorgente" onClose={() => setDialog(null)}><form onSubmit={e => { e.preventDefault(); void relink(); }}><p className="modal-description">Seleziona lo stesso contenuto originale. Verifica che durata e frame rate coincidano prima di riutilizzare i timecode.</p><label>Nuovo percorso assoluto<input autoFocus required value={filePath} onChange={e => setFilePath(e.target.value)} placeholder={media?.path ?? ''} /></label><div className="modal-actions"><button type="button" className="button" onClick={() => setDialog(null)}>Annulla</button><button className="button accent" disabled={!filePath.trim() || busy > 0}>Verifica e ricollega</button></div></form></Modal>}
    {dialog === 'export' && project && <Modal error={error} title="Esporta progetto" onClose={() => setDialog(null)}><p className="modal-description">Esporta i dati reali del progetto. I file video non sono inclusi.</p><div className="export-list">{[{ format: 'txt', name: 'Testo semplice', description: 'Report leggibile con timecode e note' }, { format: 'csv', name: 'CSV UTF-8', description: 'Annotazioni compatibili con Excel' }, { format: 'json', name: 'JSON completo', description: 'Dati strutturati di tutto il progetto' }, { format: 'srt', name: 'Sottotitoli SRT', description: 'Segmenti della trascrizione con inizio e fine' }].map(item => <a key={item.format} className="export-item" href={`/api/projects/${project.id}/export?format=${item.format}${item.format === 'srt' && media ? `&media_id=${media.id}` : ''}`} download><span className="format-label">{item.format.toUpperCase()}</span><span><strong>{item.name}</strong><small>{item.description}</small></span><Icon name="download" /></a>)}</div><p className="help-text">SRT disponibile solo quando sono presenti segmenti trascritti. PDF previsto in una versione successiva.</p></Modal>}
    {dialog === 'settings' && <Modal error={error} title="Impostazioni dello studio" onClose={() => setDialog(null)} wide><div className="settings-grid"><section><h3>Layout dei pannelli</h3><label>Larghezza monitor: {playerWidth}%<input type="range" min="27" max="45" value={playerWidth} onChange={e => setPlayerWidth(Number(e.target.value))} /></label><label>Larghezza assistente: {assistantWidth} px<input type="range" min="250" max="380" value={assistantWidth} onChange={e => setAssistantWidth(Number(e.target.value))} /></label><p className="help-text">Le larghezze si adattano automaticamente agli schermi più piccoli.</p></section><section><h3>Motori locali</h3><dl className="engine-list"><dt>Backend</dt><dd>{connected ? 'Connesso' : 'Non raggiungibile'}</dd><dt>FFmpeg</dt><dd>{health?.ffmpeg ? 'Disponibile' : 'Non disponibile'}</dd><dt>FFprobe</dt><dd>{health?.ffprobe ? 'Disponibile' : 'Non disponibile'}</dd><dt>faster-whisper</dt><dd>{health?.transcription?.installed ? 'Installato' : 'Non installato'}</dd><dt>Modello di trascrizione</dt><dd>{health?.transcription?.model_configured ? 'Configurato' : 'Non configurato'}</dd><dt>LLM generativo</dt><dd>Modello AI non configurato</dd></dl><p className="help-text">Installa l’extra AI e configura il percorso del modello locale seguendo il README. Il player e l’editor funzionano anche senza AI.</p><button className="button small" onClick={() => { void refreshHealth(); }}>Verifica motori</button></section></div><div className="shortcut-guide"><h3>Scorciatoie del player</h3><p><kbd>Spazio</kbd> Play/Pausa <kbd>←</kbd> <kbd>→</kbd> Fotogramma <kbd>J</kbd> −1 secondo <kbd>K</kbd> Pausa <kbd>L</kbd> Play <kbd>I</kbd> IN <kbd>O</kbd> OUT <kbd>M</kbd> Marker</p><p className="help-text">Le scorciatoie sono disattivate durante la scrittura. La riproduzione inversa continua non è supportata.</p></div><p className="privacy-note"><Icon name="info" /> Il backend ascolta su 127.0.0.1. Nessun servizio cloud è attivo per impostazione predefinita.</p></Modal>}
  </main>;
}
