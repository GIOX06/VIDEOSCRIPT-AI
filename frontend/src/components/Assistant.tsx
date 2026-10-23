import { useEffect, useRef, useState } from 'react';
import type { Action, Media, Project } from '../types';
import { frameTimecode } from '../services/timecode';
import Icon from './Icon';

interface Props { project: Project | null; media: Media | null; position: number; inFrame: number | null; outFrame: number | null; action: Action; llmAvailable: boolean }
export default function Assistant({ project, media, position, inFrame, outFrame, action, llmAvailable }: Props) {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<'base' | 'llm'>('base');
  useEffect(() => { if (!llmAvailable) setMode('base'); }, [llmAvailable]);
  const [pending, setPending] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, [project?.chat.length]);
  const ask = async (text: string) => {
    if (!project || !text.trim() || pending) return;
    setPending(true);
    try {
      await action('/api/assistant/query', { project_id: project.id, media_id: media?.id ?? null, query: text.trim(), position, in_frame: inFrame, out_frame: outFrame, mode });
      setQuery('');
    } catch { /* The parent displays a persistent error. */ }
    finally { setPending(false); }
  };
  return <aside className="assistant-panel panel">
    <div className="panel-heading"><span><Icon name="chat" /> ASSISTENTE</span><span className="tiny-tag">LOCALE</span></div>
    <div className="assistant-mode"><span className="status-dot active" /><strong>{mode === 'llm' ? 'LLM locale · generativo' : 'Consultazione base'}</strong><small>{llmAvailable ? 'Modello locale disponibile' : 'Modello AI non configurato'}</small></div>
    <>{llmAvailable && <label className="assistant-mode-select">Modalità<select aria-label="Modalità assistente" value={mode} onChange={e => setMode(e.target.value as 'base' | 'llm')}><option value="base">Consultazione base</option><option value="llm">LLM locale (generativo)</option></select></label>}</><div className="assistant-context"><span>Contesto del progetto</span><strong>{project?.name ?? 'Nessun progetto aperto'}</strong>{media && <small>{inFrame !== null ? `${frameTimecode(inFrame, media)} → ${outFrame !== null ? frameTimecode(outFrame, media) : 'posizione corrente'}` : 'Annotazioni, trascrizioni e QC'}</small>}</div>
    <div className="chat-history" aria-live="polite" aria-label="Cronologia della chat">
      {!project?.chat.length && <div className="assistant-welcome"><div className="assistant-orbit"><Icon name="chat" size={25} /></div><h3>Consulta il tuo progetto.</h3><p>Trova dialoghi, note e rilievi reali. Nessuna immagine viene analizzata in questa modalità.</p><div className="prompt-list">{['Quali problemi QC sono stati rilevati?', 'Elenca le annotazioni degli ultimi 30 secondi.', 'Mostrami cosa viene detto in questa scena.'].map(prompt => <button key={prompt} disabled={!project || pending} onClick={() => { void ask(prompt); }}>{prompt}<span>↗</span></button>)}</div></div>}
      {project?.chat.map(message => <article className={`chat-message ${message.role}`} key={message.id}><span>{message.role === 'user' ? 'TU' : 'CONSULTAZIONE LOCALE'}</span><p>{message.content}</p></article>)}
      {pending && <p className="help-text">Consultazione dei dati del progetto…</p>}<div ref={bottom} />
    </div>
    <form className="chat-composer" onSubmit={e => { e.preventDefault(); void ask(query); }}><label className="sr-only" htmlFor="assistant-query">Domanda all'assistente</label><textarea id="assistant-query" placeholder="Cerca tra i dati del progetto…" value={query} disabled={!project || pending} rows={3} onChange={e => setQuery(e.target.value)} /><div><span>Nessuna modifica automatica alle note</span><button className="send-button" aria-label="Invia domanda" disabled={!project || !query.trim() || pending}><Icon name="send" /></button></div></form>
  </aside>;
}
