import { useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import type { Action, Annotation, Media, Project, QCResult, Transcript } from '../types';
import { frameTimecode, frameToSeconds, secondsToFrame } from '../services/timecode';
import './editor.css';

export interface EditorProps {
  project: Project; media: Media | null; position: number; inFrame: number | null; outFrame: number | null;
  onSeek: (frame: number) => void; onSetIn: () => void; onSetOut: () => void;
  action: Action; onError: (message: string) => void;
}

const CATEGORIES = ['Dialogue', 'Visual Description', 'Sound Effect', 'Music', 'Audio QC', 'Video QC', 'Technical QC', 'Dubbing Note', 'General Note'];
const LABELS: Record<string, string> = {
  Dialogue: 'Dialogo', 'Visual Description': 'Descrizione visiva', 'Sound Effect': 'Effetto sonoro', Music: 'Musica',
  'Audio QC': 'QC audio', 'Video QC': 'QC video', 'Technical QC': 'QC tecnico', 'Dubbing Note': 'Nota doppiaggio', 'General Note': 'Nota generale',
};
const ERROR = (error: unknown) => error instanceof Error ? error.message : String(error);
const measuredLabel = (value: unknown) => value === null || value === undefined ? '—' : typeof value === 'object' ? JSON.stringify(value) : String(value);

export default function Editor(props: EditorProps) {
  const { project, media, position, inFrame, outFrame, onSeek, onSetIn, onSetOut, action, onError } = props;
  const [tab, setTab] = useState<'annotations' | 'transcripts' | 'qc'>('annotations');
  const [busy, setBusy] = useState(false);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('');
  const [editing, setEditing] = useState<string | null>(null);
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('General Note');
  const [verification, setVerification] = useState('Da verificare');
  const [draftStart, setDraftStart] = useState<number | null>(null);
  const [draftEnd, setDraftEnd] = useState<number | null>(null);
  const [omitEnd, setOmitEnd] = useState(false);
  const [qcLink, setQcLink] = useState('');
  const [language, setLanguage] = useState('');
  const [modelPath, setModelPath] = useState('');
  const [selectionOnly, setSelectionOnly] = useState(false);
  const [qcSettings, setQcSettings] = useState({
    black_duration: 0.3, black_threshold: 0.1, silence_duration: 0.5, silence_threshold_db: -40,
    preset: 'source', expected_duration: '', duration_tolerance: 1, peak_threshold_db: -1,
  });
  const currentFrame = secondsToFrame(position, media);
  const annotations = useMemo(() => (project.annotations ?? []).filter(item => item.media_id === media?.id).sort((a, b) => a.start_frame - b.start_frame), [project.annotations, media?.id]);
  const transcripts = useMemo(() => (project.transcripts ?? []).filter(item => item.media_id === media?.id).sort((a, b) => a.start - b.start), [project.transcripts, media?.id]);
  const results = useMemo(() => (project.qc_results ?? []).filter(item => item.media_id === media?.id), [project.qc_results, media?.id]);
  const visible = annotations.filter(item => (!filter || item.category === filter) && (!search || `${item.description} ${item.tc_in}`.toLocaleLowerCase('it').includes(search.toLocaleLowerCase('it'))));
  const start = draftStart ?? inFrame ?? currentFrame;
  const end = omitEnd ? null : draftEnd ?? outFrame;

  function resetDraft() {
    setEditing(null); setDescription(''); setCategory('General Note'); setVerification('Da verificare');
    setDraftStart(null); setDraftEnd(null); setOmitEnd(false); setQcLink('');
  }
  useEffect(() => { resetDraft(); setSearch(''); setFilter(''); }, [media?.id]);

  async function execute(work: () => Promise<unknown>) {
    setBusy(true);
    try { await work(); } catch (error) { onError(ERROR(error)); } finally { setBusy(false); }
  }
  function editAnnotation(item: Annotation) {
    setEditing(item.id); setDescription(item.description); setCategory(item.category); setVerification(item.verification);
    setDraftStart(item.start_frame); setDraftEnd(item.end_frame); setOmitEnd(item.end_frame === null); setQcLink(item.qc_result_id ?? '');
    setTab('annotations');
  }
  async function submitAnnotation(event: FormEvent) {
    event.preventDefault();
    if (!media || !description.trim()) return;
    if (end !== null && end < start) { onError('Il fotogramma OUT deve essere successivo o uguale a IN.'); return; }
    await execute(async () => {
      const payload = { media_id: media.id, start_frame: start, end_frame: end, category, description: description.trim(), verification, qc_result_id: qcLink || null };
      if (editing) await action(`/api/annotations/${editing}`, payload, 'PATCH');
      else await action(`/api/projects/${project.id}/annotations`, { ...payload, origin: 'manual' });
      resetDraft();
    });
  }
  function duplicate(item: Annotation) {
    void execute(() => action(`/api/projects/${project.id}/annotations`, {
      media_id: item.media_id, start_frame: item.start_frame, end_frame: item.end_frame,
      category: item.category, description: item.description, origin: 'manual', verification: 'Da verificare', qc_result_id: item.qc_result_id,
    }));
  }
  function remove(item: Annotation) {
    if (!window.confirm('Eliminare questa annotazione? L’operazione non può essere annullata.')) return;
    void execute(async () => { await action(`/api/annotations/${item.id}`, undefined, 'DELETE'); if (editing === item.id) resetDraft(); });
  }
  function launchTranscription(event: FormEvent) {
    event.preventDefault();
    if (!media) return;
    if (selectionOnly && (inFrame === null || outFrame === null || outFrame <= inFrame)) {
      onError('Imposta un intervallo IN/OUT valido nel player per ritrascrivere una selezione.'); return;
    }
    void execute(() => action(`/api/media/${media.id}/transcribe`, {
      language: language || null, start: selectionOnly ? frameToSeconds(inFrame!, media) : 0,
      end: selectionOnly ? frameToSeconds(outFrame!, media) : null, model_path: modelPath.trim() || null,
    }));
  }
  function launchQC(event: FormEvent) {
    event.preventDefault();
    if (!media) return;
    void execute(() => action(`/api/media/${media.id}/qc`, {
      ...qcSettings, expected_duration: qcSettings.expected_duration === '' ? null : Number(qcSettings.expected_duration),
    }));
  }
  function noteQC(result: QCResult) {
    if (!media) return;
    void execute(() => action(`/api/projects/${project.id}/annotations`, {
      media_id: media.id, start_frame: result.start_frame ?? 0, end_frame: result.end_frame,
      category: result.test.toLowerCase().includes('black') ? 'Video QC' : result.test.toLowerCase().includes('silence') || result.test.toLowerCase().includes('peak') ? 'Audio QC' : 'Technical QC',
      description: result.description, origin: 'manual', verification: 'Da verificare', qc_result_id: result.id,
    }));
  }

  return <section className="editor-panel" aria-label="Editor del progetto">
    <div className="editor-heading"><div><span className="eyebrow">WORKSPACE</span><h2>Il dettaglio conta.</h2></div><span className="editor-mode">EDITOR</span></div>
    <div className="editor-tabs" role="tablist" aria-label="Contenuti del progetto">
      <button role="tab" aria-selected={tab === 'annotations'} className={tab === 'annotations' ? 'selected' : ''} onClick={() => setTab('annotations')}>Annotazioni <span>{annotations.length}</span></button>
      <button role="tab" aria-selected={tab === 'transcripts'} className={tab === 'transcripts' ? 'selected' : ''} onClick={() => setTab('transcripts')}>Trascrizione <span>{transcripts.length}</span></button>
      <button role="tab" aria-selected={tab === 'qc'} className={tab === 'qc' ? 'selected' : ''} onClick={() => setTab('qc')}>QC <span>{results.length}</span></button>
    </div>
    {!media ? <div className="editor-empty"><span className="empty-symbol">＋</span><h3>Il primo fotogramma è l’inizio.</h3><p>Importa un file video per aggiungere annotazioni, trascrivere i dialoghi e analizzare il media.</p></div> : <>
      {tab === 'annotations' && <div className="editor-tab-content">
        <form className="annotation-form" onSubmit={event => void submitAnnotation(event)}>
          <div className="section-label"><span>{editing ? 'MODIFICA ANNOTAZIONE' : 'NUOVA ANNOTAZIONE'}</span><span className="mono">{frameTimecode(start, media)}</span></div>
          <div className="editor-form-row"><label>Categoria<select value={category} onChange={event => setCategory(event.target.value)}>{CATEGORIES.map(value => <option key={value} value={value}>{LABELS[value]}</option>)}</select></label><label>Verifica<select value={verification} onChange={event => setVerification(event.target.value)}><option>Da verificare</option><option>Verificato</option></select></label></div>
          <label className="sr-only" htmlFor="annotation-description">Descrizione dell’annotazione</label>
          <textarea id="annotation-description" value={description} onChange={event => setDescription(event.target.value)} placeholder="Descrivi ciò che osservi o ascolti…" required rows={3} maxLength={10000} />
          <div className="annotation-range"><label>Frame IN<input aria-label="Frame IN annotazione" type="number" min={0} step={1} value={start} onChange={event => setDraftStart(Math.max(0, Number(event.target.value)))} /></label><button type="button" className="subtle" onClick={() => { onSetIn(); setDraftStart(currentFrame); }}>I · attuale</button><label>Frame OUT<input aria-label="Frame OUT annotazione" type="number" min={0} step={1} value={end ?? ''} onChange={event => { setDraftEnd(event.target.value === '' ? null : Math.max(0, Number(event.target.value))); setOmitEnd(event.target.value === ''); }} placeholder="Opzionale" /></label><button type="button" className="subtle" onClick={() => { onSetOut(); setDraftEnd(currentFrame); setOmitEnd(false); }}>O · attuale</button></div>
          <div className="annotation-timecodes"><span>IN <b className="mono">{frameTimecode(start, media)}</b></span><span>OUT <b className="mono">{end === null ? '—' : frameTimecode(end, media)}</b></span><button type="button" className="text-link" onClick={() => { setDraftStart(currentFrame); setDraftEnd(null); setOmitEnd(true); }}>Solo marker</button></div>
          {results.length > 0 && <label>Collega a un rilievo QC<select value={qcLink} onChange={event => setQcLink(event.target.value)}><option value="">Nessun collegamento</option>{results.map(result => <option key={result.id} value={result.id}>{result.test} · {result.tc_in ?? 'Media'} · {result.status}</option>)}</select></label>}
          <div className="editor-form-actions"><span>Note salvate nel progetto locale</span>{editing && <button type="button" className="subtle" onClick={resetDraft}>Annulla</button>}<button className="primary" disabled={busy || !description.trim()} type="submit">{editing ? 'Salva modifica' : '＋ Aggiungi nota'}</button></div>
        </form>
        <div className="editor-filter"><label className="search-field"><span aria-hidden="true">⌕</span><input aria-label="Cerca annotazioni" placeholder="Cerca nelle annotazioni…" value={search} onChange={event => setSearch(event.target.value)} /></label><select aria-label="Filtra categoria" value={filter} onChange={event => setFilter(event.target.value)}><option value="">Tutte le categorie</option>{CATEGORIES.map(value => <option key={value} value={value}>{LABELS[value]}</option>)}</select></div>
        <div className="result-list" aria-live="polite">
          {visible.length === 0 && <div className="list-empty">{annotations.length ? 'Nessuna annotazione corrisponde ai filtri.' : 'Nessuna annotazione. Crea una nota al timecode corrente.'}</div>}
          {visible.map(item => <article className={`annotation-card ${editing === item.id ? 'editing' : ''}`} key={item.id}>
            <div className="card-topline"><button className="tc-link mono" onClick={() => onSeek(item.start_frame)} title="Posiziona il player">{item.tc_in}</button>{item.tc_out && <span className="mono time-range-end">→ {item.tc_out}</span>}<span className="category-badge">{LABELS[item.category] ?? item.category}</span></div>
            <p className="annotation-description">{item.description}</p>
            <div className="card-footer"><span className={item.verification === 'Verificato' ? 'verified-label' : 'pending-label'}>{item.verification === 'Verificato' ? '✓ ' : '○ '}{item.verification}</span><span className="origin-label">{item.origin === 'manual' ? 'Manuale' : item.origin}{item.qc_result_id ? ' · QC collegato' : ''}</span><div className="row-actions"><button disabled={busy} onClick={() => editAnnotation(item)}>Modifica</button><button disabled={busy} onClick={() => duplicate(item)}>Duplica</button><button className="danger-text" disabled={busy} onClick={() => remove(item)}>Elimina</button></div></div>
          </article>)}
        </div>
      </div>}
      {tab === 'transcripts' && <div className="editor-tab-content">
        <form className="analysis-form" onSubmit={launchTranscription}>
          <div className="section-label"><span>TRASCRIZIONE LOCALE</span><span className="mode-chip">faster-whisper</span></div>
          <p className="panel-notice">Il modello lavora sul tuo computer. I timestamp AI sono approssimati e il testo è sempre da verificare.</p>
          <div className="editor-form-row"><label>Lingua<select value={language} onChange={event => setLanguage(event.target.value)}><option value="">Riconoscimento automatico</option><option value="it">Italiano</option><option value="en">Inglese</option><option value="fr">Francese</option><option value="de">Tedesco</option><option value="es">Spagnolo</option><option value="pt">Portoghese</option><option value="ja">Giapponese</option></select></label><label>Modello locale (cartella)<input value={modelPath} onChange={event => setModelPath(event.target.value)} placeholder="Usa modello configurato" autoComplete="off" /></label></div>
          <div className="editor-form-actions"><label className="checkbox-label"><input type="checkbox" checked={selectionOnly} onChange={event => setSelectionOnly(event.target.checked)} />Solo intervallo IN/OUT</label><button className="primary" disabled={busy || !media.available} type="submit">{selectionOnly ? 'Ritrascrivi intervallo' : 'Trascrivi audio'}</button></div>
          {selectionOnly && <p className="panel-notice">Intervallo: <span className="mono">{inFrame === null ? 'IN non impostato' : frameTimecode(inFrame, media)} → {outFrame === null ? 'OUT non impostato' : frameTimecode(outFrame, media)}</span>. Vengono sostituiti solo i segmenti completamente contenuti nell’intervallo IN/OUT. I segmenti esterni e le annotazioni manuali vengono conservati.</p>}
        </form>
        <div className="result-list" aria-live="polite">{transcripts.length === 0 ? <div className="list-empty">Nessuna trascrizione disponibile. Installa faster-whisper e configura un modello locale per iniziare.</div> : transcripts.map(item => <TranscriptCard key={item.id} transcript={item} onSeek={onSeek} action={action} onError={onError} />)}</div>
      </div>}
      {tab === 'qc' && <div className="editor-tab-content">
        <form className="analysis-form" onSubmit={launchQC}>
          <div className="section-label"><span>CONTROLLO QUALITÀ PRELIMINARE</span><span className="mode-chip">FFmpeg</span></div>
          <p className="panel-notice">Nero e silenzio possono essere intenzionali. Ogni rilievo richiede revisione; questa analisi non certifica conformità broadcast o PSE.</p>
          <div className="editor-form-row"><label>Preset<select value={qcSettings.preset} onChange={event => setQcSettings({ ...qcSettings, preset: event.target.value })}><option value="source">Sorgente · nessun vincolo HD</option><option value="hd25">HD 1920×1080 · 25 fps</option><option value="hd2997">HD 1920×1080 · 29,97 fps</option></select></label><label>Durata attesa (secondi)<input type="number" min={0} step="0.1" placeholder="Non verificare" value={qcSettings.expected_duration} onChange={event => setQcSettings({ ...qcSettings, expected_duration: event.target.value })} /></label></div>
          <details className="qc-thresholds"><summary>Regola soglie di analisi</summary><div className="threshold-grid">
            <label>Durata nero (s)<input type="number" min="0.01" max="60" step="0.01" value={qcSettings.black_duration} onChange={event => setQcSettings({ ...qcSettings, black_duration: Number(event.target.value) })} /></label>
            <label>Soglia nero (0–1)<input type="number" min="0" max="1" step="0.01" value={qcSettings.black_threshold} onChange={event => setQcSettings({ ...qcSettings, black_threshold: Number(event.target.value) })} /></label>
            <label>Durata silenzio (s)<input type="number" min="0.01" max="60" step="0.01" value={qcSettings.silence_duration} onChange={event => setQcSettings({ ...qcSettings, silence_duration: Number(event.target.value) })} /></label>
            <label>Soglia silenzio (dB)<input type="number" min="-100" max="0" step="1" value={qcSettings.silence_threshold_db} onChange={event => setQcSettings({ ...qcSettings, silence_threshold_db: Number(event.target.value) })} /></label>
            <label>Picco sospetto (dB)<input type="number" min="-30" max="0" step="0.1" value={qcSettings.peak_threshold_db} onChange={event => setQcSettings({ ...qcSettings, peak_threshold_db: Number(event.target.value) })} /></label>
            <label>Tolleranza durata (s)<input type="number" min="0" step="0.1" value={qcSettings.duration_tolerance} onChange={event => setQcSettings({ ...qcSettings, duration_tolerance: Number(event.target.value) })} /></label>
          </div></details>
          <div className="editor-form-actions"><span>Blackdetect · Silencedetect · Metadati</span><button type="submit" className="primary" disabled={busy || !media.available}>Avvia analisi QC</button></div>
        </form>
        <div className="qc-summary">{(['PASS', 'WARNING', 'FAIL', 'NOT TESTED'] as const).map(status => <span key={status} className={`qc-stat ${status.toLowerCase().replace(' ', '-')}`}>{status}<b>{results.filter(item => item.status === status).length}</b></span>)}</div>
        <div className="result-list" aria-live="polite">{results.length === 0 && <div className="list-empty">Nessuna analisi eseguita per questo media.</div>}{results.map(result => <article className="qc-card" key={result.id}>
          <div className="card-topline"><span className={`qc-status ${result.status.toLowerCase().replace(' ', '-')}`}>{result.status}</span><strong>{result.test}</strong>{result.start_frame !== null && <button className="tc-link mono" onClick={() => onSeek(result.start_frame!)}>{result.tc_in}</button>}</div>
          <p>{result.description}</p>{result.tc_out && <div className="qc-measures mono">OUT {result.tc_out}</div>}
          <div className="qc-measures"><span>Misurato: <b>{measuredLabel(result.measured)}</b></span><span>Soglia: <b>{measuredLabel(result.threshold)}</b></span></div>
          <div className="card-footer"><span className={result.verification === 'Confermato' ? 'verified-label' : 'pending-label'}>{result.verification}</span><div className="row-actions"><button disabled={busy} onClick={() => void execute(() => action(`/api/qc/${result.id}`, { verification: 'Confermato' }, 'PATCH'))}>Conferma</button><button disabled={busy} onClick={() => void execute(() => action(`/api/qc/${result.id}`, { verification: 'Respinto' }, 'PATCH'))}>Respingi</button><button disabled={busy} onClick={() => noteQC(result)}>＋ Nota</button></div></div>
        </article>)}</div>
      </div>}
    </>}
  </section>;
}

function TranscriptCard({ transcript, onSeek, action, onError }: { transcript: Transcript; onSeek: (frame: number) => void; action: Action; onError: (message: string) => void }) {
  const [text, setText] = useState(transcript.text);
  const [verification, setVerification] = useState(transcript.verification);
  const [uncertainty, setUncertainty] = useState<string[]>(transcript.uncertainty ?? []);
  const [busy, setBusy] = useState(false);
  const savedUncertainty = JSON.stringify(transcript.uncertainty ?? []);
  const dirty = text !== transcript.text || verification !== transcript.verification || JSON.stringify(uncertainty) !== savedUncertainty;
  useEffect(() => {
    setText(transcript.text);
    setVerification(transcript.verification);
    setUncertainty(JSON.parse(savedUncertainty) as string[]);
  }, [transcript.text, transcript.verification, savedUncertainty]);
  async function save(annotate = false) {
    setBusy(true);
    try {
      if (dirty) await action(`/api/transcripts/${transcript.id}`, { text, verification, uncertainty }, 'PATCH');
      if (annotate) await action(`/api/transcripts/${transcript.id}/annotation`, {});
    } catch (error) { onError(ERROR(error)); } finally { setBusy(false); }
  }
  return <article className="transcript-card">
    <div className="card-topline"><button className="tc-link mono" onClick={() => onSeek(transcript.start_frame)}>{transcript.tc_in}</button><span className="mono time-range-end">→ {transcript.tc_out}</span><span className="category-badge">AI · locale</span></div>
    <label className="sr-only" htmlFor={`transcript-${transcript.id}`}>Testo segmento {transcript.tc_in}</label><textarea id={`transcript-${transcript.id}`} value={text} onChange={event => setText(event.target.value)} rows={2} maxLength={10000} />
    {uncertainty.length > 0 && <p className="uncertainty-label">Da verificare: {uncertainty.join(' · ')}</p>}
    <details className="transcript-markers"><summary>Segnala incertezza</summary><p className="panel-notice">Le voci sovrapposte sono marcate manualmente, non rilevate automaticamente. I marcatori non modificano il testo.</p><div className="row-actions">{['Parlato incomprensibile', 'Voci sovrapposte', 'Segmento incerto'].map(marker => <button key={marker} type="button" disabled={busy} aria-pressed={uncertainty.includes(marker)} onClick={() => { setUncertainty(current => current.includes(marker) ? current.filter(value => value !== marker) : [...current, marker]); setVerification('Da verificare'); }}>{uncertainty.includes(marker) ? '✓' : '＋'} {marker}</button>)}</div></details>
    <div className="card-footer"><select aria-label={`Verifica segmento ${transcript.tc_in}`} value={verification} onChange={event => setVerification(event.target.value)}><option>Da verificare</option><option>Verificato</option></select><div className="row-actions"><button disabled={busy || !text.trim() || !dirty} onClick={() => void save()}>Salva correzione</button><button disabled={busy || !text.trim()} onClick={() => void save(true)}>＋ Nell’editor</button></div></div>
  </article>;
}
