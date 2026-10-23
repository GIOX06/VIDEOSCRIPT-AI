import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import Icon from './Icon';

export default function Modal({ title, onClose, children, wide = false, error }: { title: string; onClose: () => void; children: ReactNode; wide?: boolean; error?: string }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const element = dialog.current;
    if (element && !element.open) element.showModal();
    return () => { element?.close(); };
  }, []);
  return <dialog ref={dialog} className={`modal ${wide ? 'wide' : ''}`} aria-label={title} onCancel={e => { e.preventDefault(); onClose(); }} onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
    <div className="modal-heading"><h2>{title}</h2><button className="icon-button" aria-label="Chiudi finestra" onClick={onClose}><Icon name="close" /></button></div>
    {error && <div className="modal-error" role="alert">{error}</div>}
    {children}
  </dialog>;
}
