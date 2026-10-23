interface IconProps { name: string; size?: number; className?: string }
const paths: Record<string, string> = {
  plus: 'M12 5v14M5 12h14', folder: 'M3 7h6l2 2h10v11H3z M3 7V4h7l2 3', upload: 'M12 16V3m-5 5 5-5 5 5M4 16v5h16v-5',
  save: 'M4 3h13l4 4v14H3V3h1m3 0v6h10V3M7 21v-8h10v8', download: 'M12 3v13m-5-5 5 5 5-5M4 17v4h16v-4',
  settings: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M9 3h6l1 3 3 1 2 5-2 5-3 1-1 3H9l-1-3-3-1-2-5 2-5 3-1 1-3',
  play: 'M8 4v16l12-8z', pause: 'M8 4v16M16 4v16', stop: 'M5 5h14v14H5z', backward: 'M6 5v14M18 5 7 12l11 7z', forward: 'M18 5v14M6 5l11 7-11 7z',
  volume: 'M3 9h4l5-5v16l-5-5H3zM16 8c3 2 3 6 0 8m3-11c5 4 5 10 0 14', muted: 'M3 9h4l5-5v16l-5-5H3zM16 9l5 6m0-6-5 6',
  fullscreen: 'M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5', close: 'm5 5 14 14M19 5 5 19', send: 'm3 3 19 9-19 9 4-9-4-9m4 9h15',
  film: 'M3 3h18v18H3zM7 3v18m10-18v18M3 8h4m10 0h4M3 16h4m10 0h4', check: 'm4 12 5 5L20 6', help: 'M9 9a3 3 0 1 1 4 3c-1 1-1 2-1 3m0 3h.01M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20',
  chat: 'M4 4h16v13H8l-4 4zM8 8h8m-8 4h5', refresh: 'M20 8a9 9 0 1 0 0 9M20 3v5h-5', info: 'M12 10v7m0-10h.01M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20',
};
export default function Icon({ name, size = 16, className = '' }: IconProps) {
  return <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name] ?? paths.info} /></svg>;
}
