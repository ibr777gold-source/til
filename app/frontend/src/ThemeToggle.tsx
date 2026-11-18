import {useEffect, useState} from 'react';

function savedTheme(): 'light' | 'dark' | null {
  try {
    const value = localStorage.getItem('til-theme');
    return value === 'light' || value === 'dark' ? value : null;
  } catch { return null; }
}

export default function ThemeToggle({ru = false}: {ru?: boolean}) {
  const [theme, setTheme] = useState<'light' | 'dark' | null>(savedTheme);
  const [systemDark, setSystemDark] = useState(() => window.matchMedia('(prefers-color-scheme: dark)').matches);
  useEffect(() => {
    const query = window.matchMedia('(prefers-color-scheme: dark)');
    const update = () => setSystemDark(query.matches);
    query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, []);
  useEffect(() => {
    if (theme) document.documentElement.dataset.theme = theme;
    else delete document.documentElement.dataset.theme;
  }, [theme]);
  const dark = theme ? theme === 'dark' : systemDark;
  function toggle() {
    const next = dark ? 'light' : 'dark';
    setTheme(next);
    try { localStorage.setItem('til-theme', next); } catch { /* Theme still works for this session. */ }
  }
  const label = ru ? (dark ? 'Включить светлую тему' : 'Включить тёмную тему') : (dark ? 'Yorug‘ mavzuni yoqish' : 'Qorong‘i mavzuni yoqish');
  return <button type="button" className="theme-toggle" onClick={toggle} aria-label={label} title={label}>
    {dark ? <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42m0-14.14-1.42 1.42M6.35 17.65l-1.42 1.42"/></svg> : <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M20.5 14.1A8.5 8.5 0 0 1 9.9 3.5a8.5 8.5 0 1 0 10.6 10.6Z"/></svg>}
  </button>;
}
